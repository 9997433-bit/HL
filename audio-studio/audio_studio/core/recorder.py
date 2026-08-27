"""Input-device backends and crash-safe Broadcast Wave recording.

Like :mod:`audio_studio.core.output`, this module keeps PortAudio behind a
small Qt-free interface. Hardware callbacks publish float32 blocks while the
base class owns lifecycle and thread-safe accumulation. WAV targets are
streamed as PCM-24 Broadcast Wave files: a ``bext`` chunk is present from the
moment the temporary file is created, headers are checkpointed periodically,
and a successful stop atomically renames the file into place.
"""

from __future__ import annotations

import json
import os
import shutil
import struct
import tempfile
import threading
import time
from abc import ABC, abstractmethod
from collections.abc import Iterable, Iterator, Mapping
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, BinaryIO

import numpy as np

from .loader import save_audio
from .output import DEFAULT_BLOCK_SIZE, _quiet_native_stderr
from .types import SAMPLE_DTYPE, AudioBuffer

_PCM_24_MAX = (1 << 23) - 1
_PCM_24_MIN = -(1 << 23)
_BEXT_FIXED_SIZE = 602
_DEFAULT_FLUSH_INTERVAL = 1.0
_WAV_EXTENSIONS = frozenset({".wav", ".wave"})
_TAKE_REGISTRY_VERSION = 1
_TAKES_JSON = "takes.json"


class RecorderDeviceError(RuntimeError):
    """Raised when an input device cannot be opened or started."""


class TakeRegistryError(RuntimeError):
    """Raised when take metadata cannot be read or validated."""


@dataclass(frozen=True, slots=True)
class Take:
    """One numbered recording in a session."""

    number: int
    path: Path
    created_at: str
    sample_rate: int
    channels: int
    frames: int
    metadata: dict[str, Any]

    @property
    def name(self) -> str:
        return f"Take {self.number:03d}"

    @property
    def duration(self) -> float:
        return self.frames / self.sample_rate if self.sample_rate > 0 else 0.0

    @property
    def frame_count(self) -> int:
        """Recorder-style alias for :attr:`frames`."""
        return self.frames


RecordingTake = Take


