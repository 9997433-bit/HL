"""Garbage-collector discipline for real-time playback sessions."""

from __future__ import annotations

import gc
import os
from collections.abc import Callable

RT_GC_ENV_VAR = "AUDIO_STUDIO_RT_GC"

__all__ = ["RT_GC_ENV_VAR", "enter_realtime_mode", "leave_realtime_mode"]


def _enabled() -> bool:
    """Whether playback should manage the cyclic collector."""
    return os.environ.get(RT_GC_ENV_VAR, "1").strip() != "0"


def _gc_method(name: str) -> Callable[[], object] | None:
    """Return an optional GC API without excluding older Python runtimes."""
    method = getattr(gc, name, None)
    return method if callable(method) else None


def enter_realtime_mode() -> None:
    """Collect existing garbage, then freeze the long-lived object graph."""
    if not _enabled():
        return
    gc.collect()
    freeze = _gc_method("freeze")
    if freeze is not None:  # ``gc.freeze`` was added in Python 3.7.
        freeze()


def leave_realtime_mode() -> None:
    """Return frozen objects to the oldest generation during engine shutdown."""
    if not _enabled():
        return
    unfreeze = _gc_method("unfreeze")
    if unfreeze is not None:
        unfreeze()
