"""RF64/W64 large-container detection and the in-memory editing budget.

Plain RIFF/WAV stores chunk sizes in 32 bits, so a recording cannot cross 4 GB
without switching container: RF64 (EBU Tech 3306, with the BW64 broadcast
profile of ITU-R BS.2088) and Sony Wave64 both exist purely to lift that
limit. libsndfile decodes them all, so :class:`~.sample_source.
StreamingSampleSource` can already *play* them — what this module adds is the
policy around such files:

* recognising the containers cheaply from their header magic, without
  involving a decoder (:func:`sniff_container`, :func:`is_large_container`);
* an explicit memory budget, so a file whose decoded float32 form would not
  fit comfortably in RAM is refused by the full-decode/:class:`~.edit_session.
  EditSession` path with an error that points at streaming playback instead of
  an opaque ``MemoryError`` minutes later (:func:`check_memory_budget`);
* the open-time decision itself (:func:`should_stream`).

Frame counts are handled as plain Python ``int`` throughout: an RF64 capture
can exceed 2**31 frames, which overflows the 32-bit counts a RIFF-era API
would assume, and Python integers are arbitrary precision so nothing here can
wrap.
"""

from __future__ import annotations

from pathlib import Path

from .loader import AudioLoadError

#: Decoded float32 size above which a file is not loaded fully into memory.
#: 500 MB is ~48 minutes of stereo 48 kHz — past that, an EditSession (whose
#: undo history multiplies the resident set) stops being a good idea.
DEFAULT_MEMORY_BUDGET_BYTES: int = 500 * 1024 * 1024

#: Bytes of decoded storage per frame per channel (everything becomes float32).
BYTES_PER_SAMPLE: int = 4

#: Extensions that imply a 64-bit container even when the header is unreadable.
LARGE_CONTAINER_SUFFIXES: frozenset[str] = frozenset({".rf64", ".w64"})

#: Chunk ids at offset 0 of an RF64/BW64 file (EBU Tech 3306 / ITU-R BS.2088).
_RF64_MAGIC = b"RF64"
_BW64_MAGIC = b"BW64"

#: The first 16 bytes of a Sony Wave64 file: the 'riff' GUID.
_W64_GUID = bytes(
    (0x72, 0x69, 0x66, 0x66, 0x2E, 0x91, 0xCF, 0x11,
     0xA5, 0xD6, 0x28, 0xDB, 0x04, 0xC1, 0x00, 0x00)
)


class MemoryBudgetError(AudioLoadError):
    """A file's decoded size exceeds the in-memory editing budget.

    The message always names the alternative — streaming playback — because
    the caller that trips this is invariably a "just open the file" path.
    """


def sniff_container(path: str | Path) -> str | None:
    """Identify a 64-bit container from its first 16 bytes.

    Returns ``"RF64"``, ``"BW64"`` or ``"W64"``, or ``None`` when the file is
    something else (including a plain WAV) or cannot be read. No decoder is
    involved, so this is safe to call on arbitrary paths.
    """
    try:
        with open(path, "rb") as handle:
            head = handle.read(16)
    except OSError:
        return None
    if head[:4] == _RF64_MAGIC:
        return "RF64"
    if head[:4] == _BW64_MAGIC:
        return "BW64"
    if head == _W64_GUID:
        return "W64"
    return None


def is_large_container(path: str | Path) -> bool:
    """True when ``path`` is an RF64/BW64/W64 file.

    The header magic decides when the file is readable; the extension is the
    fallback for a path that does not exist (yet) or cannot be opened, which
    is deliberately conservative — a mislabelled ``.rf64`` streams needlessly
    rather than a real one being slurped.
    """
    path = Path(path)
    if sniff_container(path) is not None:
        return True
    return path.suffix.lower() in LARGE_CONTAINER_SUFFIXES


def estimated_decoded_bytes(path: str | Path) -> int:
    """Size of ``path`` once decoded to float32, from the header alone.

    ``soundfile`` reports the frame count as a 64-bit value; multiplied out in
    Python ints there is no overflow even for counts past 2**31.
    """
    import soundfile as sf

    path = Path(path)
    try:
        info = sf.info(str(path))
    except Exception as exc:  # noqa: BLE001 - normalised into AudioLoadError
        raise AudioLoadError(f"Cannot read audio metadata from {path}: {exc}") from exc
    return int(info.frames) * int(info.channels) * BYTES_PER_SAMPLE


def check_memory_budget(
    path: str | Path,
    *,
    budget_bytes: int = DEFAULT_MEMORY_BUDGET_BYTES,
) -> int:
    """Refuse to fully decode ``path`` when it would exceed ``budget_bytes``.

    Returns the estimated decoded size when it fits. Raises
    :class:`MemoryBudgetError` — a :class:`~.loader.AudioLoadError`, so
    existing error handling catches it — when it does not, with a message
    that directs the user to streaming playback.
    """
    if budget_bytes <= 0:
        raise ValueError(f"budget_bytes must be positive, got {budget_bytes}")
    path = Path(path)
    estimate = estimated_decoded_bytes(path)
    if estimate > budget_bytes:
        raise MemoryBudgetError(
            f"{path.name} would decode to ~{estimate / 2**20:,.0f} MiB of float32 "
            f"samples, over the {budget_bytes / 2**20:,.0f} MiB in-memory editing "
            "budget. Open it for streaming playback instead — "
            "AudioEngine.open_stream() / StreamingSampleSource read the file a "
            "block at a time and never hold it whole."
        )
    return estimate


def should_stream(
    path: str | Path,
    *,
    budget_bytes: int = DEFAULT_MEMORY_BUDGET_BYTES,
) -> bool:
    """Decide, at open time, whether ``path`` must bypass the in-memory path.

    The decision is by decoded size, not by container: a two-minute RF64 fits
    in memory and edits like any WAV. Only when the header cannot be probed
    does the container itself tip the scale — an unreadable 64-bit container
    is presumed to be large, which is the reason such files exist.
    """
    try:
        return estimated_decoded_bytes(path) > budget_bytes
    except AudioLoadError:
        return is_large_container(path)


__all__ = [
    "BYTES_PER_SAMPLE",
    "DEFAULT_MEMORY_BUDGET_BYTES",
    "LARGE_CONTAINER_SUFFIXES",
    "MemoryBudgetError",
    "check_memory_budget",
    "estimated_decoded_bytes",
    "is_large_container",
    "should_stream",
    "sniff_container",
]
