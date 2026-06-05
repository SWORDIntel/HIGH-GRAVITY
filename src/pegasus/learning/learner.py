"""Non-blocking Pegasus proxy-flow learner with optional autoresearch support."""

import importlib
import importlib.util
import json
import time
from typing import Any, Callable, Dict


def _noop_train_step(flow_data: Dict[str, Any]) -> None:
    return None


def _resolve_train_step() -> Callable[[Dict[str, Any]], Any]:
    if importlib.util.find_spec("autoresearch") is None or importlib.util.find_spec("autoresearch.train") is None:
        return _noop_train_step
    module = importlib.import_module("autoresearch.train")
    return getattr(module, "train_step", _noop_train_step)


TRAIN_STEP = _resolve_train_step()


class PegasusLearner:
    def __init__(self, gsl: Any) -> None:
        self.gsl = gsl

    def ingest_proxy_flow(self, request: dict, response: bytes) -> None:
        """Process a flow without allowing optional training failures to block it."""
        flow_data = {
            "prompt": json.dumps(request.get("messages", [])),
            "response": response.decode(errors="ignore"),
            "timestamp": time.time(),
        }
        try:
            TRAIN_STEP(flow_data)
        except Exception:
            return None
