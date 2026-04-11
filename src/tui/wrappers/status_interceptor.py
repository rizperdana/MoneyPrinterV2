"""
Status interceptor — monkey-patches src/status.py to redirect output to the TUI.

The YouTube.py module has 251+ status.* calls. We intercept them here
rather than rewriting them — the interceptor routes them to LogLine messages.
"""

import sys
import os

# Add src to path for status import
_src_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

import status as _status_module
from textual.app import App
from tui.events import LogLine

_app_ref: App | None = None
_originals: dict = {}


def attach(app: App) -> None:
    """Call once when TUI starts. Monkey-patches status module."""
    global _app_ref
    _app_ref = app

    # Save originals before patching
    for fn_name in ("info", "success", "warning", "error"):
        if hasattr(_status_module, fn_name):
            _originals[fn_name] = getattr(_status_module, fn_name)

    # Patch each function — accept **kwargs to handle show_emoji etc.
    _status_module.info = lambda msg, **kw: _emit("info", msg)
    _status_module.success = lambda msg, **kw: _emit("success", msg)
    _status_module.warning = lambda msg, **kw: _emit("warn", msg)
    _status_module.error = lambda msg, **kw: _emit("error", msg)


def detach() -> None:
    """Restore originals on TUI exit."""
    for fn_name, fn in _originals.items():
        setattr(_status_module, fn_name, fn)
    _originals.clear()


def _emit(level: str, msg: str) -> None:
    """Post a LogLine message to the TUI app (thread-safe)."""
    if _app_ref and _app_ref.is_running:
        try:
            _app_ref.call_from_thread(lambda: _app_ref.post_message(LogLine(level, str(msg))))
        except Exception:
            # If TUI isn't ready yet, silently drop
            pass