class TakeRegistry:
    """Persistent, monotonically numbered recording takes for one session.

    Passing an ``.hlproj`` or an existing directory stores ``takes.json`` and
    the recordings inside it. Any other path is treated as a sidecar anchor:
    ``session.wav`` gets ``session.wav.takes.json``. A path already ending in
    ``.takes.json`` is used as-is.
    """

    def __init__(
        self,
        session_path: str | Path,
        *,
        media_directory: str | Path | None = None,
    ) -> None:
        session = Path(session_path).expanduser().resolve()
        self.session_path = session
        self.project_root: Path | None
        if session.suffix.lower() == ".hlproj" or session.is_dir():
            self.project_root = session
            self.metadata_path = session / _TAKES_JSON
            default_media = session / "takes"
        else:
            self.project_root = None
            if session.name.endswith(".takes.json"):
                self.metadata_path = session
                stem = session.name[: -len(".takes.json")]
            else:
                self.metadata_path = Path(f"{session}.takes.json")
                stem = session.name
            default_media = self.metadata_path.parent / f"{stem}.takes"
        self.media_directory = (
            Path(media_directory).expanduser().resolve()
            if media_directory is not None
            else default_media
        )
        self._lock = threading.RLock()
        self._takes: list[Take] = []
        self.reload()

    @property
    def takes(self) -> tuple[Take, ...]:
        with self._lock:
            return tuple(self._takes)

    @property
    def json_path(self) -> Path:
        """Alias naming the metadata file by its representation."""
        return self.metadata_path

    @property
    def next_number(self) -> int:
        with self._lock:
            return max((take.number for take in self._takes), default=0) + 1

    def take(self, number: int) -> Take | None:
        with self._lock:
            return next((take for take in self._takes if take.number == int(number)), None)

    def next_take_path(self, suffix: str = ".wav") -> Path:
        """Return an unused numbered media path without creating the file."""
        suffix = suffix if str(suffix).startswith(".") else f".{suffix}"
        with self._lock:
            number = self.next_number
            registered = {take.path for take in self._takes}
            while True:
                candidate = (self.media_directory / f"take-{number:03d}{suffix}").resolve()
                if candidate not in registered and not candidate.exists():
                    return candidate
                number += 1

    def register(
        self,
        path: str | Path,
        *,
        sample_rate: int,
        channels: int,
        frames: int | None = None,
        frame_count: int | None = None,
        created_at: str | datetime | None = None,
        metadata: Mapping[str, Any] | None = None,
        number: int | None = None,
    ) -> Take:
        """Append and durably persist one completed recording."""
        rate = int(sample_rate)
        channel_count = int(channels)
        if frames is None:
            frames = frame_count
        if frames is None:
            raise ValueError("frames or frame_count is required")
        frame_total = int(frames)
        if rate <= 0 or channel_count <= 0 or frame_total < 0:
            raise ValueError("take format must have positive rate/channels and non-negative frames")

        if isinstance(created_at, datetime):
            timestamp = created_at.astimezone(timezone.utc).isoformat()
        elif created_at is None:
            timestamp = datetime.now(timezone.utc).isoformat()
        else:
            timestamp = str(created_at)
        try:
            datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("created_at must be an ISO-8601 timestamp") from exc

        resolved = Path(path).expanduser().resolve()
        details = dict(metadata or {})
        # Validate extension metadata before touching the registry file.
        try:
            json.dumps(details)
        except (TypeError, ValueError) as exc:
            raise ValueError("take metadata must be JSON serialisable") from exc

        with self._lock:
            if any(take.path == resolved for take in self._takes):
                raise ValueError(f"take is already registered: {resolved}")
            assigned = self.next_number if number is None else int(number)
            if assigned <= 0 or any(take.number == assigned for take in self._takes):
                raise ValueError(f"take number is already registered: {assigned}")
            take = Take(
                number=assigned,
                path=resolved,
                created_at=timestamp,
                sample_rate=rate,
                channels=channel_count,
                frames=frame_total,
                metadata=details,
            )
            updated = sorted([*self._takes, take], key=lambda item: item.number)
            self._write(updated)
            self._takes = updated
            return take

    register_take = register

    def reload(self) -> tuple[Take, ...]:
        """Reload metadata written by this or another registry instance."""
        with self._lock:
            if not self.metadata_path.is_file():
                self._takes = []
                return ()
            try:
                raw = json.loads(self.metadata_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise TakeRegistryError(f"cannot read {self.metadata_path}: {exc}") from exc
            if not isinstance(raw, dict) or raw.get("version") != _TAKE_REGISTRY_VERSION:
                version = raw.get("version") if isinstance(raw, dict) else None
                raise TakeRegistryError(f"unsupported take registry version {version!r}")
            entries = raw.get("takes")
            if not isinstance(entries, list):
                raise TakeRegistryError("take registry has no takes array")

            loaded: list[Take] = []
            numbers: set[int] = set()
            try:
                for item in entries:
                    number = int(item["number"])
                    if number <= 0 or number in numbers:
                        raise ValueError(f"invalid or duplicate take number {number}")
                    numbers.add(number)
                    stored_path = Path(str(item["path"]))
                    path = (
                        stored_path.resolve()
                        if stored_path.is_absolute()
                        else (self.metadata_path.parent / stored_path).resolve()
                    )
                    details = item.get("metadata") or {}
                    if not isinstance(details, dict):
                        raise TypeError("take metadata must be an object")
                    take = Take(
                        number=number,
                        path=path,
                        created_at=str(item["created_at"]),
                        sample_rate=int(item["sample_rate"]),
                        channels=int(item["channels"]),
                        frames=int(item["frames"]),
                        metadata=dict(details),
                    )
                    if take.sample_rate <= 0 or take.channels <= 0 or take.frames < 0:
                        raise ValueError(f"invalid format for take {number}")
                    loaded.append(take)
            except (KeyError, TypeError, ValueError) as exc:
                raise TakeRegistryError(
                    f"invalid take metadata in {self.metadata_path}: {exc}"
                ) from exc
            self._takes = sorted(loaded, key=lambda item: item.number)
            return tuple(self._takes)

    def copy_to(self, session_path: str | Path) -> TakeRegistry:
        """Copy this registry and its existing media into another session."""
        destination = TakeRegistry(session_path)
        if destination.metadata_path == self.metadata_path:
            return self

        for original in self.takes:
            number = original.number
            if destination.take(number) is not None:
                number = destination.next_number
            suffix = original.path.suffix or ".wav"
            target = destination.media_directory / f"take-{number:03d}{suffix}"
            if original.path.is_file():
                target.parent.mkdir(parents=True, exist_ok=True)
                if original.path != target:
                    shutil.copy2(original.path, target)
                registered_path = target
            else:
                registered_path = original.path
            destination.register(
                registered_path,
                sample_rate=original.sample_rate,
                channels=original.channels,
                frames=original.frames,
                created_at=original.created_at,
                metadata=original.metadata,
                number=number,
            )
        return destination

    def _stored_path(self, path: Path) -> str:
        if self.project_root is not None:
            try:
                return path.relative_to(self.project_root).as_posix()
            except ValueError:
                pass
        return str(path)

    def _write(self, takes: Iterable[Take]) -> None:
        payload = {
            "version": _TAKE_REGISTRY_VERSION,
            "takes": [
                {
                    "number": take.number,
                    "name": take.name,
                    "path": self._stored_path(take.path),
                    "created_at": take.created_at,
                    "sample_rate": take.sample_rate,
                    "channels": take.channels,
                    "frames": take.frames,
                    "duration_s": take.duration,
                    "metadata": take.metadata,
                }
                for take in takes
            ],
        }
        self.metadata_path.parent.mkdir(parents=True, exist_ok=True)
        pending = tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            prefix=f".{self.metadata_path.name}.",
            suffix=".tmp",
            dir=self.metadata_path.parent,
            delete=False,
        )
        try:
            with pending:
                json.dump(payload, pending, indent=2, sort_keys=True)
                pending.write("\n")
                pending.flush()
                os.fsync(pending.fileno())
            os.replace(pending.name, self.metadata_path)
            _fsync_directory(self.metadata_path.parent)
        except Exception:
            Path(pending.name).unlink(missing_ok=True)
            raise

    def __len__(self) -> int:
        return len(self.takes)

    def __iter__(self) -> Iterator[Take]:
        return iter(self.takes)


