"""Schema helpers for append-only microproxy JSONL events."""

from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
from typing import Dict
from typing import Iterable
from typing import Iterator
from typing import Mapping
from typing import Optional
from typing import Sequence
from typing import TextIO
from typing import Union


SCHEMA_VERSION = 1

EVENT_DETAIL_REQUIREMENTS: Dict[str, Sequence[str]] = {
    "request_seen": ("method", "path"),
    "route_selected": ("route",),
    "stream_started": ("stream_id",),
    "stream_finished": ("stream_id", "status_code"),
    "hot_path_candidate": ("candidate", "route"),
    "proto_observed": ("proto",),
    "mutation_applied": ("mutation",),
    "khoj_injected": ("injection_id",),
    "upstream_error": ("upstream", "error_type", "message"),
    "backpressure": ("active_streams", "max_active_streams"),
}

EVENT_NAMES = frozenset(EVENT_DETAIL_REQUIREMENTS)
REQUIRED_ENVELOPE_FIELDS = (
    "schema_version",
    "event",
    "ts",
    "request_id",
    "details",
)

PathLike = Union[str, Path]


class EventValidationError(ValueError):
    """Raised when a microproxy event does not match the published schema."""


def utc_timestamp() -> str:
    """Return an RFC 3339 UTC timestamp with millisecond precision."""

    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def make_event(
    event: str,
    request_id: str,
    details: Optional[Mapping[str, Any]] = None,
    *,
    ts: Optional[str] = None,
    schema_version: int = SCHEMA_VERSION,
    **metadata: Any,
) -> Dict[str, Any]:
    """Build and validate a microproxy event envelope."""

    envelope: Dict[str, Any] = {
        "schema_version": schema_version,
        "event": event,
        "ts": ts or utc_timestamp(),
        "request_id": request_id,
        "details": dict(details or {}),
    }
    for key, value in metadata.items():
        if value is not None:
            envelope[key] = value
    validate_event(envelope)
    return envelope


def validate_event(event: Mapping[str, Any]) -> None:
    """Validate an event object against the append-only JSONL schema."""

    if not isinstance(event, Mapping):
        raise EventValidationError("event must be an object")

    for field in REQUIRED_ENVELOPE_FIELDS:
        if field not in event:
            raise EventValidationError(f"missing envelope field: {field}")

    if (
        type(event["schema_version"]) is not int
        or event["schema_version"] != SCHEMA_VERSION
    ):
        raise EventValidationError(
            f"unsupported schema_version: {event['schema_version']!r}"
        )

    event_name = event["event"]
    if not isinstance(event_name, str):
        raise EventValidationError("event must be a string")
    if event_name not in EVENT_NAMES:
        raise EventValidationError(f"unsupported event: {event_name!r}")

    if not isinstance(event["ts"], str) or not event["ts"]:
        raise EventValidationError("ts must be a non-empty string")
    if not isinstance(event["request_id"], str) or not event["request_id"]:
        raise EventValidationError("request_id must be a non-empty string")
    if not isinstance(event["details"], Mapping):
        raise EventValidationError("details must be an object")

    for field in EVENT_DETAIL_REQUIREMENTS[event_name]:
        if field not in event["details"]:
            raise EventValidationError(
                f"missing details field for {event_name}: {field}"
            )

    try:
        json.dumps(event, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError) as exc:
        raise EventValidationError(
            f"event must be JSON serializable: {exc}"
        ) from exc


def event_to_jsonl(event: Mapping[str, Any]) -> str:
    """Serialize one validated event as a compact JSONL row."""

    validate_event(event)
    return json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n"


def event_from_jsonl(line: str) -> Dict[str, Any]:
    """Parse and validate one JSONL row."""

    try:
        event = json.loads(line)
    except json.JSONDecodeError as exc:
        raise EventValidationError(f"invalid JSONL event: {exc}") from exc
    validate_event(event)
    return event


