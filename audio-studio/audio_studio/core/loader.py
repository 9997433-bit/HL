"""File decoding and encoding.

libsndfile (via :mod:`soundfile`) covers WAV/FLAC/OGG everywhere and MP3 from
libsndfile 1.1 onwards. When the local libsndfile predates MP3 support we shell
out to ``ffmpeg`` so that the advertised format list stays honest.

The >4 GB containers — RF64 (EBU Tech 3306) and Sony Wave64 — decode through
the same path; their frame counts can exceed 2**31, so everything here reports
counts as plain Python ``int`` (see :func:`probe_frames`) and the policy for
files too large to decode whole lives in :mod:`.large_file`.
"""

from __future__ import annotations

import os
import shutil
import struct
import subprocess
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
import soundfile as sf

from .resample import resample_buffer
from .types import SAMPLE_DTYPE, AudioBuffer, AudioFormat

#: Extensions offered in the file dialog and accepted by :func:`load_audio`.
SUPPORTED_EXTENSIONS: tuple[str, ...] = (
    ".wav",
    ".wave",
    ".flac",
    ".mp3",
    ".ogg",
    ".oga",
    ".opus",
    ".aiff",
    ".aif",
    ".aifc",
    ".w64",
    ".rf64",
    ".caf",
    ".au",
)

#: Extension → libsndfile major-format token, where the two differ or where the
#: mapping deserves to be explicit. RF64 and W64 are listed even though the
#: uppercased extension happens to coincide: they are the >4 GB containers and
#: their presence in :func:`supported_formats` must not hinge on a string
#: accident.
_EXT_TO_FORMAT_TOKEN = {
    ".wave": "WAV",
    ".aif": "AIFF",
    ".aifc": "AIFF",
    ".oga": "OGG",
    ".w64": "W64",
    ".rf64": "RF64",
}

_EXT_TO_SUBTYPE_DEFAULT = {
    ".wav": "PCM_24",
    ".wave": "PCM_24",
    ".flac": "PCM_24",
    ".aiff": "PCM_24",
    ".aif": "PCM_24",
    ".ogg": "VORBIS",
    ".oga": "VORBIS",
}

# Integer export formats whose depth is below the float32 working format's
# precision. Other libsndfile PCM subtypes either expand the working format
# (PCM_32) or are not mastering/export targets (8-bit PCM).
_DITHER_BIT_DEPTHS = {
    "PCM_16": 16,
    "PCM_24": 24,
}


class AudioLoadError(RuntimeError):
    """Raised when a file cannot be decoded by any available backend."""


@dataclass(slots=True)
class LoadedAudio:
    """A decoded file together with the metadata needed by the UI."""

    buffer: AudioBuffer
    audio_format: AudioFormat
    path: Path
    #: Raw BWF broadcast-extension chunk payload, byte-for-byte as it appeared
    #: in the source file, or ``None`` when the source carried none. Pass it
    #: back to :func:`save_audio` to preserve it across an edit round trip.
    bext: bytes | None = None

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def duration(self) -> float:
        return self.buffer.duration


@lru_cache(maxsize=1)
def _libsndfile_formats() -> frozenset[str]:
    try:
        return frozenset(fmt.upper() for fmt in sf.available_formats())
    except Exception:  # pragma: no cover - defensive, libsndfile always answers
        return frozenset()


@lru_cache(maxsize=1)
def _ffmpeg_binary() -> str | None:
    return shutil.which("ffmpeg")


def supported_formats() -> dict[str, bool]:
    """Map each advertised extension to whether a decoder is actually present."""
    native = _libsndfile_formats()
    has_ffmpeg = _ffmpeg_binary() is not None
    result: dict[str, bool] = {}
    for ext in SUPPORTED_EXTENSIONS:
        token = _EXT_TO_FORMAT_TOKEN.get(ext, ext.lstrip(".").upper())
        result[ext] = token in native or has_ffmpeg
    return result