@dataclass(frozen=True, slots=True)
class BWFCue:
    """A named Broadcast Wave cue at a frame offset from recording start."""

    frame: int
    label: str = ""

    def __post_init__(self) -> None:
        if self.frame < 0:
            raise ValueError(f"cue frame must be non-negative, got {self.frame}")
        object.__setattr__(self, "frame", int(self.frame))
        object.__setattr__(self, "label", str(self.label))


def _riff_chunk(chunk_id: bytes, payload: bytes) -> bytes:
    """Return one RIFF chunk including its word-alignment padding."""
    if len(chunk_id) != 4:
        raise ValueError("RIFF chunk ids must contain four bytes")
    padding = b"\0" if len(payload) & 1 else b""
    return chunk_id + struct.pack("<I", len(payload)) + payload + padding


def _bext_payload(description: str, originator: str) -> bytes:
    """Build the fixed BWF version-1 broadcast extension fields."""
    now = datetime.now(timezone.utc)

    def field(text: str, width: int) -> bytes:
        encoded = str(text).encode("ascii", "replace")[:width]
        return encoded.ljust(width, b"\0")

    payload = b"".join(
        (
            field(description, 256),
            field(originator, 32),
            bytes(32),  # OriginatorReference
            field(now.strftime("%Y-%m-%d"), 10),
            field(now.strftime("%H-%M-%S"), 8),
            struct.pack("<QH", 0, 1),  # TimeReference, BWF version
            bytes(64),  # SMPTE UMID
            bytes(190),
        )
    )
    assert len(payload) == _BEXT_FIXED_SIZE
    return payload


def _pcm24_bytes(block: np.ndarray) -> bytes:
    """Encode channel-last float samples as little-endian packed PCM-24."""
    flat = np.asarray(block, dtype=np.float64).reshape(-1)
    if flat.size == 0:
        return b""
    integers = np.clip(
        np.rint(flat * (1 << 23)), _PCM_24_MIN, _PCM_24_MAX
    ).astype(np.int32)
    packed = np.empty((integers.size, 3), dtype=np.uint8)
    packed[:, 0] = integers & 0xFF
    packed[:, 1] = (integers >> 8) & 0xFF
    packed[:, 2] = (integers >> 16) & 0xFF
    return packed.tobytes()


def _cue_chunks(cues: Iterable[BWFCue], frame_count: int) -> bytes:
    """Build standard WAVE ``cue `` and ``LIST/adtl`` marker chunks."""
    accepted = tuple(
        cue
        for cue in cues
        if cue.frame <= frame_count and cue.frame <= 0xFFFFFFFF
    )
    if not accepted:
        return b""

    cue_payload = bytearray(struct.pack("<I", len(accepted)))
    labels = bytearray(b"adtl")
    for cue_id, cue in enumerate(accepted, start=1):
        cue_payload.extend(
            struct.pack(
                "<II4sIII",
                cue_id,
                cue.frame,
                b"data",
                0,
                0,
                cue.frame,
            )
        )
        label = cue.label.encode("utf-8", "replace") + b"\0"
        labels.extend(_riff_chunk(b"labl", struct.pack("<I", cue_id) + label))
    return _riff_chunk(b"cue ", bytes(cue_payload)) + _riff_chunk(b"LIST", bytes(labels))


