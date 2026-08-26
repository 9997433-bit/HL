"""Golden-file helpers for bit-exact WAV null tests."""

from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WavFingerprint:
    """Stable identity of the WAV format and sample payload."""

    format_tag: int
    channels: int
    sample_rate: int
    block_align: int
    bits_per_sample: int
    data_size: int
    data_sha256: str


def fingerprint_wav(path: str | Path) -> WavFingerprint:
    """Hash the ``data`` chunk and parse the fields relevant to sample identity."""
    source_path = Path(path)
    fmt: tuple[int, int, int, int, int] | None = None
    data_size: int | None = None
    data_sha256: str | None = None

    with source_path.open("rb") as source:
        header = source.read(12)
        if len(header) != 12 or header[:4] != b"RIFF" or header[8:] != b"WAVE":
            raise ValueError(f"{source_path}: expected a little-endian RIFF/WAVE file")

        while True:
            chunk_header = source.read(8)
            if not chunk_header:
                break
            if len(chunk_header) != 8:
                raise ValueError(f"{source_path}: truncated chunk header")
            chunk_id, chunk_size = struct.unpack("<4sI", chunk_header)
            if chunk_id == b"fmt ":
                payload = source.read(chunk_size)
                if len(payload) != chunk_size or chunk_size < 16:
                    raise ValueError(f"{source_path}: invalid fmt chunk")
                format_tag, channels, sample_rate, _, block_align, bits = struct.unpack(
                    "<HHIIHH",
                    payload[:16],
                )
                fmt = (format_tag, channels, sample_rate, block_align, bits)
            elif chunk_id == b"data":
                digest = hashlib.sha256()
                remaining = chunk_size
                while remaining:
                    block = source.read(min(remaining, 1024 * 1024))
                    if not block:
                        raise ValueError(f"{source_path}: truncated data chunk")
                    digest.update(block)
                    remaining -= len(block)
                data_size = chunk_size
                data_sha256 = digest.hexdigest()
            else:
                source.seek(chunk_size, 1)
            if chunk_size % 2:
                source.seek(1, 1)

    if fmt is None or data_size is None or data_sha256 is None:
        raise ValueError(f"{source_path}: missing fmt or data chunk")
    return WavFingerprint(*fmt, data_size, data_sha256)


def assert_bit_exact_wav(expected: str | Path, actual: str | Path) -> None:
    """Assert that WAV format metadata and every encoded sample bit agree."""
    expected_fingerprint = fingerprint_wav(expected)
    actual_fingerprint = fingerprint_wav(actual)
    if actual_fingerprint != expected_fingerprint:
        differing = [
            field
            for field in WavFingerprint.__dataclass_fields__
            if getattr(actual_fingerprint, field) != getattr(expected_fingerprint, field)
        ]
        raise AssertionError(
            "WAV null test failed; differing fields: " + ", ".join(differing)
        )
