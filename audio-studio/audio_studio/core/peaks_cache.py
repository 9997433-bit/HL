"""Disk cache for waveform peak pyramids (``.pk`` sidecars).

Building a :class:`~audio_studio.core.peaks.PeakPyramid` costs one full pass
over the samples, which is what makes reopening an hour-long file feel slow
even when the audio itself is streamed. The reduced levels are two orders of
magnitude smaller than the audio, so they are written once to a sidecar file
and read back on the next open.

Layout of a ``.pk`` file::

    b"ASPK"            magic
    uint16             format version
    uint32             header length
    <header>           UTF-8 JSON: cache key, geometry, per-level bin counts
    <arrays>           per level, in order: min <f4, max <f4, sumsq <f8, counts <i8

The header carries the cache key of the source file — its size and modification
time, or a content hash when ``AUDIO_STUDIO_PEAK_CACHE_KEY=content`` — so an
edited or replaced source misses instead of drawing a stale waveform. Writes go
through a temporary file in the destination directory and an ``os.replace``, so
a reader never observes a half-written pyramid and a crash mid-write leaves the
previous cache intact.

The cache is strictly an optimisation: every failure path (unreadable sidecar,
truncated file, read-only directory, stale key) degrades to rebuilding the
pyramid in memory. ``AUDIO_STUDIO_PEAK_CACHE=0`` turns it off entirely.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import struct
import tempfile
from collections.abc import Callable
from contextlib import suppress
from pathlib import Path
from typing import Any

import numpy as np

from .peaks import BASE_DECIMATION, PeakPyramid, PyramidLevel

_log = logging.getLogger(__name__)

#: File magic; also the discriminator for a foreign file that ends in ``.pk``.
MAGIC = b"ASPK"

#: Bumped whenever the on-disk layout changes; older files then simply miss.
FORMAT_VERSION = 1

#: Sidecar extension.
SUFFIX = ".pk"

#: Set to ``0``/``false``/``no``/``off`` to disable reads and writes.
ENV_ENABLED = "AUDIO_STUDIO_PEAK_CACHE"

#: Directory to keep sidecars in, instead of next to the audio file.
ENV_DIR = "AUDIO_STUDIO_PEAK_CACHE_DIR"

#: ``stat`` (default) or ``content`` — how a source file is fingerprinted.
ENV_KEY_MODE = "AUDIO_STUDIO_PEAK_CACHE_KEY"

_FALSEY = frozenset({"0", "false", "no", "off"})
_HASH_CHUNK = 1 << 20

_F4 = np.dtype("<f4")
_F8 = np.dtype("<f8")
_I8 = np.dtype("<i8")
_PREAMBLE = struct.Struct("<HI")

#: A pyramid source: the decoded frames, or a callable producing them. The
#: callable form is never invoked on a cache hit, which is what lets a streamed
#: file skip decoding altogether.
SampleProvider = np.ndarray | Callable[[], np.ndarray]


class PeakCacheError(RuntimeError):
    """Raised by :func:`decode` when a ``.pk`` payload is not usable."""


def cache_enabled() -> bool:
    """Whether ``AUDIO_STUDIO_PEAK_CACHE`` leaves the cache switched on."""
    return os.environ.get(ENV_ENABLED, "1").strip().lower() not in _FALSEY


def cache_directory() -> Path | None:
    """Shared sidecar directory from the environment, or ``None`` for sidecars."""
    raw = os.environ.get(ENV_DIR, "").strip()
    return Path(raw).expanduser() if raw else None


def key_mode() -> str:
    """``"content"`` when the environment asks for hashing, else ``"stat"``."""
    raw = os.environ.get(ENV_KEY_MODE, "").strip().lower()
    return "content" if raw in {"content", "hash", "sha256"} else "stat"


def cache_key(path: str | Path, *, mode: str | None = None) -> str:
    """Fingerprint ``path`` so a changed source invalidates its sidecar.

    The default ``stat`` mode costs one ``stat`` call and catches every edit
    that moves the size or the modification time; ``content`` reads the file
    and is what a build system with unreliable timestamps wants.
    """
    path = Path(path)
    chosen = mode or key_mode()
    if chosen == "content":
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(_HASH_CHUNK), b""):
                digest.update(block)
        return f"h1:{digest.hexdigest()}"
    if chosen != "stat":
        raise ValueError(f"unknown cache key mode {chosen!r}")
    stat = path.stat()
    return f"s1:{stat.st_size}:{stat.st_mtime_ns}"


def sidecar_path(path: str | Path, *, cache_dir: str | Path | None = None) -> Path:
    """Where the ``.pk`` for ``path`` lives.

    Next to the audio file by default (``track.wav`` → ``track.wav.pk``). When a
    cache directory is configured the name is disambiguated with a digest of the
    absolute source path, so two ``track.wav`` in different folders never
    collide.
    """
    path = Path(path)
    directory = cache_dir if cache_dir is not None else cache_directory()
    if directory is None:
        return path.with_name(path.name + SUFFIX)
    digest = hashlib.sha256(str(_absolute(path)).encode("utf-8")).hexdigest()[:16]
    return Path(directory) / f"{path.stem}-{digest}{SUFFIX}"


def _absolute(path: Path) -> Path:
    with suppress(OSError):
        return path.resolve()
    return path.absolute()


def _resolve_target(
    source: Path, cache_path: str | Path | None, cache_dir: str | Path | None
) -> Path:
    return Path(cache_path) if cache_path is not None else sidecar_path(source, cache_dir=cache_dir)


# --------------------------------------------------------------- serialisation


def encode(pyramid: PeakPyramid, *, key: str, source: str | None = None) -> bytes:
    """Serialise ``pyramid`` and its ``key`` into the ``.pk`` byte layout."""
    levels: list[dict[str, int]] = []
    blobs: list[bytes] = []
    for level in pyramid.levels:
        levels.append({"decimation": int(level.decimation), "n_bins": level.n_bins})
        blobs.append(np.ascontiguousarray(level.minimum, dtype=_F4).tobytes())
        blobs.append(np.ascontiguousarray(level.maximum, dtype=_F4).tobytes())
        blobs.append(np.ascontiguousarray(level.sumsq, dtype=_F8).tobytes())
        blobs.append(np.ascontiguousarray(level.counts, dtype=_I8).tobytes())

    header: dict[str, Any] = {
        "key": key,
        "n_frames": int(pyramid.n_frames),
        "n_channels": int(pyramid.n_channels),
        "levels": levels,
    }
    if source is not None:
        header["source"] = source
    raw = json.dumps(header, sort_keys=True, separators=(",", ":")).encode("utf-8")

    out = bytearray(MAGIC)
    out += _PREAMBLE.pack(FORMAT_VERSION, len(raw))
    out += raw
    for blob in blobs:
        out += blob
    return bytes(out)


def decode(payload: bytes, *, samples: np.ndarray | None = None) -> tuple[PeakPyramid, str]:
    """Parse a ``.pk`` payload into a pyramid and the key it was written with.

    Raises :class:`PeakCacheError` for anything that is not a well-formed
    payload of a supported version; callers that treat a bad cache as a miss
    should use :func:`read` instead.
    """
    head = _PREAMBLE.size + len(MAGIC)
    if len(payload) < head or payload[: len(MAGIC)] != MAGIC:
        raise PeakCacheError("not a peak cache file")
    version, header_len = _PREAMBLE.unpack_from(payload, len(MAGIC))
    if version != FORMAT_VERSION:
        raise PeakCacheError(f"unsupported peak cache version {version}")
    if len(payload) < head + header_len:
        raise PeakCacheError("truncated peak cache header")

    try:
        header = json.loads(payload[head : head + header_len].decode("utf-8"))
        key = str(header["key"])
        n_frames = int(header["n_frames"])
        n_channels = int(header["n_channels"])
        meta = list(header["levels"])
    except (KeyError, TypeError, ValueError, UnicodeDecodeError) as exc:
        raise PeakCacheError(f"invalid peak cache header: {exc}") from exc

    offset = head + header_len
    levels: list[PyramidLevel] = []
    try:
        for entry in meta:
            decimation = int(entry["decimation"])
            n_bins = int(entry["n_bins"])
            shape = (n_bins, n_channels)
            minimum, offset = _read_array(payload, offset, _F4, shape)
            maximum, offset = _read_array(payload, offset, _F4, shape)
            sumsq, offset = _read_array(payload, offset, _F8, shape)
            counts, offset = _read_array(payload, offset, _I8, (n_bins,))
            levels.append(
                PyramidLevel(
                    decimation,
                    minimum.astype(np.float32),
                    maximum.astype(np.float32),
                    sumsq.astype(np.float64),
                    counts.astype(np.int64),
                )
            )
    except (KeyError, TypeError, ValueError) as exc:
        raise PeakCacheError(f"invalid peak cache level: {exc}") from exc
    if offset != len(payload):
        raise PeakCacheError("peak cache carries trailing data")

    try:
        pyramid = PeakPyramid.from_levels(
            levels, n_frames=n_frames, n_channels=n_channels, samples=samples
        )
    except ValueError as exc:
        raise PeakCacheError(f"inconsistent peak cache: {exc}") from exc
    return pyramid, key


def _read_array(
    payload: bytes, offset: int, dtype: np.dtype[Any], shape: tuple[int, ...]
) -> tuple[np.ndarray, int]:
    count = 1
    for dim in shape:
        if dim < 0:
            raise ValueError(f"negative dimension {dim}")
        count *= dim
    end = offset + count * dtype.itemsize
    if end > len(payload):
        raise ValueError("truncated array")
    if count == 0:
        return np.empty(shape, dtype=dtype), end
    array = np.frombuffer(payload, dtype=dtype, count=count, offset=offset).reshape(shape)
    return array, end


# ------------------------------------------------------------------- file I/O


def write(
    path: str | Path,
    pyramid: PeakPyramid,
    *,
    key: str | None = None,
    cache_path: str | Path | None = None,
    cache_dir: str | Path | None = None,
) -> Path | None:
    """Write the sidecar for ``path`` atomically; ``None`` if that failed.

    A cache that cannot be written (read-only medium, full disk, a race with
    another process) is not an error worth surfacing — the caller already holds
    the pyramid it wanted. ``cache_path`` names the sidecar outright, for a
    caller such as the project store that records where it put it.
    """
    source = Path(path)
    target = _resolve_target(source, cache_path, cache_dir)
    try:
        payload = encode(pyramid, key=key or cache_key(source), source=source.name)
    except OSError as exc:  # the source vanished between build and write
        _log.debug("peak cache key unavailable for %s: %s", source, exc)
        return None
    try:
        _atomic_write(target, payload)
    except OSError as exc:
        _log.debug("peak cache write failed for %s: %s", target, exc)
        return None
    return target


def read(
    path: str | Path,
    *,
    samples: np.ndarray | None = None,
    key: str | None = None,
    cache_path: str | Path | None = None,
    cache_dir: str | Path | None = None,
) -> PeakPyramid | None:
    """Load the sidecar for ``path``, or ``None`` on a miss.

    A missing, unreadable, corrupt, foreign or stale file is a miss; nothing
    here raises. Passing ``samples`` both restores sample-accurate zoom and
    checks the cached geometry against the audio actually in hand.
    """
    source = Path(path)
    target = _resolve_target(source, cache_path, cache_dir)
    try:
        payload = target.read_bytes()
    except OSError:
        return None

    try:
        expected = key if key is not None else cache_key(source)
    except OSError as exc:
        _log.debug("cannot fingerprint %s: %s", source, exc)
        return None

    try:
        pyramid, stored = decode(payload, samples=samples)
    except PeakCacheError as exc:
        _log.debug("ignoring peak cache %s: %s", target, exc)
        return None
    if stored != expected:
        _log.debug("peak cache %s is stale", target)
        return None
    return pyramid


def discard(
    path: str | Path,
    *,
    cache_path: str | Path | None = None,
    cache_dir: str | Path | None = None,
) -> bool:
    """Delete the sidecar for ``path``; ``True`` when one was removed."""
    target = _resolve_target(Path(path), cache_path, cache_dir)
    try:
        target.unlink()
    except OSError:
        return False
    return True


def _atomic_write(target: Path, payload: bytes) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    handle, name = tempfile.mkstemp(
        dir=str(target.parent), prefix=f".{target.name}.", suffix=".tmp"
    )
    temp = Path(name)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, target)
    except BaseException:
        with suppress(OSError):
            temp.unlink()
        raise


# ------------------------------------------------------------------ front door


def cached_pyramid(
    path: str | Path | None,
    samples: SampleProvider,
    *,
    base_decimation: int = BASE_DECIMATION,
    enabled: bool | None = None,
    cache_path: str | Path | None = None,
    cache_dir: str | Path | None = None,
) -> PeakPyramid:
    """Return the pyramid for ``path``, from disk when it is still valid.

    On a miss the pyramid is built from ``samples`` and written back. ``samples``
    may be a callable, which is only invoked on a miss; a hit then yields a
    pyramid without source frames, so a zoomed-in view resolves to
    ``base_decimation`` frames per bin rather than to individual samples.

    ``path`` may be ``None`` (an unsaved document), and ``enabled`` overrides
    the ``AUDIO_STUDIO_PEAK_CACHE`` environment switch.
    """
    use_cache = cache_enabled() if enabled is None else bool(enabled)
    source = Path(path) if path is not None else None
    in_hand = samples if isinstance(samples, np.ndarray) else None

    key: str | None = None
    if use_cache and source is not None:
        try:
            key = cache_key(source)
        except OSError as exc:  # not a real file: an in-memory or generated clip
            _log.debug("peak cache skipped for %s: %s", source, exc)
            use_cache = False

    if use_cache and source is not None:
        hit = read(source, samples=in_hand, key=key, cache_path=cache_path, cache_dir=cache_dir)
        if hit is not None:
            return hit

    data = samples() if callable(samples) else samples
    pyramid = PeakPyramid(data, base_decimation=base_decimation)
    if use_cache and source is not None:
        write(source, pyramid, key=key, cache_path=cache_path, cache_dir=cache_dir)
    return pyramid