class _BroadcastWaveWriter:
    """Small append-only PCM-24 BWF writer with durable header checkpoints."""

    def __init__(
        self,
        target: Path,
        sample_rate: int,
        channels: int,
        *,
        description: str,
        originator: str,
        flush_interval: float,
    ) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        pending = tempfile.NamedTemporaryFile(  # noqa: SIM115 - closed by finalize/abandon
            mode="w+b",
            prefix=f".{target.name}.",
            suffix=".tmp",
            dir=target.parent,
            delete=False,
        )
        self.target = target
        self.path = Path(pending.name)
        self._file: BinaryIO = pending
        self._sample_rate = int(sample_rate)
        self._channels = int(channels)
        self._block_align = self._channels * 3
        self._flush_frames = max(1, int(round(sample_rate * flush_interval)))
        self._frames = 0
        self._checkpoint_frame = 0
        self._audio_bytes = 0
        self._closed = False

        try:
            self._write_header(description, originator)
            self.flush()
        except Exception:
            pending.close()
            self.path.unlink(missing_ok=True)
            raise

    @property
    def frames(self) -> int:
        return self._frames

    def _write_header(self, description: str, originator: str) -> None:
        stream = self._file
        stream.write(b"RIFF\0\0\0\0WAVE")
        stream.write(_riff_chunk(b"bext", _bext_payload(description, originator)))
        byte_rate = self._sample_rate * self._block_align
        fmt = struct.pack(
            "<HHIIHH",
            1,
            self._channels,
            self._sample_rate,
            byte_rate,
            self._block_align,
            24,
        )
        stream.write(_riff_chunk(b"fmt ", fmt))
        stream.write(b"data")
        self._data_size_offset = stream.tell()
        stream.write(struct.pack("<I", 0))
        self._data_start = stream.tell()
        self._audio_end = self._data_start

    def write(self, block: np.ndarray) -> None:
        if self._closed:
            raise OSError("cannot write to a closed Broadcast Wave file")
        data = np.asarray(block)
        if data.ndim != 2 or data.shape[1] != self._channels:
            raise ValueError(
                f"BWF block has shape {data.shape}, expected (frames, {self._channels})"
            )
        encoded = _pcm24_bytes(data)
        if self._audio_bytes + len(encoded) > 0xFFFFFFFF:
            raise OSError("recording exceeds the 4 GiB RIFF/WAVE limit")
        self._file.seek(self._audio_end)
        self._file.write(encoded)
        self._audio_bytes += len(encoded)
        self._audio_end += len(encoded)
        self._frames += int(data.shape[0])
        if self._frames - self._checkpoint_frame >= self._flush_frames:
            self.flush()

    def _checkpoint_sizes(self, file_end: int) -> None:
        if file_end - 8 > 0xFFFFFFFF:
            raise OSError("recording exceeds the 4 GiB RIFF/WAVE limit")
        stream = self._file
        stream.seek(4)
        stream.write(struct.pack("<I", file_end - 8))
        stream.seek(self._data_size_offset)
        stream.write(struct.pack("<I", self._audio_bytes))
        stream.seek(file_end)

    def flush(self) -> None:
        """Durably checkpoint all complete frames and current RIFF sizes."""
        if self._closed:
            return
        stream = self._file
        stream.seek(self._audio_end)
        if self._audio_bytes & 1:
            stream.write(b"\0")
        file_end = self._audio_end + (self._audio_bytes & 1)
        stream.truncate(file_end)
        self._checkpoint_sizes(file_end)
        stream.flush()
        os.fsync(stream.fileno())
        self._checkpoint_frame = self._frames
        stream.seek(self._audio_end)

    def finalize(self, cues: Iterable[BWFCue]) -> None:
        """Append cues, make the file durable, and close it."""
        if self._closed:
            return
        stream = self._file
        stream.seek(self._audio_end)
        if self._audio_bytes & 1:
            stream.write(b"\0")
        stream.write(_cue_chunks(cues, self._frames))
        file_end = stream.tell()
        stream.truncate(file_end)
        self._checkpoint_sizes(file_end)
        stream.flush()
        os.fsync(stream.fileno())
        stream.close()
        self._closed = True

    def close_partial(self) -> None:
        """Close a checkpointed temporary file without publishing it."""
        if self._closed:
            return
        self.flush()
        self._file.close()
        self._closed = True


def _fsync_directory(path: Path) -> None:
    """Persist a rename on platforms that allow directory fsync."""
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _publish_bwf(writer: _BroadcastWaveWriter, cues: Iterable[BWFCue]) -> Path:
    writer.finalize(cues)
    os.replace(writer.path, writer.target)
    _fsync_directory(writer.target.parent)
    return writer.target


