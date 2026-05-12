#!/usr/bin/env python3
"""Probe accelerator runtime availability from inside the Khoj container."""

import json
import os
import signal
import subprocess
from contextlib import contextmanager


def _env_snapshot():
    keys = [
        "CUDA_VISIBLE_DEVICES",
        "NVIDIA_VISIBLE_DEVICES",
        "NVIDIA_DRIVER_CAPABILITIES",
        "OPENVINO_DEVICE",
        "KHOJ_ACCEL_CUDA",
        "KHOJ_ACCEL_OPENVINO",
        "KHOJ_ACCEL_MYRIAD",
        "KHOJ_OPENVINO_VERSION",
        "KHOJ_OPENVINO_SOURCE",
        "INTEL_OPENVINO_DIR",
        "HDDL_INSTALL_DIR",
        "PYTHONPATH",
        "LD_LIBRARY_PATH",
    ]
    return {key: os.environ.get(key) for key in keys if os.environ.get(key) is not None}


def _probe_torch(out):
    try:
        import torch

        cuda_available = bool(torch.cuda.is_available())
        torch_info = {
            "version": getattr(torch, "__version__", ""),
            "cuda_available": cuda_available,
            "cuda_count": int(torch.cuda.device_count()),
            "cuda_runtime_ok": False,
        }
        if cuda_available:
            device = torch.device("cuda:0")
            sample = torch.tensor([1.0, 2.0], device=device) * 2
            torch.cuda.synchronize(device)
            torch_info["device_name"] = torch.cuda.get_device_name(0)
            torch_info["cuda_runtime_ok"] = bool(sample.detach().cpu().tolist() == [2.0, 4.0])
            torch_info["proof"] = "torch tensor op on cuda:0"
        out["torch"] = torch_info
    except Exception as exc:
        out["torch_error"] = f"{type(exc).__name__}: {exc}"


def _openvino_model():
    try:
        import openvino as ov
        opset8 = ov.opset8
        ov_type = ov.Type
        model_cls = ov.Model
    except AttributeError:
        from openvino.runtime import Model, Type, opset8

        ov_type = Type
        model_cls = Model

    param = opset8.parameter([1, 2], ov_type.f32, name="input")
    relu = opset8.relu(param)
    result = opset8.result(relu)
    return model_cls([result], [param], "highgravity_runtime_probe")


def _compile_openvino_with_timeout(core, model, target, timeout_s=20):
    def _timeout(_signum, _frame):
        raise TimeoutError(f"OpenVINO compile timed out after {timeout_s}s")

    previous = signal.signal(signal.SIGALRM, _timeout)
    signal.alarm(timeout_s)
    try:
        core.compile_model(model, target)
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)


@contextmanager
def _silence_native_output():
    stdout_fd = os.dup(1)
    stderr_fd = os.dup(2)
    try:
        with open(os.devnull, "w") as devnull:
            os.dup2(devnull.fileno(), 1)
            os.dup2(devnull.fileno(), 2)
            yield
    finally:
        os.dup2(stdout_fd, 1)
        os.dup2(stderr_fd, 2)
        os.close(stdout_fd)
        os.close(stderr_fd)


def _probe_openvino(out):
    try:
        import openvino as ov

        core_cls = getattr(ov, "Core", None)
        if core_cls is None:
            from openvino.runtime import Core

            core_cls = Core
        core = core_cls()
        devices = list(core.available_devices)
        requested = (os.environ.get("OPENVINO_DEVICE", "AUTO") or "").strip() or "AUTO"
        openvino_info = {
            "version": getattr(ov, "__version__", ""),
            "devices": devices,
            "requested_device": requested,
            "compile": {},
        }
        if requested.upper() != "AUTO":
            available = {device.upper() for device in devices}
            requested_upper = requested.upper()
            openvino_info["requested_device_supported"] = (
                requested_upper in available
                or any(device.upper().startswith(f"{requested_upper}.") for device in devices)
            )
            if not openvino_info["requested_device_supported"]:
                openvino_info["requested_device_error"] = (
                    f'{requested} not available in runtime devices: {",".join(sorted(devices))}'
                )

        compile_targets = []
        if requested.upper() != "AUTO":
            matching_devices = [
                device
                for device in devices
                if device.upper() == requested.upper() or device.upper().startswith(f"{requested.upper()}.")
            ]
            compile_targets.extend(matching_devices or [requested])
        for candidate in ("MYRIAD", "NPU", "GPU", "CPU"):
            for device in devices:
                device_upper = device.upper()
                if device_upper == candidate or device_upper.startswith(f"{candidate}."):
                    compile_targets.append(device)
        seen = set()
        model = _openvino_model()
        for target in compile_targets:
            normalized = target.upper()
            if normalized in seen:
                continue
            seen.add(normalized)
            try:
                with _silence_native_output():
                    _compile_openvino_with_timeout(core, model, target)
                openvino_info["compile"][target] = {
                    "ok": True,
                    "proof": f"compiled tiny OpenVINO model on {target}",
                }
            except Exception as exc:
                openvino_info["compile"][target] = {
                    "ok": False,
                    "error": f"{type(exc).__name__}: {exc}",
                }
        out["openvino"] = openvino_info
    except Exception as exc:
        out["openvino_error"] = f"{type(exc).__name__}: {exc}"


def _probe_nvidia_smi(out):
    try:
        out["nvidia_smi"] = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
            text=True,
            timeout=3,
        ).strip()
    except Exception as exc:
        out["nvidia_smi_error"] = f"{type(exc).__name__}: {exc}"


def _probe_usb_passthrough(out):
    usb_root = "/dev/bus/usb"
    devices = []
    try:
        for bus in sorted(os.listdir(usb_root)):
            bus_path = os.path.join(usb_root, bus)
            if not os.path.isdir(bus_path):
                continue
            for dev in sorted(os.listdir(bus_path)):
                dev_path = os.path.join(bus_path, dev)
                try:
                    st = os.stat(dev_path)
                except OSError:
                    continue
                devices.append(
                    {
                        "bus": bus,
                        "device": dev,
                        "path": dev_path,
                        "mode": oct(st.st_mode & 0o777),
                    }
                )
        out["usb"] = {
            "dev_bus_usb_present": True,
            "device_count": len(devices),
            "devices": devices[:32],
        }
    except Exception as exc:
        out["usb"] = {
            "dev_bus_usb_present": os.path.exists(usb_root),
            "error": f"{type(exc).__name__}: {exc}",
        }


def main():
    out = {"env": _env_snapshot()}
    _probe_torch(out)
    _probe_openvino(out)
    _probe_nvidia_smi(out)
    _probe_usb_passthrough(out)
    print(json.dumps(out, sort_keys=True))


if __name__ == "__main__":
    main()