def file_dialog_filter() -> str:
    """Qt file-dialog filter string covering every supported container."""
    patterns = " ".join(f"*{ext}" for ext in SUPPORTED_EXTENSIONS)
    return (
        f"Audio files ({patterns});;"
        "WAV (*.wav *.wave);;RF64/W64 (*.rf64 *.w64);;FLAC (*.flac);;MP3 (*.mp3);;"
        "Ogg (*.ogg *.oga *.opus);;AIFF (*.aiff *.aif);;All files (*)"
    )


def probe(path: str | Path) -> AudioFormat:
    """Read container metadata without decoding the samples."""
    path = Path(path)
    try:
        info = sf.info(str(path))
    except Exception as exc:  # noqa: BLE001 - normalised into AudioLoadError
        raise AudioLoadError(f"Cannot read audio metadata from {path}: {exc}") from exc
    container = str(info.format or path.suffix.lstrip(".").upper())
    # libsndfile builds differ in how they label the 64-bit WAV variants (an
    # RF64 opened by an older build may report plain "WAV"), so the container
    # is pinned from the header magic rather than trusted when they disagree.
    if container not in ("RF64", "BW64", "W64"):
        from .large_file import sniff_container

        sniffed = sniff_container(path)
        if sniffed is not None:
            container = sniffed
    return AudioFormat(
        sample_rate=int(info.samplerate),
        channels=int(info.channels),
        subtype=str(info.subtype or "UNKNOWN"),
        container=container,
    )


def probe_frames(path: str | Path) -> int:
    """Total frames in ``path`` as an arbitrary-precision Python ``int``.

    Kept separate from :func:`probe` because
    :class:`~audio_studio.core.types.AudioFormat` describes *how* the audio is
    encoded, not how much of it there is. RF64/W64 containers may hold more
    than 2**31 frames; ``soundfile`` reports the count as a 64-bit value and
    the conversion to a Python ``int`` here cannot overflow past even that.
    """
    path = Path(path)
    try:
        info = sf.info(str(path))
    except Exception as exc:  # noqa: BLE001 - normalised into AudioLoadError
        raise AudioLoadError(f"Cannot read audio metadata from {path}: {exc}") from exc
    return int(info.frames)


def read_bext(path: str | Path) -> bytes | None:
    """Raw ``bext`` chunk payload of a Broadcast Wave file, or ``None``.

    libsndfile decodes the samples but does not surface the broadcast
    extension, so the chunk is read straight out of the RIFF structure. Only
    chunk headers are touched — a multi-gigabyte data chunk is seeked over,
    not read. An RF64 whose ``data`` precedes ``bext`` with the 0xFFFFFFFF
    placeholder size cannot be skipped without its ``ds64`` table and reports
    ``None``; every writer this application meets (including its own recorder)
    puts ``bext`` first.
    """
    try:
        with Path(path).open("rb") as stream:
            header = stream.read(12)
            if (
                len(header) != 12
                or header[:4] not in (b"RIFF", b"RF64", b"BW64")
                or header[8:12] != b"WAVE"
            ):
                return None
            while True:
                chunk_header = stream.read(8)
                if len(chunk_header) != 8:
                    return None
                chunk_id, chunk_size = struct.unpack("<4sI", chunk_header)
                if chunk_id == b"bext":
                    payload = stream.read(chunk_size)
                    return payload if len(payload) == chunk_size else None
                if chunk_size == 0xFFFFFFFF:
                    return None  # 64-bit chunk: the real size lives in ds64
                stream.seek(chunk_size + (chunk_size & 1), os.SEEK_CUR)
    except OSError:
        return None