def recover_bwf_recording(
    partial_path: str | Path,
    target_path: str | Path | None = None,
) -> Path:
    """Recover complete PCM frames from an interrupted streamed BWF file.

    The temporary writer keeps ``bext`` and ``fmt `` complete from the outset.
    Recovery therefore only needs to discard an incomplete final sample frame
    and repair the RIFF/data sizes. When ``target_path`` is supplied the
    partial is copied first, preserving the original crash artifact.
    """
    source = Path(partial_path)
    target = source if target_path is None else Path(target_path)
    if target != source:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)

    with target.open("r+b") as stream:
        header = stream.read(12)
        if len(header) != 12 or header[:4] != b"RIFF" or header[8:] != b"WAVE":
            raise ValueError(f"{source} is not a RIFF/WAVE file")

        block_align: int | None = None
        data_size_offset: int | None = None
        data_start: int | None = None
        while True:
            chunk_header = stream.read(8)
            if len(chunk_header) != 8:
                break
            chunk_id, chunk_size = struct.unpack("<4sI", chunk_header)
            payload_start = stream.tell()
            if chunk_id == b"fmt ":
                fmt = stream.read(min(chunk_size, 16))
                if len(fmt) < 16:
                    break
                block_align = struct.unpack("<HHIIHH", fmt[:16])[4]
            elif chunk_id == b"data":
                data_size_offset = payload_start - 4
                data_start = payload_start
                break
            stream.seek(payload_start + chunk_size + (chunk_size & 1))

        if not block_align or data_size_offset is None or data_start is None:
            raise ValueError(f"{source} has no complete PCM format/data header")

        stream.seek(0, os.SEEK_END)
        available = max(0, stream.tell() - data_start)
        usable = (available // block_align) * block_align
        if usable > 0xFFFFFFFF:
            raise OSError("partial recording exceeds the 4 GiB RIFF/WAVE limit")
        audio_end = data_start + usable
        stream.seek(audio_end)
        if usable & 1:
            stream.write(b"\0")
        file_end = audio_end + (usable & 1)
        stream.truncate(file_end)
        stream.seek(data_size_offset)
        stream.write(struct.pack("<I", usable))
        stream.seek(4)
        stream.write(struct.pack("<I", file_end - 8))
        stream.flush()
        os.fsync(stream.fileno())
    return target


class AudioRecorder(ABC):
    """Common surface of hardware and synthetic recording backends.

    Captured blocks are copied out of the device callback and accumulated in
    memory. WAV targets are also streamed to a crash-recoverable BWF temporary
    file; other containers retain the snapshot-on-stop behaviour.
    """

    name: str = "abstract"

    def __init__(self) -> None:
        self._sample_rate = 0
        self._channels = 0
        self._block_size = DEFAULT_BLOCK_SIZE
        self._target_path: Path | None = None
        self._chunks: list[np.ndarray] = []
        self._frame_count = 0
        self._bwf_writer: _BroadcastWaveWriter | None = None
        self._target_written = False
        self._description = "Audio Studio recording"
        self._originator = "Audio Studio"
        self._marker_source: Iterable[object] | None = None
        self._recording_cues: list[BWFCue] = []
        self._flush_interval = _DEFAULT_FLUSH_INTERVAL
        self._opened = False
        self._running = False
        self._state_lock = threading.RLock()
        self._transition_lock = threading.RLock()

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    @property
    def channels(self) -> int:
        return self._channels

    @property
    def block_size(self) -> int:
        return self._block_size

    @property
    def target_path(self) -> Path | None:
        return self._target_path

    @property
    def temporary_path(self) -> Path | None:
        """Current recoverable BWF temporary path, when recording to WAV."""
        with self._state_lock:
            return self._bwf_writer.path if self._bwf_writer is not None else None

    @property
    def is_open(self) -> bool:
        with self._state_lock:
            return self._opened

    @property
    def is_running(self) -> bool:
        with self._state_lock:
            return self._running

    @property
    def frame_count(self) -> int:
        """Number of frames captured since the stream was opened."""
        with self._state_lock:
            return self._frame_count

    @property
    def frames_recorded(self) -> int:
        """Alias useful next to ``NullOutput.frames_rendered``."""
        return self.frame_count

    @property
    def duration(self) -> float:
        return self.frame_count / self._sample_rate if self._sample_rate else 0.0

    @property
    def buffer(self) -> AudioBuffer:
        """A consistent snapshot of all audio captured so far."""
        with self._state_lock:
            if self._chunks:
                data = np.concatenate(self._chunks, axis=0)
            else:
                data = np.zeros((0, max(self._channels, 1)), dtype=SAMPLE_DTYPE)
            sample_rate = max(self._sample_rate, 1)
        return AudioBuffer(data, sample_rate)

    def open(
        self,
        sample_rate: int,
        channels: int,
        *,
        block_size: int = DEFAULT_BLOCK_SIZE,
        target_path: str | Path | None = None,
        description: str = "Audio Studio recording",
        originator: str = "Audio Studio",
        markers: Iterable[object] | None = None,
        flush_interval: float = _DEFAULT_FLUSH_INTERVAL,
    ) -> None:
        """Configure a fresh recording and open its input stream."""
        if sample_rate <= 0 or channels <= 0 or block_size <= 0 or flush_interval < 0:
            raise RecorderDeviceError(
                f"invalid stream format {sample_rate} Hz / {channels} ch / {block_size} frames"
            )
        with self._transition_lock:
            self.close()
            with self._state_lock:
                self._sample_rate = int(sample_rate)
                self._channels = int(channels)
                self._block_size = int(block_size)
                self._target_path = Path(target_path) if target_path is not None else None
                self._chunks.clear()
                self._frame_count = 0
                self._target_written = False
                self._description = str(description)
                self._originator = str(originator)
                self._marker_source = markers
                self._recording_cues.clear()
                self._flush_interval = float(flush_interval)
            try:
                self._open_stream()
            except Exception:
                self._close_stream()
                raise
            target = self._target_path
            if target is not None and target.suffix.lower() in _WAV_EXTENSIONS:
                try:
                    writer = _BroadcastWaveWriter(
                        target,
                        self._sample_rate,
                        self._channels,
                        description=self._description,
                        originator=self._originator,
                        flush_interval=self._flush_interval,
                    )
                except Exception:
                    self._close_stream()
                    raise
                with self._state_lock:
                    self._bwf_writer = writer
            with self._state_lock:
                self._opened = True

    @abstractmethod
    def _open_stream(self) -> None: ...

    def start(self) -> None:
        """Start capturing; repeated calls while running are harmless."""
        with self._transition_lock:
            with self._state_lock:
                if not self._opened:
                    raise RecorderDeviceError("start() called before open()")
                if self._running:
                    return
                self._running = True
            try:
                self._start_stream()
            except Exception:
                with self._state_lock:
                    self._running = False
                raise

    @abstractmethod
    def _start_stream(self) -> None: ...

    def stop(self) -> AudioBuffer:
        """Stop capturing, atomically publish the target, and return the audio."""
        with self._transition_lock:
            with self._state_lock:
                was_running = self._running
                self._running = False
            if was_running:
                self._stop_stream()
            captured = self.buffer
            target = self._target_path
            writer = self._bwf_writer
            if writer is not None:
                _publish_bwf(writer, self._bwf_cues())
                with self._state_lock:
                    self._bwf_writer = None
                    self._target_written = True
            elif target is not None and not self._target_written:
                save_audio(target, captured)
                with self._state_lock:
                    self._target_written = True
            return captured

    @abstractmethod
    def _stop_stream(self) -> None: ...

    def save(self, path: str | Path | None = None) -> Path:
        """Write the current snapshot without changing capture state."""
        target = Path(path) if path is not None else self._target_path
        if target is None:
            raise ValueError("no recording target path was provided")
        snapshot = self.buffer
        if target.suffix.lower() in _WAV_EXTENSIONS:
            writer = _BroadcastWaveWriter(
                target,
                snapshot.sample_rate,
                snapshot.n_channels,
                description=self._description,
                originator=self._originator,
                flush_interval=self._flush_interval,
            )
            writer.write(snapshot.data)
            written = _publish_bwf(writer, self._bwf_cues())
        else:
            written = save_audio(target, snapshot)
        with self._state_lock:
            self._target_path = written
            self._target_written = True
        return written

    def flush(self) -> None:
        """Durably checkpoint streamed WAV audio captured so far."""
        with self._state_lock:
            writer = self._bwf_writer
            if writer is not None:
                writer.flush()

    def add_cue(self, frame: int | None = None, label: str = "") -> BWFCue:
        """Add a cue to the BWF, defaulting to the current recording frame."""
        with self._state_lock:
            cue = BWFCue(self._frame_count if frame is None else frame, label)
            self._recording_cues.append(cue)
            return cue

    def add_marker(self, frame: int | None = None, name: str = "") -> BWFCue:
        """Alias for :meth:`add_cue` using marker terminology."""
        return self.add_cue(frame, name)

    def abandon(self) -> Path | None:
        """Stop without rename and leave a checkpointed file for recovery."""
        with self._transition_lock:
            with self._state_lock:
                was_running = self._running
                self._running = False
                writer = self._bwf_writer
            if was_running:
                self._stop_stream()
            if writer is not None:
                writer.close_partial()
            self._close_stream()
            with self._state_lock:
                self._bwf_writer = None
                self._opened = False
            return writer.path if writer is not None else None

    def close(self) -> None:
        """Stop and release the stream; safe to call more than once."""
        with self._transition_lock:
            with self._state_lock:
                opened = self._opened
                needs_stop = self._running or (
                    self._target_path is not None and not self._target_written
                )
            if not opened:
                return
            if needs_stop:
                self.stop()
            self._close_stream()
            with self._state_lock:
                self._opened = False

    @abstractmethod
    def _close_stream(self) -> None: ...

    def _capture(self, block: np.ndarray) -> None:
        """Normalise and append one device block without exposing its storage."""
        data = np.asarray(block, dtype=SAMPLE_DTYPE)
        if data.ndim == 1:
            data = data[:, np.newaxis]
        if data.ndim != 2 or data.shape[1] != self._channels:
            raise RecorderDeviceError(
                f"input block has shape {data.shape}, expected (frames, {self._channels})"
            )
        copied = np.ascontiguousarray(data, dtype=SAMPLE_DTYPE).copy()
        with self._state_lock:
            if not self._running or copied.shape[0] == 0:
                return
            self._chunks.append(copied)
            self._frame_count += int(copied.shape[0])
            if self._bwf_writer is not None:
                self._bwf_writer.write(copied)

    def _bwf_cues(self) -> tuple[BWFCue, ...]:
        """Snapshot explicit cues plus point markers supplied to ``open``."""
        with self._state_lock:
            cues = list(self._recording_cues)
            marker_source = self._marker_source
        if marker_source is not None:
            for marker in marker_source:
                frame = getattr(marker, "frame", None)
                if frame is None:
                    continue
                cues.append(BWFCue(int(frame), str(getattr(marker, "name", ""))))
        return tuple(cues)


class NullRecorder(AudioRecorder):
    """Synthetic input used when hardware is absent and by deterministic tests.

    The default source is digital silence. Set ``tone_frequency`` to generate a
    phase-continuous sine tone. ``realtime=False`` leaves capture under explicit
    :meth:`pump` control.
    """

    name = "null"

    def __init__(
        self,
        *,
        realtime: bool = True,
        tone_frequency: float | None = None,
        amplitude: float = 0.1,
    ) -> None:
        super().__init__()
        self._realtime = realtime
        self._tone_frequency = tone_frequency
        self._amplitude = float(amplitude)
        self._phase_frame = 0
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def _open_stream(self) -> None:
        self._phase_frame = 0
        self._stop_event.clear()

    def _start_stream(self) -> None:
        self._stop_event.clear()
        if self._realtime:
            self._thread = threading.Thread(
                target=self._run, name="NullRecorder", daemon=True
            )
            self._thread.start()

    def _stop_stream(self) -> None:
        self._stop_event.set()
        thread, self._thread = self._thread, None
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=2.0)

    def _close_stream(self) -> None:
        self._stop_event.set()

    def pump(self, n_frames: int | None = None) -> np.ndarray:
        """Synthesize one block and offer it to the recorder."""
        count = self._block_size if n_frames is None else int(n_frames)
        if count < 0:
            raise ValueError(f"n_frames must be non-negative, got {count}")
        if self._tone_frequency is None:
            block = np.zeros((count, self._channels), dtype=SAMPLE_DTYPE)
        else:
            frames = self._phase_frame + np.arange(count, dtype=np.float64)
            mono = self._amplitude * np.sin(
                2.0 * np.pi * self._tone_frequency * frames / self._sample_rate
            )
            block = np.repeat(mono[:, np.newaxis], self._channels, axis=1).astype(
                SAMPLE_DTYPE
            )
        self._phase_frame += count
        self._capture(block)
        return block

    def _run(self) -> None:
        period = self._block_size / self._sample_rate
        next_deadline = time.perf_counter()
        while not self._stop_event.is_set():
            self.pump()
            next_deadline += period
            delay = next_deadline - time.perf_counter()
            if delay > 0:
                self._stop_event.wait(delay)
            else:
                next_deadline = time.perf_counter()


class SoundDeviceRecorder(AudioRecorder):
    """PortAudio input backend driven by a ``sounddevice`` callback.

    Callback status and capture failures are retained as monotonic counters so
    long-running recording checks can distinguish an intact stream from one
    that merely produced a decodable partial file.
    """

    name = "sounddevice"

    def __init__(self, device: int | str | None = None) -> None:
        super().__init__()
        self._device = device
        self._stream: Any | None = None
        self._callback_count = 0
        self._input_underflows = 0
        self._input_overflows = 0
        self._callback_errors = 0

    @staticmethod
    def is_available() -> bool:
        """True when ``sounddevice`` and its PortAudio library can be imported."""
        try:
            import sounddevice  # noqa: F401
        except Exception:  # noqa: BLE001 - PortAudio load errors are platform-specific
            return False
        return True

    @property
    def callback_count(self) -> int:
        return self._callback_count

    @property
    def input_underflows(self) -> int:
        return self._input_underflows

    @property
    def input_overflows(self) -> int:
        return self._input_overflows

    @property
    def xruns(self) -> int:
        return self._input_underflows + self._input_overflows

    @property
    def callback_errors(self) -> int:
        return self._callback_errors

    @property
    def stream_active(self) -> bool:
        stream = self._stream
        if stream is None:
            return False
        try:
            return bool(stream.active)
        except Exception:  # noqa: BLE001 - a failed/closed stream is inactive
            return False

    def _open_stream(self) -> None:
        try:
            import sounddevice as sd
        except Exception as exc:  # noqa: BLE001
            raise RecorderDeviceError(f"sounddevice is unavailable: {exc}") from exc

        self._callback_count = 0
        self._input_underflows = 0
        self._input_overflows = 0
        self._callback_errors = 0
        try:
            with _quiet_native_stderr():
                self._stream = sd.InputStream(
                    samplerate=self._sample_rate,
                    channels=self._channels,
                    dtype="float32",
                    blocksize=self._block_size,
                    device=self._device,
                    callback=self._sounddevice_callback,
                )
        except Exception as exc:  # noqa: BLE001
            self._teardown()
            raise RecorderDeviceError(f"Cannot open input stream: {exc}") from exc

    def _sounddevice_callback(
        self, indata: np.ndarray, _frames: int, _time_info: Any, status: Any
    ) -> None:
        """Copy one real device block into the product recorder without raising."""
        self._callback_count += 1
        if status:
            if getattr(status, "input_underflow", False):
                self._input_underflows += 1
            if getattr(status, "input_overflow", False):
                self._input_overflows += 1
        try:
            self._capture(indata)
        except Exception:  # noqa: BLE001 - never cross the PortAudio callback boundary
            self._callback_errors += 1

    def _start_stream(self) -> None:
        if self._stream is None:
            raise RecorderDeviceError("start() called before open()")
        try:
            self._stream.start()
        except Exception as exc:  # noqa: BLE001
            raise RecorderDeviceError(f"Cannot start input stream: {exc}") from exc

    def _stop_stream(self) -> None:
        stream = self._stream
        if stream is not None:
            with suppress(Exception):  # the device may already have disappeared
                stream.stop()

    def _close_stream(self) -> None:
        self._teardown()

    def _teardown(self) -> None:
        stream, self._stream = self._stream, None
        if stream is not None:
            with suppress(Exception):  # shutdown is best-effort
                stream.close()


class PyAudioRecorder(AudioRecorder):
    """PortAudio input backend driven in callback (push) mode."""

    name = "pyaudio"

    def __init__(self, device_index: int | None = None) -> None:
        super().__init__()
        self._device_index = device_index
        self._pyaudio: object | None = None
        self._stream: object | None = None

    @staticmethod
    def is_available() -> bool:
        try:
            import pyaudio  # noqa: F401
        except Exception:  # noqa: BLE001 - missing PortAudio shared library included
            return False
        return True

    def _open_stream(self) -> None:
        try:
            import pyaudio
        except Exception as exc:  # noqa: BLE001
            raise RecorderDeviceError(f"PyAudio is unavailable: {exc}") from exc

        try:
            with _quiet_native_stderr():
                instance = pyaudio.PyAudio()
                self._pyaudio = instance
                self._stream = instance.open(
                    format=pyaudio.paFloat32,
                    channels=self._channels,
                    rate=self._sample_rate,
                    input=True,
                    input_device_index=self._device_index,
                    frames_per_buffer=self._block_size,
                    stream_callback=self._pyaudio_callback,
                    start=False,
                )
        except Exception as exc:  # noqa: BLE001
            self._teardown()
            raise RecorderDeviceError(f"Cannot open input stream: {exc}") from exc

    def _pyaudio_callback(
        self, in_data: bytes | None, frame_count: int, _time_info: dict, _status: int
    ) -> tuple[None, int]:
        import pyaudio

        try:
            raw = np.frombuffer(in_data or b"", dtype="<f4")
            expected = frame_count * self._channels
            if raw.size < expected:
                padded = np.zeros(expected, dtype=SAMPLE_DTYPE)
                padded[: raw.size] = raw
                raw = padded
            self._capture(raw[:expected].reshape(frame_count, self._channels))
        except Exception:  # noqa: BLE001 - never let an exception cross the device boundary
            pass
        return None, pyaudio.paContinue

    def _start_stream(self) -> None:
        if self._stream is None:
            raise RecorderDeviceError("start() called before open()")
        try:
            self._stream.start_stream()  # type: ignore[attr-defined]
        except Exception as exc:  # noqa: BLE001
            raise RecorderDeviceError(f"Cannot start input stream: {exc}") from exc

    def _stop_stream(self) -> None:
        stream = self._stream
        if stream is not None:
            with suppress(Exception):  # the device may already be gone
                stream.stop_stream()  # type: ignore[attr-defined]

    def _close_stream(self) -> None:
        self._teardown()

    def _teardown(self) -> None:
        stream, self._stream = self._stream, None
        instance, self._pyaudio = self._pyaudio, None
        for obj, method in ((stream, "close"), (instance, "terminate")):
            if obj is not None:
                with suppress(Exception):  # shutdown is best-effort
                    getattr(obj, method)()


def create_recorder(*, prefer_null: bool = False) -> AudioRecorder:
    """Return a hardware recorder when possible, otherwise a synthetic one."""
    if not prefer_null and SoundDeviceRecorder.is_available():
        probe = SoundDeviceRecorder()
        try:
            probe.open(48000, 1)
        except RecorderDeviceError:
            probe.close()
        else:
            probe.close()
            return SoundDeviceRecorder()
    if not prefer_null and PyAudioRecorder.is_available():
        probe = PyAudioRecorder()
        try:
            probe.open(48000, 1)
        except RecorderDeviceError:
            probe.close()
        else:
            probe.close()
            return PyAudioRecorder()
    return NullRecorder()
