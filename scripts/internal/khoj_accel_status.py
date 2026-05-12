#!/usr/bin/env python3
"""Build HIGH-GRAVITY Khoj acceleration status JSON."""

import argparse
import json
import os
import time


def _flag(value):
    return str(value or "").lower() in {"1", "true", "yes", "on"}


def _csv(value):
    return [item for item in str(value or "").split(",") if item]


def _load_json(path):
    if not path:
        return {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            raw = fh.read()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            start = raw.find("{")
            if start >= 0:
                payload, _ = json.JSONDecoder().raw_decode(raw[start:])
                return payload
            raise
    except Exception as exc:
        return {"error": type(exc).__name__}


def runtime_activity(runtime):
    torch_info = runtime.get("torch") or {}
    openvino_info = runtime.get("openvino") or {}
    usb_info = runtime.get("usb") or {}
    compile_results = openvino_info.get("compile") or {}
    ov_compile_ok = any(result.get("ok") for result in compile_results.values())
    ov_accel_compile_ok = any(
        name.upper() != "CPU" and result.get("ok")
        for name, result in compile_results.items()
    )
    myriad_compile_ok = any(
        name.upper() == "MYRIAD" and result.get("ok")
        or name.upper().startswith("MYRIAD.") and result.get("ok")
        for name, result in compile_results.items()
    )
    npu_compile_ok = any(
        name.upper() == "NPU" and result.get("ok")
        for name, result in compile_results.items()
    )
    devices = [str(device) for device in openvino_info.get("devices") or []]
    myriad_devices = [
        device
        for device in devices
        if device.upper() == "MYRIAD" or device.upper().startswith("MYRIAD.")
    ]
    myriad_compile_results = {
        name: result
        for name, result in compile_results.items()
        if name.upper() == "MYRIAD" or name.upper().startswith("MYRIAD.")
    }
    myriad_compile_errors = [
        str(result.get("error", ""))
        for result in myriad_compile_results.values()
        if not result.get("ok") and result.get("error")
    ]
    myriad_compile_failed = bool(myriad_devices and myriad_compile_results and not myriad_compile_ok)
    boot_error_markers = (
        "not opened",
        "failed to find booted device",
        "allocate graph",
        "boot",
    )
    myriad_boot_failed = any(
        marker in error.lower()
        for error in myriad_compile_errors
        for marker in boot_error_markers
    )
    return {
        "cuda": bool(torch_info.get("cuda_runtime_ok")),
        "openvino": bool(ov_compile_ok),
        "openvino_accelerated": bool(ov_accel_compile_ok),
        "openvino_runtime_visible": bool(devices),
        "openvino_compile_ok": bool(ov_compile_ok),
        "myriad": bool(myriad_compile_ok),
        "ncs2": bool(myriad_compile_ok),
        "myriad_visible": bool(myriad_devices),
        "myriad_devices": myriad_devices,
        "myriad_compile_ok": bool(myriad_compile_ok),
        "myriad_compile_failed": myriad_compile_failed,
        "myriad_boot_failed": myriad_boot_failed,
        "myriad_compile_errors": myriad_compile_errors[:3],
        "npu": bool(npu_compile_ok),
        "openvino_devices_visible": devices,
        "usb_passthrough": bool(usb_info.get("dev_bus_usb_present")),
        "usb_device_count": int(usb_info.get("device_count") or 0),
    }


def proof_summary(runtime):
    activity = runtime_activity(runtime)
    torch_info = runtime.get("torch") or {}
    openvino_info = runtime.get("openvino") or {}
    compile_results = openvino_info.get("compile") or {}
    return {
        "cuda": {
            "active": activity["cuda"],
            "method": torch_info.get("proof", "torch.cuda.is_available plus tensor op"),
            "error": runtime.get("torch_error", ""),
        },
        "openvino": {
            "active": activity["openvino"],
            "method": "openvino.Core().compile_model on tiny model",
            "compile": compile_results,
            "error": runtime.get("openvino_error", ""),
        },
        "myriad": {
            "active": activity["myriad"],
            "method": "OpenVINO compile_model on MYRIAD",
            "compile": compile_results.get("MYRIAD", {})
            or next((result for name, result in compile_results.items() if name.upper().startswith("MYRIAD.")), {}),
        },
        "ncs2": {
            "active": activity["ncs2"],
            "method": "NCS2 reports as MYRIAD in OpenVINO",
            "compile": compile_results.get("MYRIAD", {})
            or next((result for name, result in compile_results.items() if name.upper().startswith("MYRIAD.")), {}),
        },
    }


def _previous_host(previous):
    fallback = {
        "cuda": bool(previous.get("cuda")),
        "nvidia_name": previous.get("nvidia_name", ""),
        "openvino": bool(previous.get("openvino")),
        "openvino_devices": previous.get("openvino_host_devices") or [],
        "npu": bool(previous.get("npu")),
        "myriad": bool(previous.get("myriad")),
        "myriad_count": int(previous.get("myriad_count") or 0),
        "ncs2": bool(previous.get("myriad")),
        "ncs2_count": int(previous.get("myriad_count") or 0),
    }
    if previous.get("host"):
        fallback.update(dict(previous.get("host") or {}))
    return fallback


def _previous_container(previous):
    fallback = {
        "cuda_exposed": bool(previous.get("cuda")),
        "openvino_exposed": bool(previous.get("openvino")),
        "npu_exposed": bool(previous.get("npu")),
        "myriad_exposed": bool(previous.get("myriad")),
        "ncs2_exposed": bool(previous.get("myriad")),
    }
    if previous.get("container"):
        fallback.update(dict(previous.get("container") or {}))
    return fallback


def build_status(env, runtime=None, phase=None, previous=None):
    runtime = runtime or {}
    previous = previous or {}
    if not runtime and isinstance(previous.get("runtime"), dict):
        runtime = dict(previous.get("runtime") or {})
    host_openvino_devices = _csv(env.get("OPENVINO_HOST_DEVICES"))
    myriad_count = int(env.get("MYRIAD_COUNT") or 0)
    host = {
        "cuda": _flag(env.get("CUDA_HOST_DETECTED")),
        "nvidia_name": env.get("NVIDIA_NAME", ""),
        "openvino": _flag(env.get("OPENVINO_HOST_DETECTED")) or bool(host_openvino_devices),
        "openvino_devices": host_openvino_devices,
        "npu": _flag(env.get("NPU_HOST_DETECTED")),
        "myriad": _flag(env.get("MYRIAD_HOST_DETECTED")) or myriad_count > 0,
        "myriad_count": myriad_count,
        "ncs2": _flag(env.get("MYRIAD_HOST_DETECTED")) or myriad_count > 0,
        "ncs2_count": myriad_count,
    }
    container = {
        "cuda_exposed": _flag(env.get("CUDA_ENABLED")),
        "openvino_exposed": _flag(env.get("OPENVINO_ENABLED")),
        "npu_exposed": _flag(env.get("NPU_ENABLED")),
        "myriad_exposed": _flag(env.get("MYRIAD_ENABLED")),
        "ncs2_exposed": _flag(env.get("MYRIAD_ENABLED")),
    }
    if not any(host.values()) and previous:
        host = _previous_host(previous)
        myriad_count = int(host.get("myriad_count") or 0)
    if not any(container.values()) and previous:
        container = _previous_container(previous)
    activity = runtime_activity(runtime)
    payload = {
        "updated_at": int(time.time()),
        "phase": phase or env.get("PHASE", ""),
        "mode": env.get("ACCEL_MODE", "auto"),
        "host": host,
        "container": container,
        "runtime_active": activity,
        "proof": proof_summary(runtime),
        "runtime": runtime,
        "cuda": container["cuda_exposed"],
        "openvino": container["openvino_exposed"],
        "npu": container["npu_exposed"],
        "myriad": container["myriad_exposed"],
        "myriad_count": myriad_count,
        "nvidia_name": env.get("NVIDIA_NAME", "") or host.get("nvidia_name", ""),
        "openvino_host_devices": host_openvino_devices or host.get("openvino_devices", []),
    }
    return payload


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-file", default="")
    parser.add_argument("--previous-file", default="")
    parser.add_argument("--phase", default="")
    args = parser.parse_args()
    runtime = _load_json(args.runtime_file)
    previous = _load_json(args.previous_file)
    status = build_status(
        os.environ,
        runtime=runtime,
        phase=args.phase or None,
        previous=previous,
    )
    print(json.dumps(status, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
