#!/usr/bin/env python3
"""HIGH-GRAVITY Antigravity stream monitor.

Reads local HIGH-GRAVITY JSONL telemetry streams produced by the C microproxy
front and the Python TLS termination layer. It never decrypts traffic itself;
it only summarizes plaintext/decompressed observations already emitted by the
local proxy chain.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from collections import Counter, defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Deque, Dict, Iterable, Iterator, List, Optional, TextIO

VERSION = "1.1.0"

DEFAULT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TRAFFIC_LOG = DEFAULT_ROOT / "logs" / "traffic_flows.jsonl"
DEFAULT_MICROPROXY_LOG = DEFAULT_ROOT / "logs" / "microproxy_events.jsonl"
DEFAULT_STATE_FILE = Path(
    os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local" / "state"))
) / "high-gravity" / "antigravity" / "state.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def load_jsonl(path: Path, *, skip_invalid: bool = True) -> Iterator[Dict[str, Any]]:
    if not path.exists():
        return
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line_no, line in enumerate(handle, 1):
            raw = line.strip()
            if not raw:
                continue
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError as exc:
                if skip_invalid:
                    continue
                raise SystemExit(f"{path}:{line_no}: invalid JSONL: {exc}") from exc
            if isinstance(payload, dict):
                payload.setdefault("_source", str(path))
                payload.setdefault("_line", line_no)
                yield payload


def follow_jsonl(path: Path, *, interval: float = 0.5, from_start: bool = False) -> Iterator[Dict[str, Any]]:
    """Follow a JSONL path and reopen it after size-based rotation."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch(exist_ok=True)
    handle = path.open("r", encoding="utf-8", errors="replace")
    try:
        if not from_start:
            handle.seek(0, 2)
        while True:
            line = handle.readline()
            if not line:
                try:
                    current = path.stat()
                    opened = os.fstat(handle.fileno())
                    rotated = current.st_ino != opened.st_ino or current.st_size < handle.tell()
                except FileNotFoundError:
                    rotated = False
                if rotated:
                    handle.close()
                    handle = path.open("r", encoding="utf-8", errors="replace")
                    continue
                time.sleep(interval)
                continue
            raw = line.strip()
            if not raw:
                continue
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                payload.setdefault("_source", str(path))
                yield payload
    finally:
        handle.close()


def body_size(event: Dict[str, Any]) -> int:
    body = event.get("body")
    if isinstance(body, dict):
        try:
            return int(body.get("bytes") or 0)
        except (TypeError, ValueError):
            return 0
    for key in ("bytes_in", "bytes_out", "bytes"):
        try:
            return int(event.get(key) or 0)
        except (TypeError, ValueError):
            pass
    return 0


def summarize(traffic_events: Iterable[Dict[str, Any]], microproxy_events: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    traffic_count = 0
    traffic_bytes = 0
    by_direction: Counter[str] = Counter()
    by_route: Counter[str] = Counter()
    by_status: Counter[str] = Counter()
    by_content_type: Counter[str] = Counter()
    last_request_by_id: Dict[str, Dict[str, Any]] = {}
    recent: Deque[Dict[str, Any]] = deque(maxlen=10)

    for event in traffic_events:
        traffic_count += 1
        traffic_bytes += body_size(event)
        by_direction[str(event.get("direction") or "unknown")] += 1
        by_route[str(event.get("route_mode") or event.get("route") or "unknown")] += 1
        if event.get("status") is not None:
            by_status[str(event.get("status"))] += 1
        content_type = str(event.get("content_type") or "unknown").split(";", 1)[0]
        by_content_type[content_type] += 1
        request_id = str(event.get("request_id") or "")
        if request_id:
            last_request_by_id[request_id] = event
        recent.append({
            "ts": event.get("ts"),
            "direction": event.get("direction"),
            "method": event.get("method"),
            "path": event.get("path"),
            "status": event.get("status"),
            "bytes": body_size(event),
            "route_mode": event.get("route_mode"),
        })

    micro_count = 0
    micro_by_event: Counter[str] = Counter()
    micro_by_route: Counter[str] = Counter()
    direct_counts: Counter[str] = Counter()
    for event in microproxy_events:
        micro_count += 1
        event_name = str(event.get("event") or event.get("type") or "unknown")
        micro_by_event[event_name] += 1
        route = str(event.get("route") or "unknown")
        micro_by_route[route] += 1
        if route in {"direct_upstream", "python_fallback", "passthrough"}:
            direct_counts[route] += 1

    paired = defaultdict(int)
    for event in last_request_by_id.values():
        paired[str(event.get("direction") or "unknown")] += 1

    return {
        "schema_version": 1,
        "generated_at": utc_now(),
        "traffic": {
            "events": traffic_count,
            "bytes": traffic_bytes,
            "unique_request_ids": len(last_request_by_id),
            "by_direction": dict(sorted(by_direction.items())),
            "by_route": dict(sorted(by_route.items())),
            "by_status": dict(sorted(by_status.items())),
            "by_content_type": dict(sorted(by_content_type.items())),
            "recent": list(recent),
        },
        "microproxy": {
            "events": micro_count,
            "by_event": dict(sorted(micro_by_event.items())),
            "by_route": dict(sorted(micro_by_route.items())),
            "direct_path": dict(sorted(direct_counts.items())),
        },
    }


def print_human_summary(summary: Dict[str, Any]) -> None:
    traffic = summary["traffic"]
    micro = summary["microproxy"]
    print(f"HIGH-GRAVITY Antigravity stream summary @ {summary['generated_at']}")
    print(f"traffic_events={traffic['events']} traffic_bytes={traffic['bytes']} unique_request_ids={traffic['unique_request_ids']}")
    print(f"directions={traffic['by_direction']}")
    print(f"routes={traffic['by_route']}")
    print(f"statuses={traffic['by_status']}")
    print(f"content_types={traffic['by_content_type']}")
    print(f"microproxy_events={micro['events']} microproxy_routes={micro['by_route']} direct_path={micro['direct_path']}")
    if traffic["recent"]:
        print("recent:")
        for item in traffic["recent"]:
            print(
                f"  {item.get('ts')} {item.get('direction')} {item.get('status') or '-'} "
                f"{item.get('method') or '-'} {item.get('path') or '-'} bytes={item.get('bytes')} route={item.get('route_mode') or '-'}"
            )


def redacted_event(event: Dict[str, Any], *, include_body: bool = False) -> Dict[str, Any]:
    clone = dict(event)
    body = clone.get("body")
    if isinstance(body, dict) and not include_body:
        clone["body"] = {
            "bytes": body.get("bytes"),
            "sha256": body.get("sha256"),
            "sample_sha256": body.get("sample_sha256"),
            "sample_bytes": body.get("sample_bytes"),
            "truncated": body.get("truncated"),
        }
    return clone


def export_csv(events: Iterable[Dict[str, Any]], output: TextIO) -> None:
    fieldnames = ["ts", "direction", "request_id", "method", "host", "path", "status", "route_mode", "content_type", "bytes", "sha256"]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for event in events:
        body = event.get("body") if isinstance(event.get("body"), dict) else {}
        writer.writerow({
            "ts": event.get("ts"),
            "direction": event.get("direction"),
            "request_id": event.get("request_id"),
            "method": event.get("method"),
            "host": event.get("host"),
            "path": event.get("path"),
            "status": event.get("status"),
            "route_mode": event.get("route_mode"),
            "content_type": event.get("content_type"),
            "bytes": body.get("bytes"),
            "sha256": body.get("sha256"),
        })


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Summarize/tail Antigravity proxy data streams.")
    parser.add_argument("--traffic-log", type=Path, default=DEFAULT_TRAFFIC_LOG)
    parser.add_argument("--microproxy-log", type=Path, default=DEFAULT_MICROPROXY_LOG)
    parser.add_argument("--state-file", type=Path, default=DEFAULT_STATE_FILE)
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON summary.")
    sub = parser.add_subparsers(dest="command")

    summary = sub.add_parser("summary", help="Summarize traffic and C microproxy streams.")
    summary.add_argument("--json", action="store_true", dest="summary_json", help="Emit machine-readable JSON summary.")

    tail = sub.add_parser("tail", help="Tail decrypted traffic flow JSONL.")
    tail.add_argument("--from-start", action="store_true")
    tail.add_argument("--include-body", action="store_true", help="Include captured body samples in output.")
    tail.add_argument("--interval", type=float, default=0.5)

    export = sub.add_parser("export", help="Export decrypted traffic flow rows.")
    export.add_argument("--format", choices=["jsonl", "csv"], default="jsonl")
    export.add_argument("--output", type=Path)
    export.add_argument("--include-body", action="store_true", help="Include captured body samples for JSONL export.")

    sub.add_parser("paths", help="Print stream paths and existence checks.")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    command = args.command or "summary"

    if command == "paths":
        payload = {
            "traffic_log": str(args.traffic_log),
            "traffic_log_exists": args.traffic_log.exists(),
            "microproxy_log": str(args.microproxy_log),
            "microproxy_log_exists": args.microproxy_log.exists(),
            "state_file": str(args.state_file),
            "state_file_exists": args.state_file.exists(),
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    if command == "summary":
        summary = summarize(load_jsonl(args.traffic_log), load_jsonl(args.microproxy_log))
        if args.json or getattr(args, "summary_json", False):
            print(json.dumps(summary, indent=2, sort_keys=True))
        else:
            print_human_summary(summary)
        return 0

    if command == "tail":
        for event in follow_jsonl(args.traffic_log, interval=args.interval, from_start=args.from_start):
            print(json.dumps(redacted_event(event, include_body=args.include_body), sort_keys=True), flush=True)
        return 0

    if command == "export":
        events = list(load_jsonl(args.traffic_log))
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            handle: TextIO
            with args.output.open("w", encoding="utf-8", newline="") as handle:
                if args.format == "csv":
                    export_csv(events, handle)
                else:
                    for event in events:
                        handle.write(json.dumps(redacted_event(event, include_body=args.include_body), sort_keys=True) + "\n")
            print(json.dumps({"output": str(args.output), "events": len(events), "format": args.format}, sort_keys=True))
        else:
            if args.format == "csv":
                export_csv(events, sys.stdout)
            else:
                for event in events:
                    print(json.dumps(redacted_event(event, include_body=args.include_body), sort_keys=True))
        return 0

    parser.error(f"unknown command: {command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