def append_event(path: PathLike, event: Mapping[str, Any]) -> None:
    """Append one event row to a JSONL file."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(event_to_jsonl(event))


def iter_events(
    source: Union[PathLike, TextIO],
    *,
    skip_invalid: bool = False,
) -> Iterator[Dict[str, Any]]:
    """Yield validated events from a JSONL file path or open text stream."""

    close_after = False
    if hasattr(source, "read"):
        handle = source  # type: ignore[assignment]
    else:
        handle = Path(source).open("r", encoding="utf-8")
        close_after = True

    try:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                yield event_from_jsonl(line)
            except EventValidationError:
                if skip_invalid:
                    continue
                raise EventValidationError(
                    f"invalid event on line {line_number}"
                )
    finally:
        if close_after:
            handle.close()


def read_events(
    source: Union[PathLike, TextIO],
    *,
    skip_invalid: bool = False,
) -> Dict[str, Any]:
    """Read validated events and count skipped invalid rows.

    This is intended for control-plane consumers that need an explicit invalid
    row count in their JSON summary instead of silently dropping bad rows.
    """

    close_after = False
    if hasattr(source, "read"):
        handle = source  # type: ignore[assignment]
    else:
        handle = Path(source).open("r", encoding="utf-8")
        close_after = True

    events = []
    invalid_rows = 0
    try:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                events.append(event_from_jsonl(line))
            except EventValidationError as exc:
                if skip_invalid:
                    invalid_rows += 1
                    continue
                raise EventValidationError(
                    f"invalid event on line {line_number}: {exc}"
                ) from exc
    finally:
        if close_after:
            handle.close()

    return {
        "events": events,
        "invalid_rows": invalid_rows,
    }


def summarize_events(events: Iterable[Mapping[str, Any]]) -> Dict[str, int]:
    """Return event counts keyed by event name after validating each event."""

    counts = {name: 0 for name in sorted(EVENT_NAMES)}
    for event in events:
        validate_event(event)
        counts[event["event"]] += 1
    return counts


def summarize_routes(events: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
    """Summarize observed route choices and optional route classifications.

    A route classification can be carried as ``details["classification"]`` or
    ``details["route_class"]``. When neither exists, the route name is used as
    the classification so early producers still produce useful summaries.
    """

    route_counts = Counter()
    classification_counts = Counter()
    request_routes: Dict[str, Dict[str, str]] = {}

    for event in events:
        validate_event(event)
        if event["event"] != "route_selected":
            continue

        details = event["details"]
        route = str(details["route"])
        classification = str(
            details.get("classification")
            or details.get("route_class")
            or route
        )
        request_id = str(event["request_id"])

        route_counts[route] += 1
        classification_counts[classification] += 1
        request_routes[request_id] = {
            "route": route,
            "classification": classification,
        }

    return {
        "total": sum(route_counts.values()),
        "routes": dict(sorted(route_counts.items())),
        "classifications": dict(sorted(classification_counts.items())),
        "requests": dict(sorted(request_routes.items())),
    }


def summarize_stream_lifecycle(
    events: Iterable[Mapping[str, Any]]
) -> Dict[str, Any]:
    """Summarize stream start/finish lifecycle events from validated rows."""

    streams: Dict[str, Dict[str, Any]] = {}
    status_codes = Counter()
    quota_exhausted_signals = 0
    connect_error_signals = 0

    for event in events:
        validate_event(event)
        if event["event"] not in ("stream_started", "stream_finished"):
            continue

        details = event["details"]
        stream_id = str(details["stream_id"])
        stream = streams.setdefault(
            stream_id,
            {
                "stream_id": stream_id,
                "request_id": str(event["request_id"]),
                "started_at": None,
                "finished_at": None,
                "status_code": None,
                "duration_ms": None,
            },
        )
        stream["request_id"] = str(event["request_id"])

        if event["event"] == "stream_started":
            stream["started_at"] = event["ts"]
            continue

        status_code = details["status_code"]
        stream["finished_at"] = event["ts"]
        stream["status_code"] = status_code
        status_codes[str(status_code)] += 1
        if details.get("quota_exhausted_signal") is True:
            quota_exhausted_signals += 1
        if details.get("connect_error_signal") is True:
            connect_error_signals += 1

        duration_ms = _duration_ms(stream["started_at"], stream["finished_at"])
        if duration_ms is not None:
            stream["duration_ms"] = duration_ms

    started = sum(1 for stream in streams.values() if stream["started_at"])
    finished = sum(1 for stream in streams.values() if stream["finished_at"])
    open_streams = sorted(
        stream_id
        for stream_id, stream in streams.items()
        if stream["started_at"] and not stream["finished_at"]
    )
    finish_without_start = sorted(
        stream_id
        for stream_id, stream in streams.items()
        if stream["finished_at"] and not stream["started_at"]
    )

    return {
        "streams_started": started,
        "streams_finished": finished,
        "streams_open": len(open_streams),
        "streams_finished_without_start": len(finish_without_start),
        "open_stream_ids": open_streams,
        "finished_without_start_ids": finish_without_start,
        "status_codes": dict(sorted(status_codes.items())),
        "quota_exhausted_signals": quota_exhausted_signals,
        "connect_error_signals": connect_error_signals,
        "streams": dict(sorted(streams.items())),
    }


def summarize_upstream_errors(
    events: Iterable[Mapping[str, Any]]
) -> Dict[str, Any]:
    """Summarize upstream failures from validated event rows."""

    upstream_counts = Counter()
    error_type_counts = Counter()
    request_errors: Dict[str, Dict[str, str]] = {}

    for event in events:
        validate_event(event)
        if event["event"] != "upstream_error":
            continue

        details = event["details"]
        upstream = str(details["upstream"])
        error_type = str(details["error_type"])
        message = str(details["message"])
        request_id = str(event["request_id"])

        upstream_counts[upstream] += 1
        error_type_counts[error_type] += 1
        request_errors[request_id] = {
            "upstream": upstream,
            "error_type": error_type,
            "message": message,
        }

    return {
        "total": sum(upstream_counts.values()),
        "upstreams": dict(sorted(upstream_counts.items())),
        "error_types": dict(sorted(error_type_counts.items())),
        "requests": dict(sorted(request_errors.items())),
    }


def summarize_backpressure(events: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
    """Summarize C-edge parent-side stream throttling events."""

    total = 0
    max_active_seen = 0
    max_configured = 0
    wait_ms_total = 0
    recent = []

    for event in events:
        validate_event(event)
        if event["event"] != "backpressure":
            continue

        details = event["details"]
        active_streams = int(details.get("active_streams", 0) or 0)
        configured = int(details.get("max_active_streams", 0) or 0)
        wait_ms = int(details.get("wait_ms", 0) or 0)
        total += 1
        max_active_seen = max(max_active_seen, active_streams)
        max_configured = max(max_configured, configured)
        wait_ms_total += wait_ms
        recent.append(
            {
                "ts": event.get("ts"),
                "request_id": event.get("request_id"),
                "active_streams": active_streams,
                "max_active_streams": configured,
                "wait_ms": wait_ms,
            }
        )

    return {
        "total": total,
        "max_active_seen": max_active_seen,
        "max_active_streams": max_configured,
        "wait_ms_total": wait_ms_total,
        "recent": recent[-10:],
    }


def summarize_requests(events: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
    """Count request ids observed across lifecycle, route, and error events."""

    request_ids = set()
    request_seen_ids = set()
    routed_ids = set()
    stream_started_ids = set()
    stream_finished_ids = set()
    upstream_error_ids = set()

    for event in events:
        validate_event(event)
        request_id = str(event["request_id"])
        request_ids.add(request_id)

        event_name = event["event"]
        if event_name == "request_seen":
            request_seen_ids.add(request_id)
        elif event_name == "route_selected":
            routed_ids.add(request_id)
        elif event_name == "stream_started":
            stream_started_ids.add(request_id)
        elif event_name == "stream_finished":
            stream_finished_ids.add(request_id)
        elif event_name == "upstream_error":
            upstream_error_ids.add(request_id)

    return {
        "total": len(request_ids),
        "request_seen": len(request_seen_ids),
        "routed": len(routed_ids),
        "stream_started": len(stream_started_ids),
        "stream_finished": len(stream_finished_ids),
        "upstream_errors": len(upstream_error_ids),
    }


def summarize_observer_events(
    events: Iterable[Mapping[str, Any]]
) -> Dict[str, Any]:
    """Return passive observer summaries from one event iterable."""

    rows = list(events)
    return {
        "events": summarize_events(rows),
        "requests": summarize_requests(rows),
        "routes": summarize_routes(rows),
        "streams": summarize_stream_lifecycle(rows),
        "upstream_errors": summarize_upstream_errors(rows),
        "backpressure": summarize_backpressure(rows),
    }


def _duration_ms(started_at: Any, finished_at: Any) -> Optional[int]:
    if not isinstance(started_at, str) or not isinstance(finished_at, str):
        return None

    try:
        started = _parse_utc_timestamp(started_at)
        finished = _parse_utc_timestamp(finished_at)
    except ValueError:
        return None

    return int((finished - started).total_seconds() * 1000)


def _parse_utc_timestamp(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed
