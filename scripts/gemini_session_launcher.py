#!/usr/bin/env python3
"""
Compatibility shim for tests/importers that expect scripts/gemini_session_launcher.py.
"""

from pathlib import Path
import runpy

_MODULE_PATH = Path(__file__).resolve().parent.parent / "bin" / "gemini_session_launcher.py"
globals().update(runpy.run_path(str(_MODULE_PATH)))

