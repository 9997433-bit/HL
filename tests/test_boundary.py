"""Boundary and malformed-input probes for the WAV benchmark loader."""

from __future__ import annotations

import struct
from pathlib import Path

import pytest

from tools.benchmark_audio import AudioProbeError, load_wav


def _pcm_wav(
    *,
    sample_rate: int = 48_000,
    declared_frames: int = 0,
    payload: bytes = b"",
) -> bytes:
    channels = 1
    sample_width = 2
    block_align = channels * sample_width
    byte_rate = sample_rate * block_align
    declared_data_size = declared_frames * block_align
    riff_size = 36 + declared_data_size
    return b"".join(
        (
            b"RIFF",
            struct.pack("<I", riff_size),
            b"WAVE",
            b"fmt ",
            struct.pack(
                "<IHHIIHH",
                16,
                1,
                channels,
                sample_rate,
                byte_rate,
                block_align,
                sample_width * 8,
            ),
            b"data",
            struct.pack("<I", declared_data_size),
            payload,
        )
    )


def test_empty_file_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "empty.wav"
    path.write_bytes(b"")

    with pytest.raises(AudioProbeError, match="invalid WAV"):
        load_wav(path)


def test_simulated_huge_file_is_rejected_before_payload_read(
    tmp_path: Path,
) -> None:
    path = tmp_path / "declared-huge.wav"
    path.write_bytes(_pcm_wav(declared_frames=2_000_000))

    with pytest.raises(AudioProbeError, match="safety limit"):
        load_wav(path, max_frames=1_000_000)


def test_corrupt_header_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "corrupt.wav"
    path.write_bytes(b"RIFF\x08\x00\x00\x00WAVEjunk")

    with pytest.raises(AudioProbeError, match="invalid WAV"):
        load_wav(path)


@pytest.mark.parametrize("sample_rate", [1, 1_000_000])
def test_extreme_sample_rate_metadata_is_rejected(
    tmp_path: Path, sample_rate: int
) -> None:
    path = tmp_path / f"rate-{sample_rate}.wav"
    path.write_bytes(_pcm_wav(sample_rate=sample_rate))

    with pytest.raises(AudioProbeError, match="sample rate"):
        load_wav(path)


def test_truncated_pcm_payload_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "truncated.wav"
    path.write_bytes(_pcm_wav(declared_frames=4, payload=b"\x00\x00"))

    with pytest.raises(AudioProbeError, match="truncated PCM payload"):
        load_wav(path)
