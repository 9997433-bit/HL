"""Loudness Match: the LUFS-normalising effect, its rack slot and the CLI preset.

The effect is the editor-side twin of the batch pipeline's ``NormalizeLoudness``
operation, so the important assertions are against delivered numbers: the
rendered clip *measures* the preset's LUFS, the true-peak ceiling wins when the
two disagree, and both code paths produce the same samples.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest
from conftest import make_tone

from audio_studio.batch import cli
from audio_studio.batch.pipeline import NormalizeLoudness
from audio_studio.core.loader import load_audio, save_audio
from audio_studio.dsp.effects import (
    LOUDNESS_PRESETS,
    EffectChain,
    LoudnessNormalizeEffect,
    LoudnessPreset,
    loudness_preset,
)
from audio_studio.dsp.loudness import LoudnessMeter, integrated_loudness

SR = 48_000

#: Long enough for BS.1770 gating (>= 400 ms) while keeping the suite fast.
TONE_SECONDS = 2.0


def stereo_tone(amplitude: float, duration_s: float = TONE_SECONDS) -> np.ndarray:
    """1 kHz in both channels — the EBU Tech 3341 measurement signal."""
    t = np.arange(int(duration_s * SR)) / SR
    mono = amplitude * np.sin(2.0 * np.pi * 1000.0 * t)
    return np.stack([mono, mono])


# ---------------------------------------------------------------------------
# presets
# ---------------------------------------------------------------------------


class TestPresets:
    def test_broadcast_is_ebu_r128(self) -> None:
        preset = LOUDNESS_PRESETS["broadcast"]
        assert preset.target_lufs == -23.0
        assert preset.max_true_peak_dbtp == -1.0

    def test_streaming_is_minus_16(self) -> None:
        preset = LOUDNESS_PRESETS["streaming"]
        assert preset.target_lufs == -16.0
        assert preset.max_true_peak_dbtp == -1.0

    def test_lookup_is_case_insensitive_and_passes_objects_through(self) -> None:
        assert loudness_preset("Broadcast").target_lufs == -23.0
        preset = LoudnessPreset("custom", -20.0)
        assert loudness_preset(preset) is preset

    def test_unknown_preset_raises(self) -> None:
        with pytest.raises(KeyError, match="unknown loudness preset"):
            loudness_preset("mastering")

    def test_from_preset_configures_the_effect(self) -> None:
        effect = LoudnessNormalizeEffect.from_preset("streaming")
        assert effect.target_lufs == -16.0
        assert effect.max_true_peak_dbtp == -1.0

    def test_apply_preset_retargets_an_existing_effect(self) -> None:
        effect = LoudnessNormalizeEffect.from_preset("broadcast")
        effect.apply_preset("streaming")
        assert effect.target_lufs == -16.0


# ---------------------------------------------------------------------------
# the effect
# ---------------------------------------------------------------------------


class TestLoudnessNormalizeEffect:
    @pytest.mark.parametrize("preset, target", [("broadcast", -23.0), ("streaming", -16.0)])
    def test_the_render_measures_the_preset_target(self, preset: str, target: float) -> None:
        out = LoudnessNormalizeEffect.from_preset(preset).process(stereo_tone(0.5), SR)
        assert LoudnessMeter(SR).integrated(out) == pytest.approx(target, abs=0.1)

    def test_quiet_material_is_gained_up_to_the_target(self) -> None:
        effect = LoudnessNormalizeEffect.from_preset("streaming")
        out = effect.process(stereo_tone(0.01), SR)
        assert LoudnessMeter(SR).integrated(out) == pytest.approx(-16.0, abs=0.1)
        assert effect.applied_gain_db > 0.0

    def test_a_custom_numeric_target_works_without_a_preset(self) -> None:
        effect = LoudnessNormalizeEffect(target_lufs=-20.0, max_true_peak_dbtp=None)
        out = effect.process(stereo_tone(0.5), SR)
        assert LoudnessMeter(SR).integrated(out) == pytest.approx(-20.0, abs=0.1)

    def test_the_true_peak_ceiling_caps_the_gain(self) -> None:
        # A -20 dBFS tone asked for -3 LUFS wants ~17 dB; a -10 dBTP ceiling
        # only allows ~10 dB, so the clip comes out quiet rather than clipped.
        effect = LoudnessNormalizeEffect(target_lufs=-3.0, max_true_peak_dbtp=-10.0)
        out = effect.process(stereo_tone(0.1), SR)
        meter = LoudnessMeter(SR)
        assert meter.true_peak(out) <= -10.0 + 0.1
        assert meter.integrated(out) == pytest.approx(-10.0, abs=0.3)
        assert effect.applied_gain_db == pytest.approx(10.0, abs=0.3)

    def test_max_gain_db_clamps_the_boost(self) -> None:
        effect = LoudnessNormalizeEffect(
            target_lufs=-3.0, max_true_peak_dbtp=None, max_gain_db=5.0
        )
        effect.process(stereo_tone(0.01), SR)
        assert effect.applied_gain_db == 5.0

    def test_silence_passes_through_untouched(self) -> None:
        effect = LoudnessNormalizeEffect.from_preset("broadcast")
        silence = np.zeros((2, SR), dtype=np.float32)
        out = effect.process(silence, SR)
        assert np.array_equal(out, silence)
        assert effect.applied_gain_db == 0.0
        assert effect.measured_lufs == -math.inf

    def test_a_clip_shorter_than_one_gating_block_passes_through(self) -> None:
        fragment = stereo_tone(0.5, duration_s=0.1)
        out = LoudnessNormalizeEffect.from_preset("broadcast").process(fragment, SR)
        assert np.allclose(out, fragment)

    def test_it_is_offline_only(self) -> None:
        effect = LoudnessNormalizeEffect.from_preset("broadcast")
        assert effect.is_offline_only
        with pytest.raises(NotImplementedError, match="whole signal"):
            effect.process_block(stereo_tone(0.5), SR)

    def test_a_preview_chain_skips_it_instead_of_raising(self) -> None:
        chain = EffectChain([LoudnessNormalizeEffect.from_preset("broadcast")])
        block = stereo_tone(0.5, duration_s=0.01)
        assert np.allclose(chain.process_block(block, SR), block)

    def test_disabled_effect_is_identity(self) -> None:
        tone = stereo_tone(0.5)
        out = LoudnessNormalizeEffect(enabled=False).process(tone, SR)
        assert np.array_equal(out, tone)

    def test_parameters_snapshot(self) -> None:
        effect = LoudnessNormalizeEffect.from_preset("streaming")
        params = effect.parameters()
        assert params["target_lufs"] == -16.0
        assert params["max_true_peak_dbtp"] == -1.0
        assert params["enabled"] is True

    def test_it_matches_the_batch_pipeline_sample_for_sample(self) -> None:
        buffer = make_tone(duration=TONE_SECONDS)
        from_pipeline = NormalizeLoudness(-16.0, max_true_peak_dbtp=-1.0).apply(buffer)
        from_effect = LoudnessNormalizeEffect(-16.0, max_true_peak_dbtp=-1.0).process(
            buffer.data, buffer.sample_rate, channels_last=True
        )
        assert np.allclose(from_pipeline.data, from_effect, atol=1e-7)


# ---------------------------------------------------------------------------
# effect rack
# ---------------------------------------------------------------------------


class TestLoudnessRackControls:
    @pytest.fixture()
    def rack(self, qapp):
        from audio_studio.ui.effect_rack import EffectRackPanel, default_preview_chain

        return EffectRackPanel(default_preview_chain())

    def test_the_default_rack_ends_with_loudness_match_switched_off(self, rack) -> None:
        assert isinstance(rack.chain[-1], LoudnessNormalizeEffect)
        assert rack.loudness is not None
        assert not rack.loudness.enabled
        assert rack.loudness.target_lufs == -23.0

    def test_the_enable_checkbox_reaches_the_effect(self, rack) -> None:
        rack.loudness_enabled.setChecked(True)
        assert rack.loudness.enabled
        assert "Loudness Match" in rack.summary()

    def test_the_preset_combo_retargets_the_effect(self, rack) -> None:
        rack.loudness_preset.setCurrentIndex(1)
        assert rack.loudness.target_lufs == -16.0
        assert rack.loudness.max_true_peak_dbtp == -1.0
        rack.loudness_preset.setCurrentIndex(0)
        assert rack.loudness.target_lufs == -23.0

    def test_the_panel_reads_loudness_state_back_from_a_chain(self, rack) -> None:
        from audio_studio.ui.effect_rack import default_preview_chain

        other = default_preview_chain()
        effect = next(e for e in other if isinstance(e, LoudnessNormalizeEffect))
        effect.enabled = True
        effect.apply_preset("streaming")

        rack.set_chain(other)
        assert rack.loudness_enabled.isChecked()
        assert rack.loudness_preset.currentIndex() == 1

    def test_reset_switches_it_off_and_back_to_broadcast(self, rack) -> None:
        rack.loudness_enabled.setChecked(True)
        rack.loudness_preset.setCurrentIndex(1)
        rack.reset()
        assert not rack.loudness.enabled
        assert rack.loudness.target_lufs == -23.0
        assert rack.loudness_preset.currentIndex() == 0


# ---------------------------------------------------------------------------
# batch CLI --preset
# ---------------------------------------------------------------------------


@pytest.fixture()
def quiet_wav(tmp_path: Path) -> Path:
    """One quiet stereo tone, far below every delivery target."""
    source = tmp_path / "in"
    source.mkdir()
    tone = make_tone(440.0, duration=TONE_SECONDS, amplitude=0.05)
    save_audio(source / "quiet.wav", tone, subtype="FLOAT")
    return source


def _measure(path: Path) -> float:
    rendered = load_audio(path).buffer
    return integrated_loudness(rendered.data, rendered.sample_rate, channels_last=True)


class TestBatchCliPreset:
    @pytest.mark.parametrize("preset, target", [("broadcast", -23.0), ("streaming", -16.0)])
    def test_preset_normalizes_to_its_target(
        self, quiet_wav: Path, tmp_path: Path, preset: str, target: float
    ) -> None:
        out = tmp_path / "out"
        code = cli.main(
            [
                "--input", str(quiet_wav / "*.wav"),
                "--output", str(out),
                "--preset", preset,
                "--subtype", "FLOAT",
            ]
        )
        assert code == 0
        assert _measure(out / "quiet.wav") == pytest.approx(target, abs=0.1)

    def test_explicit_lufs_overrides_the_preset_target(
        self, quiet_wav: Path, tmp_path: Path
    ) -> None:
        out = tmp_path / "out"
        code = cli.main(
            [
                "--input", str(quiet_wav / "*.wav"),
                "--output", str(out),
                "--preset", "broadcast",
                "--lufs", "-20",
                "--subtype", "FLOAT",
            ]
        )
        assert code == 0
        assert _measure(out / "quiet.wav") == pytest.approx(-20.0, abs=0.1)

    def test_explicit_true_peak_overrides_the_preset_ceiling(
        self, quiet_wav: Path, tmp_path: Path
    ) -> None:
        # The -26 dBFS tone would need ~10 dB to reach -16 LUFS, but a -30 dBTP
        # ceiling forces the gain down instead: the ceiling must win.
        out = tmp_path / "out"
        code = cli.main(
            [
                "--input", str(quiet_wav / "*.wav"),
                "--output", str(out),
                "--preset", "streaming",
                "--true-peak", "-30",
                "--subtype", "FLOAT",
            ]
        )
        assert code == 0
        rendered = load_audio(out / "quiet.wav").buffer
        peak_db = 20.0 * np.log10(float(np.max(np.abs(rendered.data))))
        assert peak_db <= -30.0 + 0.1
        assert _measure(out / "quiet.wav") < -25.0

    def test_the_preset_describes_itself_in_the_progress_log(
        self, quiet_wav: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = cli.main(
            [
                "--input", str(quiet_wav / "*.wav"),
                "--output", str(tmp_path / "out"),
                "--preset", "broadcast",
                "--subtype", "FLOAT",
            ]
        )
        assert code == 0
        captured = capsys.readouterr().out
        assert "normalize integrated loudness to -23 LUFS" in captured
        assert "true peak <= -1 dBTP" in captured

    def test_an_unknown_preset_is_rejected_by_the_parser(self, tmp_path: Path) -> None:
        with pytest.raises(SystemExit):
            cli.main(
                [
                    "--input", "*.wav",
                    "--output", str(tmp_path),
                    "--preset", "mastering",
                ]
            )