def _append_bext(path: Path, payload: bytes) -> None:
    """Attach a ``bext`` chunk to an already-written RIFF/WAVE file.

    The chunk goes after the existing chunks (RIFF mandates ``fmt `` before
    ``data`` but fixes no position for ``bext``) and the RIFF size is
    re-stated to cover it.
    """
    with path.open("r+b") as stream:
        header = stream.read(12)
        if len(header) != 12 or header[:4] != b"RIFF" or header[8:12] != b"WAVE":
            raise AudioLoadError(
                f"Cannot attach bext metadata to {path}: not a RIFF/WAVE file"
            )
        stream.seek(0, os.SEEK_END)
        end = stream.tell()
        start_pad = end & 1
        chunk = b"bext" + struct.pack("<I", len(payload)) + payload
        chunk += b"\0" if len(payload) & 1 else b""
        if end + start_pad + len(chunk) - 8 > 0xFFFFFFFF:
            raise AudioLoadError(
                f"Cannot attach bext metadata to {path}: RIFF size would overflow"
            )
        if start_pad:
            stream.write(b"\0")
        stream.write(chunk)
        total = end + start_pad + len(chunk)
        stream.seek(4)
        stream.write(struct.pack("<I", total - 8))


def load_audio(path: str | Path, *, target_sample_rate: int | None = None) -> LoadedAudio:
    """Decode ``path`` into a float32 :class:`AudioBuffer`.

    ``target_sample_rate`` resamples the result, which the engine uses when a
    file's rate does not match the open output device. Broadcast Wave sources
    additionally have their ``bext`` chunk captured on :attr:`LoadedAudio.bext`
    so an edit round trip can hand it back to :func:`save_audio`.
    """
    path = Path(path)
    if not path.exists():
        raise AudioLoadError(f"File not found: {path}")

    try:
        data, sample_rate = sf.read(str(path), dtype="float32", always_2d=True)
        audio_format = probe(path)
    except Exception as native_exc:  # noqa: BLE001 - fall back before giving up
        data, sample_rate, audio_format = _decode_with_ffmpeg(path, native_exc)

    buffer = AudioBuffer(np.ascontiguousarray(data, dtype=SAMPLE_DTYPE), int(sample_rate))
    if target_sample_rate and target_sample_rate != buffer.sample_rate:
        buffer = resample(buffer, target_sample_rate)
    return LoadedAudio(
        buffer=buffer, audio_format=audio_format, path=path, bext=read_bext(path)
    )


def _decode_with_ffmpeg(
    path: Path, native_exc: Exception
) -> tuple[np.ndarray, int, AudioFormat]:
    """Decode via ffmpeg to raw float32 when libsndfile cannot handle the codec."""
    ffmpeg = _ffmpeg_binary()
    if ffmpeg is None:
        raise AudioLoadError(
            f"Cannot decode {path.name}: libsndfile refused it ({native_exc}) and "
            "ffmpeg is not installed."
        ) from native_exc

    probe_bin = shutil.which("ffprobe")
    sample_rate, channels = 44100, 2
    if probe_bin:
        try:
            out = subprocess.run(
                [
                    probe_bin, "-v", "error", "-select_streams", "a:0",
                    "-show_entries", "stream=sample_rate,channels",
                    "-of", "csv=p=0", str(path),
                ],
                capture_output=True, text=True, check=True, timeout=30,
            ).stdout.strip()
            first = out.splitlines()[0]
            fields = [f for f in first.split(",") if f]
            sample_rate, channels = int(fields[0]), int(fields[1])
        except Exception:  # noqa: BLE001 - keep the defaults and let ffmpeg decide
            pass

    try:
        raw = subprocess.run(
            [
                ffmpeg, "-v", "error", "-i", str(path),
                "-f", "f32le", "-acodec", "pcm_f32le",
                "-ar", str(sample_rate), "-ac", str(channels), "-",
            ],
            capture_output=True, check=True, timeout=600,
        ).stdout
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.decode("utf-8", "replace").strip() if exc.stderr else ""
        raise AudioLoadError(f"ffmpeg failed to decode {path.name}: {detail}") from exc
    except subprocess.TimeoutExpired as exc:
        raise AudioLoadError(f"ffmpeg timed out decoding {path.name}") from exc

    data = np.frombuffer(raw, dtype="<f4")
    usable = (data.size // channels) * channels
    data = data[:usable].reshape(-1, channels)
    audio_format = AudioFormat(
        sample_rate=sample_rate,
        channels=channels,
        subtype="FLOAT",
        container=path.suffix.lstrip(".").upper() or "UNKNOWN",
    )
    return data, sample_rate, audio_format


def resample(
    buffer: AudioBuffer,
    target_sample_rate: int,
    *,
    quality: str = "vhq",
) -> AudioBuffer:
    """Convert ``buffer`` with the selected offline SRC backend."""
    if target_sample_rate <= 0:
        raise ValueError(f"target_sample_rate must be positive, got {target_sample_rate}")
    if buffer.sample_rate == target_sample_rate or buffer.n_frames == 0:
        return AudioBuffer(buffer.data, target_sample_rate)

    converted = resample_buffer(
        buffer.data,
        buffer.sample_rate,
        target_sample_rate,
        quality=quality,
    )
    return AudioBuffer(converted, target_sample_rate)


def quantize_with_tpdf(
    samples: np.ndarray,
    bit_depth: int,
    *,
    rng: np.random.Generator | None = None,
) -> np.ndarray:
    """Quantize floating-point samples with triangular-PDF dither.

    The difference of two independent uniform variates produces TPDF noise with
    a peak amplitude of one target-format LSB. Values are clipped to the
    asymmetric range representable by signed PCM before being returned as
    float32 values on the target quantization grid.
    """
    if not 2 <= bit_depth <= 32:
        raise ValueError(f"bit_depth must be between 2 and 32, got {bit_depth}")

    array = np.asarray(samples)
    generator = rng if rng is not None else np.random.default_rng()
    scale = float(1 << (bit_depth - 1))
    noise_lsb = generator.random(array.shape)
    noise_lsb -= generator.random(array.shape)

    quantized = np.rint(array.astype(np.float64, copy=False) * scale + noise_lsb)
    np.clip(quantized, -scale, scale - 1.0, out=quantized)
    quantized /= scale
    return np.ascontiguousarray(quantized, dtype=SAMPLE_DTYPE)


def save_audio(
    path: str | Path,
    buffer: AudioBuffer,
    *,
    subtype: str | None = None,
    dither: bool = True,
    bext: bytes | None = None,
) -> Path:
    """Encode ``buffer`` to ``path``; the container follows the extension.

    PCM-16 and PCM-24 exports receive TPDF dither by default before their
    float32 samples are reduced to the integer target depth. Set
    ``dither=False`` for a deliberate bit-exact/no-op integer round trip.
    Dither is ignored for floating-point and compressed subtypes.

    ``bext`` attaches a Broadcast Wave extension chunk, byte-for-byte —
    normally the payload :func:`load_audio` captured from the source, so that
    editing a BWF does not silently strip its provenance. Only WAV targets can
    hold the chunk; asking for it on any other container raises ``ValueError``
    rather than dropping metadata the caller said to keep.
    """
    path = Path(path)
    if bext is not None and path.suffix.lower() not in (".wav", ".wave"):
        raise ValueError(f"bext metadata requires a WAV target, not {path.suffix!r}")
    path.parent.mkdir(parents=True, exist_ok=True)
    chosen = subtype or _EXT_TO_SUBTYPE_DEFAULT.get(path.suffix.lower(), "PCM_24")
    output = buffer.data
    bit_depth = _DITHER_BIT_DEPTHS.get(chosen.upper())
    if dither and bit_depth is not None:
        output = quantize_with_tpdf(output, bit_depth)
    try:
        sf.write(str(path), output, buffer.sample_rate, subtype=chosen)
    except Exception as exc:  # noqa: BLE001 - normalised into AudioLoadError
        raise AudioLoadError(f"Cannot write {path}: {exc}") from exc
    if bext is not None:
        _append_bext(path, bext)
    return path


def describe_backends() -> str:
    """One-line summary of the decoding capabilities, shown in the About box."""
    native = ", ".join(sorted(_libsndfile_formats())) or "none"
    ffmpeg = _ffmpeg_binary() or "not installed"
    return (
        f"libsndfile {sf.__libsndfile_version__} [{native}]\n"
        f"ffmpeg fallback: {ffmpeg}\n"
        f"python {sys.version.split()[0]}"
    )
