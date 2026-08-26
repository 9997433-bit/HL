"""Bit-exact WAV import/export null tests."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
AUDIO_STUDIO_ROOT = REPOSITORY_ROOT / "audio-studio"
if str(AUDIO_STUDIO_ROOT) not in sys.path:
    sys.path.insert(0, str(AUDIO_STUDIO_ROOT))

from audio_studio.core.loader import load_audio, save_audio

from tools.golden_audio import assert_bit_exact_wav, fingerprint_wav


@pytest.mark.parametrize("subtype", ("PCM_16", "PCM_24", "FLOAT"))
def test_wav_noop_import_export_is_sample_bit_exact(
    tmp_path: Path,
    subtype: str,
) -> None:
    rng = np.random.default_rng(3341)
    samples = rng.uniform(-0.8, 0.8, size=(48_137, 2)).astype(np.float32)
    source = tmp_path / f"source-{subtype}.wav"
    exported = tmp_path / f"exported-{subtype}.wav"
    sf.write(source, samples, 48_000, subtype=subtype)

    loaded = load_audio(source)
    save_audio(exported, loaded.buffer, subtype=subtype)

    assert_bit_exact_wav(source, exported)


def test_golden_fingerprint_detects_one_changed_sample_byte(tmp_path: Path) -> None:
    source = tmp_path / "source.wav"
    changed = tmp_path / "changed.wav"
    sf.write(source, np.zeros((128, 1), dtype=np.float32), 48_000, subtype="PCM_16")
    payload = bytearray(source.read_bytes())
    payload[-1] ^= 0x01
    changed.write_bytes(payload)

    assert fingerprint_wav(source).data_sha256 != fingerprint_wav(changed).data_sha256
    with pytest.raises(AssertionError, match="data_sha256"):
        assert_bit_exact_wav(source, changed)
