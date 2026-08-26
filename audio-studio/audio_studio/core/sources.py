"""Spec-facing aliases for :mod:`audio_studio.core.sample_source`.

The Round 2 convergence audit (``.agent_workspace/round2/fable-convergence-audit.md``
§4.1) freezes this module path and the names ``ArraySource`` and
``FileStreamSource``. The implementation landed under the longer, more explicit
``sample_source`` spelling, so both vocabularies are kept alive here rather than
forcing every downstream caller to pick one: the objects are identical, not
wrappers, so ``isinstance`` and identity checks hold across either import.

Composite sources the audit also freezes (``RegionSource``, ``LoopSource``,
``ChunkTableSource``) are not implemented yet; the transport still handles
looping and region playback itself.
"""

from __future__ import annotations

from .edit_session import EditSession
from .sample_source import (
    BaseSampleSource,
    MemorySampleSource,
    SampleSource,
    StreamingSampleSource,
    open_source,
)

#: An in-memory clip. ``exact`` is ``True``: reads never touch the disk.
ArraySource = MemorySampleSource

#: A file read a block at a time through libsndfile. ``exact`` is ``False``.
FileStreamSource = StreamingSampleSource

#: An edit document, which satisfies the protocol directly.
ChunkTableSource = EditSession

__all__ = [
    "ArraySource",
    "BaseSampleSource",
    "ChunkTableSource",
    "FileStreamSource",
    "MemorySampleSource",
    "SampleSource",
    "StreamingSampleSource",
    "open_source",
]
