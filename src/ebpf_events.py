"""Read-only eBPF telemetry compatibility surface."""

from pathlib import Path
from typing import Any, Dict, Optional


def read_summary(path: Optional[Path] = None) -> Dict[str, Any]:
    """Return an empty summary when no eBPF event collector is configured."""
    source = Path(path) if path else None
    return {"available": bool(source and source.exists()), "source": str(source) if source else None, "events": 0}
