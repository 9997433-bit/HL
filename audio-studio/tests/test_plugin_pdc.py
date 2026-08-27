"""Plugin delay compensation: reported latency, the padded preview path, the toggle.

A plugin that reports latency hands audio back late. The preview pads the rest
of the path so that the total delay is a constant — bypassing the plugin swaps
its delay for an equal compensation delay, and an A/B against the dry signal
still nulls. These tests drive that promise end to end with a mock host that
has *real* latency (a delay line it is honest about), so alignment is measured
in samples rather than asserted from bookkeeping.

pedalboard is not needed anywhere here: hosts are fakes, and the
``VST3PluginWrapper`` probes are exercised against plain namespace objects.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest

from audio_studio.core.engine import AudioEngine
from audio_studio.core.loader import LoadedAudio
from audio_studio.core.output import NullOutput
from audio_studio.dsp.effects import (
    Effect,
    EffectChain,
    GainEffect,
    LimiterEffect,
)
from audio_studio.dsp.preview import EffectPreview, LatencyCompensator
from audio_studio.plugins import PluginEffectAdapter, PluginHost, VST3PluginWrapper
from audio_studio.ui.plugin_panel import PluginPanel

BLOCK = 256

LATENCY = 37  # deliberately not a divisor of the block size


# -- hosts that need no plugin ------------------------------------------------


class LatentHost(PluginHost):
    """A transparent plugin that is honest about its delay.

    Output is the input, ``latency`` samples late — the shape of every
    lookahead limiter and linear-phase EQ. What it reports and what it does
    agree by construction, so a null test against the compensated bypass path
    measures the compensation and nothing else.
    """

    def __init__(self, latency: int = LATENCY, path: str | Path = "/plugins/Latent.vst3") -> None:
        self._latency = int(latency)
        self._path = Path(path)
        self._tail: np.ndarray | None = None

    @property
    def name(self) -> str:
        return self._path.stem

    @property
    def plugin_path(self) -> Path:
        return self._path

    def prepare(self, sample_rate: float, n_channels: int) -> None:
        self._tail = None

    def reset(self) -> None:
        self._tail = None

    def process_block(self, block: np.ndarray, sample_rate: float) -> np.ndarray:
        audio = np.asarray(block, dtype=np.float32)
        if self._latency <= 0 or audio.shape[-1] == 0:
            return audio
        tail_shape = (*audio.shape[:-1], self._latency)
        if self._tail is None or self._tail.shape != tail_shape:
            self._tail = np.zeros(tail_shape, dtype=np.float32)
        joined = np.concatenate([self._tail, audio], axis=-1)
        self._tail = joined[..., audio.shape[-1] :]
        return joined[..., : audio.shape[-1]]

    def latency_samples(self) -> int:
        return self._latency

    def parameters(self) -> dict[str, Any]:
        return {"mix": 1.0}


class ParamHost(PluginHost):
    """Pass-through host with writable parameters, for the state-blob contract."""

    def __init__(
        self,
        path: str | Path = "/plugins/Param.vst3",
        *,
        parameters: dict[str, Any] | None = None,
        writable: bool = True,
    ) -> None:
        self._path = Path(path)
        self._parameters = dict(
            parameters if parameters is not None else {"drive": 0.25, "tone": 0.5}
        )
        self._writable = writable

    @property
    def name(self) -> str:
        return self._path.stem

    @property
    def plugin_path(self) -> Path:
        return self._path

    def prepare(self, sample_rate: float, n_channels: int) -> None: ...

    def process_block(self, block: np.ndarray, sample_rate: float) -> np.ndarray:
        return block

    def latency_samples(self) -> int:
        return 0

    def parameters(self) -> dict[str, Any]:
        return dict(self._parameters)

    def set_parameter(self, name: str, value: Any) -> None:
        if not self._writable:
            raise NotImplementedError("ParamHost is read-only")
        if name not in self._parameters:
            raise KeyError(name)
        self._parameters[name] = value


class Boom(Effect):
    """An effect with a bug in it."""

    name = "Boom"

    def _process_planar(self, audio: np.ndarray, sample_rate: float) -> np.ndarray:
        raise ValueError("bad parameter")


def ramp(n: int, channels: int = 1) -> np.ndarray:
    """A frames-first ramp signal, unambiguous under any shift."""
    data = np.arange(1, n + 1, dtype=np.float32)[:, np.newaxis]
    return np.repeat(data, channels, axis=1)


def stream(preview: EffectPreview, signal: np.ndarray, block: int = 64) -> np.ndarray:
    """Feed ``signal`` through the preview block by block, as the feeder would."""
    out = [
        preview.process_block(signal[start : start + block], 48_000)
        for start in range(0, signal.shape[0], block)
    ]
    return np.concatenate(out)


def delayed(signal: np.ndarray, samples: int) -> np.ndarray:
    """``signal`` late by ``samples``, zero-primed — the compensated expectation."""
    if samples <= 0:
        return signal
    pad = np.zeros((samples, *signal.shape[1:]), dtype=signal.dtype)
    return np.concatenate([pad, signal])[: signal.shape[0]]


# -- the delay line itself -----------------------------------------------------


class TestLatencyCompensator:
    def test_zero_delay_is_a_pass_through(self) -> None:
        pdc = LatencyCompensator()
        block = ramp(16)
        assert pdc.delay_samples == 0
        assert pdc.process(block) is block

    def test_it_delays_by_exactly_the_requested_samples(self) -> None:
        pdc = LatencyCompensator()
        pdc.set_delay(5)
        signal = ramp(64)

        out = np.concatenate([pdc.process(signal[:20]), pdc.process(signal[20:])])

        np.testing.assert_allclose(out, delayed(signal, 5))

    def test_uneven_blocks_and_blocks_shorter_than_the_delay(self) -> None:
        pdc = LatencyCompensator()
        pdc.set_delay(7)
        signal = ramp(30)
        cuts = [3, 8, 12, 25, 30]

        out = np.concatenate(
            [pdc.process(signal[a:b]) for a, b in zip([0, *cuts[:-1]], cuts, strict=True)]
        )

        np.testing.assert_allclose(out, delayed(signal, 7))

    def test_stereo_blocks_are_delayed_along_the_time_axis(self) -> None:
        pdc = LatencyCompensator()
        pdc.set_delay(4)
        signal = ramp(32, channels=2)
        signal[:, 1] *= -1.0

        out = pdc.process(signal)

        np.testing.assert_allclose(out, delayed(signal, 4))

    def test_resizing_reprimes_with_silence(self) -> None:
        pdc = LatencyCompensator(3)
        pdc.process(ramp(8))

        pdc.set_delay(5)
        out = pdc.process(ramp(8))

        assert pdc.delay_samples == 5
        np.testing.assert_allclose(out[:5], np.zeros((5, 1), dtype=np.float32))

    def test_reset_forgets_the_buffered_tail(self) -> None:
        pdc = LatencyCompensator(2)
        pdc.process(ramp(8))

        pdc.reset()
        out = pdc.process(ramp(4))

        np.testing.assert_allclose(out[:2], np.zeros((2, 1), dtype=np.float32))


# -- reported latency, summed up the chain --------------------------------------


class TestChainLatency:
    def test_native_effects_report_zero(self) -> None:
        chain = EffectChain([GainEffect(), LimiterEffect()])
        assert GainEffect().latency_samples() == 0
        assert chain.latency_samples() == 0
        assert chain.latency_samples(include_bypassed=True) == 0

    def test_the_adapter_exposes_the_host_figure(self) -> None:
        adapter = PluginEffectAdapter(LatentHost(latency=128))
        assert adapter.latency_samples() == 128

    def test_the_chain_sums_its_members(self) -> None:
        chain = EffectChain(
            [
                GainEffect(),
                PluginEffectAdapter(LatentHost(64)),
                PluginEffectAdapter(LatentHost(32)),
            ]
        )
        assert chain.latency_samples() == 96

    def test_a_bypassed_member_delays_nothing_but_still_counts_as_reference(self) -> None:
        latent = PluginEffectAdapter(LatentHost(64))
        chain = EffectChain([latent, PluginEffectAdapter(LatentHost(32))])

        latent.bypass = True

        assert chain.latency_samples() == 32
        assert chain.latency_samples(include_bypassed=True) == 96

    def test_nested_chains_recurse(self) -> None:
        inner = EffectChain([PluginEffectAdapter(LatentHost(16))])
        outer = EffectChain([inner, PluginEffectAdapter(LatentHost(8))])

        assert outer.latency_samples() == 24

        inner[0].bypass = True
        assert outer.latency_samples() == 8
        assert outer.latency_samples(include_bypassed=True) == 24

    def test_an_unusable_report_counts_as_zero(self) -> None:
        broken = PluginEffectAdapter(LatentHost(64))
        broken.host.latency_samples = lambda: None  # type: ignore[method-assign]
        chain = EffectChain([broken, PluginEffectAdapter(LatentHost(32))])

        assert chain.latency_samples() == 32


class TestWrapperLatencyProbe:
    """`VST3PluginWrapper.latency_samples` against whatever pedalboard exposes."""

    @staticmethod
    def wrapper(plugin: object) -> VST3PluginWrapper:
        instance = VST3PluginWrapper.__new__(VST3PluginWrapper)
        instance._plugin_path = Path("/plugins/Probe.vst3")  # noqa: SLF001
        instance._plugin = plugin  # noqa: SLF001
        instance._sample_rate = None  # noqa: SLF001
        instance._n_channels = None  # noqa: SLF001
        return instance

    def test_nothing_reported_means_zero(self) -> None:
        assert self.wrapper(SimpleNamespace()).latency_samples() == 0

    def test_a_plain_attribute_is_read(self) -> None:
        assert self.wrapper(SimpleNamespace(latency_samples=384)).latency_samples() == 384

    def test_a_callable_is_called(self) -> None:
        assert (
            self.wrapper(SimpleNamespace(latency_samples=lambda: 512)).latency_samples()
            == 512
        )

    def test_the_second_spelling_is_probed_too(self) -> None:
        assert self.wrapper(SimpleNamespace(latency=100)).latency_samples() == 100

    def test_garbage_reports_degrade_to_zero(self) -> None:
        assert self.wrapper(SimpleNamespace(latency_samples="many")).latency_samples() == 0
        assert self.wrapper(SimpleNamespace(latency_samples=-64)).latency_samples() == 0

    def test_a_raising_probe_degrades_to_zero(self) -> None:
        def explode() -> int:
            raise RuntimeError("plugin crashed")

        assert self.wrapper(SimpleNamespace(latency_samples=explode)).latency_samples() == 0


# -- the compensated preview path ------------------------------------------------


class TestPreviewCompensation:
    def make_preview(
        self, latency: int = LATENCY, *, pdc: bool = True
    ) -> tuple[EffectPreview, PluginEffectAdapter]:
        adapter = PluginEffectAdapter(LatentHost(latency))
        chain = EffectChain([GainEffect(gain_db=0.0, ramp_ms=0.0), adapter])
        preview = EffectPreview(NullOutput(realtime=False), chain, pdc_enabled=pdc)
        return preview, adapter

    def test_an_active_plugin_needs_no_padding(self) -> None:
        preview, _adapter = self.make_preview()
        signal = ramp(512, channels=2)

        out = stream(preview, signal)

        assert preview.pdc_padding_samples() == 0
        assert preview.latency_samples() == LATENCY
        np.testing.assert_allclose(out, delayed(signal, LATENCY))

    def test_a_bypassed_plugin_is_padded_to_the_same_delay(self) -> None:
        """The null test: bypassing must not move the stream in time."""
        wet_preview, _ = self.make_preview()
        dry_preview, dry_adapter = self.make_preview()
        dry_adapter.bypass = True
        signal = ramp(512, channels=2)

        wet = stream(wet_preview, signal)
        dry = stream(dry_preview, signal)

        assert dry_preview.pdc_padding_samples() == LATENCY
        assert dry_preview.latency_samples() == wet_preview.latency_samples() == LATENCY
        # The plugin is transparent apart from its delay, so wet minus dry
        # nulls sample for sample — the definition of aligned.
        np.testing.assert_allclose(wet, dry)
        np.testing.assert_allclose(dry, delayed(signal, LATENCY))

    def test_a_fully_bypassed_chain_is_still_aligned(self) -> None:
        preview, _adapter = self.make_preview()
        preview.chain.bypass = True
        signal = ramp(256)

        out = stream(preview, signal)

        assert not preview.is_active
        assert preview.pdc_padding_samples() == LATENCY
        np.testing.assert_allclose(out, delayed(signal, LATENCY))

    def test_the_error_fallback_does_not_flap_the_compensator(self) -> None:
        """A raising chain costs dry blocks, exactly as before PDC existed.

        The compensator keys off *reported* latency, not off whether a given
        block succeeded: a failure substitutes dry content into the block's
        own slot in the timeline rather than resizing the delay line around
        it, which would turn one bad parameter into a click on every block.
        """
        preview, _adapter = self.make_preview()
        preview.chain.add(Boom())
        signal = ramp(256)

        out = stream(preview, signal)

        assert preview.failed_blocks > 0
        assert preview.pdc_padding_samples() == 0
        np.testing.assert_allclose(out, signal)

    def test_turning_pdc_off_restores_the_uncompensated_path(self) -> None:
        preview, adapter = self.make_preview(pdc=False)
        adapter.bypass = True
        signal = ramp(256)

        out = stream(preview, signal)

        assert not preview.pdc_enabled
        assert preview.pdc_padding_samples() == 0
        assert preview.latency_samples() == 0
        np.testing.assert_allclose(out, signal)

    def test_the_toggle_is_live(self) -> None:
        preview, adapter = self.make_preview()
        adapter.bypass = True
        signal = ramp(128)

        padded = stream(preview, signal)
        preview.pdc_enabled = False
        flat = stream(preview, signal)

        np.testing.assert_allclose(padded, delayed(signal, LATENCY))
        np.testing.assert_allclose(flat, signal)

    def test_zero_latency_plugins_cost_nothing(self) -> None:
        preview, _adapter = self.make_preview(latency=0)
        signal = ramp(128)

        out = stream(preview, signal)

        assert preview.pdc_padding_samples() == 0
        assert preview.latency_samples() == 0
        np.testing.assert_allclose(out, signal)


class TestFeederIntegration:
    """The same null test through the engine's feeder thread and ring buffer."""

    @staticmethod
    def run_engine(
        clip: LoadedAudio, *, bypass: bool, pdc: bool = True, blocks: int = 6
    ) -> np.ndarray:
        adapter = PluginEffectAdapter(LatentHost(LATENCY))
        adapter.bypass = bypass
        device = NullOutput(realtime=False)
        preview = EffectPreview(device, EffectChain([adapter]), pdc_enabled=pdc)
        engine = AudioEngine(preview, block_size=BLOCK, ring_blocks=8)
        try:
            engine.set_clip(clip)
            engine.play()
            out = np.concatenate([device.pump(BLOCK) for _ in range(blocks)])
            engine.stop()
        finally:
            engine.shutdown()
        return out

    def test_bypass_nulls_against_the_active_plugin(self, loaded_clip: LoadedAudio) -> None:
        wet = self.run_engine(loaded_clip, bypass=False)
        dry = self.run_engine(loaded_clip, bypass=True)

        source = loaded_clip.buffer.data[: wet.shape[0]]
        np.testing.assert_allclose(wet, dry, atol=1e-6)
        np.testing.assert_allclose(wet, delayed(source, LATENCY), atol=2e-3)

    def test_without_pdc_the_bypass_moves_the_stream(
        self, loaded_clip: LoadedAudio
    ) -> None:
        dry = self.run_engine(loaded_clip, bypass=True, pdc=False)

        source = loaded_clip.buffer.data[: dry.shape[0]]
        np.testing.assert_allclose(dry, source, atol=2e-3)
        assert not np.allclose(dry, delayed(source, LATENCY), atol=2e-3)


# -- the state-blob contract ------------------------------------------------------


class TestHostStateBlob:
    def test_the_default_blob_is_the_parameter_dict_as_json(self) -> None:
        host = ParamHost(parameters={"drive": 0.25, "tone": 0.5})
        blob = host.state_blob()
        assert blob is not None
        assert json.loads(blob.decode("utf-8")) == {"drive": 0.25, "tone": 0.5}

    def test_restore_writes_the_parameters_back(self) -> None:
        saved = ParamHost(parameters={"drive": 0.9, "tone": 0.1})
        fresh = ParamHost()

        assert fresh.restore_state(saved.state_blob() or b"") is True
        assert fresh.parameters() == {"drive": 0.9, "tone": 0.1}

    def test_unknown_parameters_are_skipped_not_fatal(self) -> None:
        fresh = ParamHost(parameters={"drive": 0.25})
        blob = json.dumps({"drive": 0.7, "vanished": 1.0}).encode("utf-8")

        assert fresh.restore_state(blob) is True
        assert fresh.parameters() == {"drive": 0.7}

    def test_garbage_blobs_are_refused_quietly(self) -> None:
        host = ParamHost()
        assert host.restore_state(b"\x00\x01\x02") is False
        assert host.restore_state(b"[1, 2, 3]") is False
        assert host.parameters() == {"drive": 0.25, "tone": 0.5}

    def test_a_read_only_host_restores_nothing(self) -> None:
        host = ParamHost(writable=False)
        blob = json.dumps({"drive": 0.9}).encode("utf-8")
        assert host.restore_state(blob) is False

    def test_the_adapter_forwards_both_directions(self) -> None:
        saved = PluginEffectAdapter(ParamHost(parameters={"drive": 0.8, "tone": 0.2}))
        fresh = PluginEffectAdapter(ParamHost())

        blob = saved.state_blob()
        assert blob is not None
        assert fresh.restore_state(blob) is True
        assert fresh.plugin_parameters() == {"drive": 0.8, "tone": 0.2}


class FakeParameter:
    def __init__(self, raw_value: float) -> None:
        self.raw_value = raw_value


class TestWrapperStateBlob:
    """`VST3PluginWrapper` prefers the native chunk and falls back to JSON."""

    wrapper = staticmethod(TestWrapperLatencyProbe.wrapper)

    def test_a_native_chunk_is_preferred(self) -> None:
        plugin = SimpleNamespace(
            raw_state=b"\x00\x01native", parameters={"drive": FakeParameter(0.25)}
        )
        assert self.wrapper(plugin).state_blob() == b"\x00\x01native"

    def test_without_a_chunk_the_parameters_are_serialised(self) -> None:
        plugin = SimpleNamespace(parameters={"drive": FakeParameter(0.25)})
        blob = self.wrapper(plugin).state_blob()
        assert blob is not None
        assert json.loads(blob.decode("utf-8")) == {"drive": 0.25}

    def test_a_native_chunk_restores_to_the_attribute_it_came_from(self) -> None:
        plugin = SimpleNamespace(raw_state=b"old", parameters={})
        assert self.wrapper(plugin).restore_state(b"\x00\x01new") is True
        assert plugin.raw_state == b"\x00\x01new"

    def test_parameter_json_goes_to_the_parameters_even_with_a_chunk_attribute(
        self,
    ) -> None:
        drive = FakeParameter(0.25)
        plugin = SimpleNamespace(raw_state=b"old", parameters={"drive": drive})

        blob = json.dumps({"drive": 0.9}).encode("utf-8")
        assert self.wrapper(plugin).restore_state(blob) is True

        assert drive.raw_value == pytest.approx(0.9)
        assert plugin.raw_state == b"old"

    def test_nowhere_to_restore_to_reports_false(self) -> None:
        plugin = SimpleNamespace(parameters={})
        assert self.wrapper(plugin).restore_state(b"\x00\x01chunk") is False


# -- the panel ---------------------------------------------------------------


@pytest.mark.usefixtures("qapp")
class TestPanelPDC:
    @staticmethod
    def loader(path: str | Path) -> PluginEffectAdapter:
        return PluginEffectAdapter(LatentHost(64, path))

    @pytest.fixture()
    def panel(self) -> PluginPanel:
        chain = EffectChain([GainEffect(gain_db=0.0), LimiterEffect(enabled=False)])
        return PluginPanel(chain, loader=self.loader)

    def test_pdc_is_on_by_default(self, panel: PluginPanel) -> None:
        assert panel.pdc_enabled
        assert panel.pdc_button.isChecked()
        assert panel.latency_label.text() == "Plugin latency: 0 samples"

    def test_the_readout_shows_the_compensated_constant(self, panel: PluginPanel) -> None:
        panel.load_plugin("/plugins/First.vst3")
        panel.load_plugin("/plugins/Second.vst3")

        assert panel.compensated_latency_samples() == 128
        assert panel.latency_label.text() == "Plugin latency: 128 samples (compensated)"

    def test_a_bypassed_slot_stays_in_the_compensated_figure(
        self, panel: PluginPanel
    ) -> None:
        """PDC's whole point: the path is padded to the same constant either way."""
        panel.load_plugin("/plugins/First.vst3")
        panel.load_plugin("/plugins/Second.vst3")

        panel.slots[0].bypass_button.setChecked(True)

        assert panel.total_latency_samples() == 64
        assert panel.compensated_latency_samples() == 128
        assert panel.latency_label.text() == "Plugin latency: 128 samples (compensated)"

    def test_toggling_off_reports_the_uncompensated_delay(
        self, panel: PluginPanel
    ) -> None:
        panel.load_plugin("/plugins/First.vst3")
        panel.load_plugin("/plugins/Second.vst3")
        panel.slots[0].bypass_button.setChecked(True)
        states: list[bool] = []
        panel.pdcToggled.connect(states.append)

        panel.pdc_button.setChecked(False)

        assert states == [False]
        assert not panel.pdc_enabled
        assert panel.latency_label.text() == "Plugin latency: 64 samples (not compensated)"

    def test_set_pdc_enabled_drives_the_button_and_the_signal(
        self, panel: PluginPanel
    ) -> None:
        states: list[bool] = []
        panel.pdcToggled.connect(states.append)

        panel.set_pdc_enabled(False)
        panel.set_pdc_enabled(False)  # no change, no signal
        panel.set_pdc_enabled(True)

        assert states == [False, True]


@pytest.mark.usefixtures("qapp")
class TestMainWindowPDC:
    @pytest.fixture()
    def window(self):
        from audio_studio.ui.main_window import MainWindow

        main = MainWindow(AudioEngine(NullOutput(realtime=False), block_size=BLOCK))
        yield main
        main._mark_project_saved()  # noqa: SLF001 - avoid blocking close prompts in tests
        main.close()

    def test_the_panel_toggle_reaches_the_preview_insert(self, window) -> None:
        assert window.preview.pdc_enabled

        window.plugin_panel.pdc_button.setChecked(False)
        assert not window.preview.pdc_enabled

        window.plugin_panel.pdc_button.setChecked(True)
        assert window.preview.pdc_enabled
