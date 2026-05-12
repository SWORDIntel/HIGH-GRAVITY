#!/usr/bin/env python3
"""Summarize NCS2/OpenVINO state for safe recovery workflows."""

import argparse
import json
import re
import sys
from pathlib import Path


KNOWN_MYRIAD_PRODUCTS = {
    "2150": "Movidius Neural Compute Stick",
    "2485": "Movidius MyriadX / NCS2",
    "f63b": "Movidius booted device",
    "f63c": "Movidius booted device",
    "2491": "Movidius Myriad device",
}

BOOT_FAILURE_MARKERS = (
    "myriad device is not opened",
    "failed to find booted device after boot",
    "failed to allocate graph",
)


def load_json(path):
    if not path:
        return {}
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}


def parse_lsusb(text):
    devices = []
    pattern = re.compile(
        r"^Bus\s+(?P<bus>\d+)\s+Device\s+(?P<device>\d+):\s+ID\s+"
        r"(?P<vendor>[0-9a-fA-F]{4}):(?P<product>[0-9a-fA-F]{4})\s*(?P<label>.*)$"
    )
    for line in text.splitlines():
        match = pattern.match(line.strip())
        if not match:
            continue
        item = match.groupdict()
        item["vendor"] = item["vendor"].lower()
        item["product"] = item["product"].lower()
        if item["vendor"] != "03e7":
            continue
        product_label = KNOWN_MYRIAD_PRODUCTS.get(item["product"], "Intel Movidius device")
        item["known_label"] = product_label
        item["path"] = f"/dev/bus/usb/{item['bus']}/{item['device']}"
        devices.append(item)
    return devices


def _openvino_runtime(status):
    runtime = status.get("runtime") or status
    return runtime.get("openvino") or {}


def _compile_entries(status):
    openvino = _openvino_runtime(status)
    compile_results = openvino.get("compile") or {}
    return [
        {"target": target, **(result if isinstance(result, dict) else {"result": result})}
        for target, result in compile_results.items()
        if str(target).upper() == "MYRIAD" or str(target).upper().startswith("MYRIAD.")
    ]


def classify_state(status, lsusb_devices):
    openvino = _openvino_runtime(status)
    visible_devices = [str(device) for device in openvino.get("devices") or []]
    visible_myriad = [
        device for device in visible_devices if device.upper() == "MYRIAD" or device.upper().startswith("MYRIAD.")
    ]
    compile_entries = _compile_entries(status)
    compile_ok = any(bool(entry.get("ok")) for entry in compile_entries)
    errors = " | ".join(str(entry.get("error", "")) for entry in compile_entries if entry.get("error"))
    boot_failure = any(marker in errors.lower() for marker in BOOT_FAILURE_MARKERS)

    if compile_ok:
        state = "compile_active"
        recommendation = "NCS2 is usable; no reset needed."
        next_command = ""
    elif visible_myriad and boot_failure:
        state = "visible_boot_failed"
        recommendation = "OpenVINO sees MYRIAD but firmware boot/open failed; reset the affected USB devices, then restart Khoj."
        next_command = "./hg.sh khoj ncs2 reset"
    elif visible_myriad:
        state = "visible_compile_failed"
        recommendation = "OpenVINO sees MYRIAD but compile failed; inspect compile error before resetting."
        next_command = "./hg.sh khoj ncs2 reset"
    elif lsusb_devices:
        state = "usb_visible_runtime_missing"
        recommendation = "USB sticks are visible but OpenVINO runtime did not expose MYRIAD; restart Khoj after checking OpenVINO env."
        next_command = "./hg.sh khoj ncs2 probe"
    else:
        state = "not_detected"
        recommendation = "No Intel Movidius USB device found by lsusb."
        next_command = "physically replug the NCS2 sticks, then run ./hg.sh khoj ncs2 probe"

    return {
        "state": state,
        "compile_ok": compile_ok,
        "boot_failure": boot_failure,
        "visible_openvino_devices": visible_devices,
        "visible_myriad_devices": visible_myriad,
        "compile": compile_entries,
        "compile_errors": errors,
        "usb_devices": lsusb_devices,
        "usb_device_count": len(lsusb_devices),
        "recommendation": recommendation,
        "next_command": next_command,
    }


def build_summary(status, lsusb_text):
    return classify_state(status, parse_lsusb(lsusb_text))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--status-file", default="logs/khoj_accel.json")
    parser.add_argument("--lsusb-file", default="")
    args = parser.parse_args()

    status = load_json(args.status_file)
    if args.lsusb_file:
        lsusb_text = Path(args.lsusb_file).read_text(encoding="utf-8")
    else:
        lsusb_text = sys.stdin.read()
    print(json.dumps(build_summary(status, lsusb_text), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
