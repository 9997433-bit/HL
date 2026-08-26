"""Live effect preview: the rack inserted between the engine and the device.

The point of the insert is that auditioning is free — nothing is written back
to the clip, bypassing is instant, and a broken effect costs one dry block
rather than the stream. Every test here is about one of those three.
"""

from __future__ import annotations

import numpy as np
import pytest

from audio_studio.core.engine import AudioEngine
from audio_studio.core.loader import LoadedAudio
from audio_studio.core.output import NullOutput
from audio_studio.dsp.effects import Effect, EffectChain, GainEffect, NormalizeEffect
from audio_studio.dsp.preview import EffectPreview

BLOCK = 256


class Boom(Effect):
    """An effect with a bug in it."""

    name = "Boom"

    def _process_planar(self, audio: np.ndarray, sample_rate: float) -> np.ndarray:
        raise ValueError("bad parameter")


def half_chain() -> EffectChain:
    return EffectChain([GainEffect(gain_db=-6.0206, ramp_ms=0.0)])


@pytest.fixture()
def preview_engine(loaded_clip: LoadedAudio):
    """An engine whose device is wrapped in a preview, pumped by hand."""
    device = NullOutput(realtime=False)
    preview = EffectPreview(device, half_chain())
    engine = AudioEngine(preview, block_size=BLOCK, ring_blocks=8)
    engine.set_clip(loaded_clip)
    yield engine, preview, device
    engine.shutdown()


def pump(engine: AudioEngine, device: NullOutput, blocks: int = 6) -> np.ndarray:
    """Play and collect ``blocks`` of what the device would have heard."""
    engine.play()
    out = [device.pump(BLOCK) for _ in range(blocks)]
    engine.stop()
    return np.concatenate(out)


class TestInsert:
    def test_the_chain_processes_what_the_device_pulls(self, preview_engine) -> None:
        engine, preview, device = preview_engine
        wet = pump(engine, device)

        source = engine.clip.buffer.data[: wet.shape[0]]
        assert np.abs(wet).max() > 0.0
        assert preview.processed_blocks > 0
        assert np.allclose(wet, source * 0.5, atol=2e-3)

    def test_bypassing_returns_the_untouched_signal(self, preview_engine) -> None:
        engine, preview, device = preview_engine
        preview.chain.bypass = True

        dry = pump(engine, device)

        assert not preview.is_active
        assert preview.processed_blocks == 0
        assert np.allclose(dry, engine.clip.buffer.data[: dry.shape[0]], atol=2e-3)

    def test_a_mix_of_half_lands_halfway(self, preview_engine) -> None:
        engine, preview, device = preview_engine
        preview.chain.mix = 0.5

        out = pump(engine, device)

        source = engine.clip.buffer.data[: out.shape[0]]
        assert np.allclose(out, source * 0.75, atol=2e-3)

    def test_the_clip_in_memory_is_never_touched(self, preview_engine) -> None:
        engine, _preview, device = preview_engine
        before = engine.clip.buffer.data.copy()

        pump(engine, device)

        assert np.array_equal(engine.clip.buffer.data, before)

    def test_a_raising_effect_costs_one_dry_block_not_the_stream(
        self, preview_engine
    ) -> None:
        engine, preview, device = preview_engine
        preview.chain.add(Boom())

        out = pump(engine, device)

        assert preview.failed_blocks > 0
        assert isinstance(preview.last_error, ValueError)
        assert np.allclose(out, engine.clip.buffer.data[: out.shape[0]], atol=2e-3)

    def test_an_offline_only_member_is_skipped_rather_than_fatal(
        self, preview_engine
    ) -> None:
        """A normaliser in the rack must not stop the EQ being auditioned."""
        engine, preview, device = preview_engine
        preview.chain.add(NormalizeEffect())

        out = pump(engine, device)

        assert preview.failed_blocks == 0
        assert np.allclose(out, engine.clip.buffer.data[: out.shape[0]] * 0.5, atol=2e-3)

    def test_the_chain_is_prepared_for_the_stream_format(self, preview_engine) -> None:
        engine, preview, _device = preview_engine
        engine.play()
        engine.stop()

        chain = preview.chain
        assert chain._prepared_sample_rate == float(engine.sample_rate)  # noqa: SLF001
        assert chain._prepared_channels == engine.n_channels  # noqa: SLF001


class TestWrapping:
    def test_the_backend_api_stays_reachable_through_the_wrapper(self) -> None:
        device = NullOutput(realtime=False)
        preview = EffectPreview(device)

        preview.open(48_000, 2, lambda n: np.zeros((n, 2), dtype=np.float32))
        preview.start()

        assert preview.name == "null+fx"
        assert preview.output is device
        assert preview.sample_rate == 48_000
        assert preview.is_open
        assert preview.pump(64).shape == (64, 2)
        assert device.frames_rendered == 64
        preview.close()
        assert not device.is_open

    def test_an_empty_rack_is_a_pass_through(self) -> None:
        preview = EffectPreview(NullOutput(realtime=False))
        assert not preview.is_active

        preview.chain.add(GainEffect(gain_db=-20.0))
        assert preview.is_active

        preview.chain.mix = 0.0
        assert not preview.is_active

    def test_rendering_before_open_returns_silence(self) -> None:
        preview = EffectPreview(NullOutput(realtime=False))
        block = preview.render(32)
        assert block.shape[0] == 32
        assert not block.any()

    def test_unknown_attributes_still_raise(self) -> None:
        preview = EffectPreview(NullOutput(realtime=False))
        with pytest.raises(AttributeError):
            _ = preview.no_such_control

    def test_repr_says_how_big_the_rack_is(self) -> None:
        assert "2 effects" in repr(EffectPreview(NullOutput(), half_chain().add(GainEffect())))


class TestAttachPreview:
    def test_attaching_replaces_the_engines_backend(self, loaded_clip) -> None:
        from audio_studio.ui.main_window import attach_preview

        engine = AudioEngine(NullOutput(realtime=False), block_size=BLOCK)
        try:
            device = engine.output
            preview = attach_preview(engine, half_chain())

            assert engine.output is preview
            assert preview.output is device
        finally:
            engine.shutdown()

    def test_attaching_twice_reuses_the_wrapper(self, loaded_clip) -> None:
        from audio_studio.ui.main_window import attach_preview

        engine = AudioEngine(NullOutput(realtime=False), block_size=BLOCK)
        try:
            first = attach_preview(engine, half_chain())
            second_chain = EffectChain([GainEffect(gain_db=-3.0)])
            second = attach_preview(engine, second_chain)

            assert second is first
            assert second.chain is second_chain
            assert not isinstance(second.output, EffectPreview)
        finally:
            engine.shutdown()
