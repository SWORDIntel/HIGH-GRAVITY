#!/usr/bin/env python3
"""Read passive microproxy JSONL events and print observer summaries."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any
from typing import Dict
from typing import Optional
from typing import Sequence


REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from microproxy.events import EventValidationError  # noqa: E402
from microproxy.events import read_events  # noqa: E402
from microproxy.events import summarize_observer_events  # noqa: E402


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Summarize append-only microproxy JSONL events.",
    )
    parser.add_argument(
        "path",
        help="Path to a microproxy JSONL event file.",
    )
    parser.add_argument(
        "--skip-invalid",
        action="store_true",
        help=(
            "Skip malformed rows instead of failing on the first invalid row."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the full summary as JSON.",
    )
    parser.add_argument(
        "--missing-ok",
        action="store_true",
        help="Treat a missing event file as an empty event stream.",
    )
    args = parser.parse_args(argv)

    try:
        read_result = read_events(args.path, skip_invalid=args.skip_invalid)
        source_exists = True
    except FileNotFoundError as exc:
        if not args.missing_ok:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        read_result = {
            "events": [],
            "invalid_rows": 0,
        }
        source_exists = False
    except (OSError, EventValidationError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    summary = summarize_observer_events(read_result["events"])
    summary["reader"] = {
        "source": str(Path(args.path)),
        "source_exists": source_exists,
        "rows": len(read_result["events"]),
        "invalid_rows": read_result["invalid_rows"],
    }

    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print_text_summary(summary)
    return 0


def print_text_summary(summary: Dict[str, Any]) -> None:
    reader = summary.get("reader")
    if reader:
        print(f"Source: {reader['source']}")
        if not reader["source_exists"]:
            print("  missing: treated as empty stream")
        print(f"Rows: {reader['rows']}")
        if reader["invalid_rows"]:
            print(f"Invalid rows skipped: {reader['invalid_rows']}")

    event_total = sum(summary["events"].values())
    print(f"Events: {event_total}")
    for name, count in summary["events"].items():
        if count:
            print(f"  {name}: {count}")

    requests = summary["requests"]
    print("Requests:")
    print(f"  total: {requests['total']}")
    print(f"  seen: {requests['request_seen']}")
    print(f"  routed: {requests['routed']}")
    print(f"  stream_started: {requests['stream_started']}")
    print(f"  stream_finished: {requests['stream_finished']}")
    print(f"  upstream_errors: {requests['upstream_errors']}")

    routes = summary["routes"]
    print(f"Routes: {routes['total']}")
    for route, count in routes["routes"].items():
        print(f"  {route}: {count}")

    if routes["classifications"]:
        print("Route classifications:")
        for classification, count in routes["classifications"].items():
            print(f"  {classification}: {count}")

    streams = summary["streams"]
    print("Streams:")
    print(f"  started: {streams['streams_started']}")
    print(f"  finished: {streams['streams_finished']}")
    print(f"  open: {streams['streams_open']}")
    if streams["streams_finished_without_start"]:
        print(
            "  finished_without_start: "
            f"{streams['streams_finished_without_start']}"
        )

    if streams["status_codes"]:
        print("Status codes:")
        for status_code, count in streams["status_codes"].items():
            print(f"  {status_code}: {count}")

    upstream_errors = summary["upstream_errors"]
    print(f"Upstream errors: {upstream_errors['total']}")
    if upstream_errors["upstreams"]:
        print("Upstreams:")
        for upstream, count in upstream_errors["upstreams"].items():
            print(f"  {upstream}: {count}")
    if upstream_errors["error_types"]:
        print("Error types:")
        for error_type, count in upstream_errors["error_types"].items():
            print(f"  {error_type}: {count}")


if __name__ == "__main__":
    raise SystemExit(main())
