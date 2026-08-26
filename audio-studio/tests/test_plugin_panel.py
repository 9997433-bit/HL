"""The VST3 plugin slot: adapter behaviour, the dock, and the missing-extra path.

pedalboard (GPL-3.0) is not a test dependency. Every test here runs without it:
the panel is driven through an injected loader that returns a fake host, and the
error paths block ``import pedalboard`` outright. The two tests that need the
real package are skipped unless the ``plugins`` extra is installed.
"""

from __future__ import annotations

import importlib
import importlib.util
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from audio_studio.core.engine import AudioEngine
from audio_studio.core.output import NullOutput
from audio_studio.dsp.effects import EffectChain, GainEffect, LimiterEffect
from audio_studio.plugins import PluginEffectAdapter, PluginHost, PluginLoadError
from audio_studio.plugins.adapter import create_plugin_effect
from audio_studio.ui.main_window import MainWindow
from audio_studio.ui.plugin_panel import (
    MAX_PARAMETER_ROWS,
    PluginPanel,
    _ParameterReadout,
    _ParameterSlider,
    plugins_extra_installed,
)

pytestmark = pytest.mark.usefixtures("qapp")

PEDALBOARD_INSTALLED = importlib.util.find_spec("pedalboard") is not None

requires_pedalboard = pytest.mark.skipif(
    not PEDALBOARD_INSTALLED,
    reason="pedalboard is not installed (needs the 'plugins' extra)",
)


# -- a plugin host that needs no plugin --------------------------------------


class FakeHost(PluginHost):
    """Halves the signal, records its life cycle, and writes parameters back."""

    def __init__(
        self,
        path: str | Path = "/plugins/FakeVerb.vst3",
        *,
        parameters: dict[str, Any] | None = None,
        writable: bool = True,
    ) -> None:
        self._path = Path(path)
        self._parameters = dict(
            parameters if parameters is not None else {"drive": 0.25, "mix": 1.0}
        )
        self._writable = writable
        self.prepare_calls: list[tuple[float, int]] = []
        self.reset_calls = 0
        self.process_calls: list[tuple[tuple[int, ...], float]] = []

    @property
    def name(self) -> str:
        return self._path.stem

    @property
    def plugin_path(self) -> Path:
        return self._path

    def prepare(self, sample_rate: float, n_channels: int) -> None:
        self.prepare_calls.append((float(sample_rate), int(n_channels)))

    def reset(self) -> None:
        self.reset_calls += 1

    def process_block(self, block: np.ndarray, sample_rate: float) -> np.ndarray:
        self.process_calls.append((block.shape, float(sample_rate)))
        return np.asarray(block, dtype=np.float32) * 0.5

    def latency_samples(self) -> int:
        return 128

    def parameters(self) -> dict[str, Any]:
        return dict(self._parameters)

    def set_parameter(self, name: str, value: Any) -> None:
        if not self._writable:
            raise NotImplementedError("FakeHost is read-only")
        if name not in self._parameters:
            raise KeyError(name)
        self._parameters[name] = value


@pytest.fixture()
def host() -> FakeHost:
    return FakeHost()


@pytest.fixture()
def chain() -> EffectChain:
    """A rack shaped like the real one: something to insert before, and after."""
    return EffectChain([GainEffect(gain_db=0.0), LimiterEffect(enabled=False)])


@pytest.fixture()
def panel(chain: EffectChain, host: FakeHost) -> PluginPanel:
    return PluginPanel(chain, loader=lambda _path: PluginEffectAdapter(host))


# -- the adapter -------------------------------------------------------------


class TestPluginEffectAdapter:
    def test_it_presents_the_host_as_an_effect(self, host: FakeHost) -> None:
        adapter = PluginEffectAdapter(host)
        assert adapter.name == "VST3: FakeVerb"
        assert adapter.plugin_name == "FakeVerb"
        assert adapter.plugin_path == Path("/plugins/FakeVerb.vst3")
        assert adapter.latency_samples() == 128
        assert adapter.plugin_parameters() == {"drive": 0.25, "mix": 1.0}

    def test_blocks_stream_through_the_host(self, host: FakeHost) -> None:
        adapter = PluginEffectAdapter(host)
        block = np.full((2, 64), 0.5, dtype=np.float32)

        out_a = adapter.process_block(block, 48_000)
        out_b = adapter.process_block(block, 48_000)

        np.testing.assert_allclose(out_a, block * 0.5)
        np.testing.assert_allclose(out_b, block * 0.5)
        # prepare() is forwarded once, on the first block; the host keeps its
        # state across calls exactly as it would outside a rack.
        assert host.prepare_calls == [(48_000.0, 2)]
        assert [shape for shape, _rate in host.process_calls] == [(2, 64), (2, 64)]

    def test_bypass_and_mix_are_the_adapter_s_own(self, host: FakeHost) -> None:
        adapter = PluginEffectAdapter(host)
        block = np.ones((1, 8), dtype=np.float32)

        adapter.mix = 0.5
        np.testing.assert_allclose(adapter.process_block(block, 48_000), block * 0.75)

        adapter.bypass = True
        np.testing.assert_allclose(adapter.process_block(block, 48_000), block)

    def test_a_plugin_that_changes_block_length_is_refused(self, host: FakeHost) -> None:
        host.process_block = lambda block, sample_rate: np.zeros(  # type: ignore[method-assign]
            (block.shape[0], block.shape[1] + 1), dtype=np.float32
        )
        adapter = PluginEffectAdapter(host)
        with pytest.raises(ValueError, match="block geometry"):
            adapter.process_block(np.ones((1, 8), dtype=np.float32), 48_000)

    def test_it_runs_as_a_chain_member(self, chain: EffectChain, host: FakeHost) -> None:
        chain.add(PluginEffectAdapter(host))
        out = chain.process_block(np.ones((2, 32), dtype=np.float32), 48_000)
        np.testing.assert_allclose(out, np.full((2, 32), 0.5, dtype=np.float32))

    def test_parameters_include_the_plugin_snapshot(self, host: FakeHost) -> None:
        parameters = PluginEffectAdapter(host).parameters()
        assert parameters["plugin"] == "FakeVerb"
        assert parameters["plugin_path"] == "/plugins/FakeVerb.vst3"
        assert parameters["plugin_parameters"] == {"drive": 0.25, "mix": 1.0}

    def test_a_read_only_host_says_so(self) -> None:
        adapter = PluginEffectAdapter(FakeHost(writable=False))
        with pytest.raises(NotImplementedError):
            adapter.set_parameter("drive", 0.5)

    def test_a_host_without_write_support_falls_back_to_the_base_contract(self) -> None:
        """The default :meth:`PluginHost.set_parameter` refuses rather than drops."""

        class MinimalHost(PluginHost):
            name = "Minimal"
            plugin_path = Path("/plugins/Minimal.vst3")

            def prepare(self, sample_rate: float, n_channels: int) -> None: ...

            def process_block(self, block: np.ndarray, sample_rate: float) -> np.ndarray:
                return block

            def latency_samples(self) -> int:
                return 0

            def parameters(self) -> dict[str, Any]:
                return {"drive": 0.5}

        with pytest.raises(NotImplementedError, match="cannot write plugin parameters"):
            PluginEffectAdapter(MinimalHost()).set_parameter("drive", 0.5)


# -- the panel ---------------------------------------------------------------


class TestPluginPanel:
    def test_it_starts_empty(self, panel: PluginPanel) -> None:
        assert not panel.has_plugin
        assert panel.plugin_name is None
        assert not panel.bypass_button.isEnabled()
        assert not panel.remove_button.isEnabled()
        assert panel.load_button.isEnabled()
        assert panel.summary() == "Plugin: none"

    def test_loading_inserts_the_plugin_ahead_of_the_limiter(
        self, panel: PluginPanel, chain: EffectChain
    ) -> None:
        assert panel.load_plugin("/plugins/FakeVerb.vst3")

        assert panel.has_plugin
        assert panel.plugin_name == "FakeVerb"
        assert [type(effect).__name__ for effect in chain] == [
            "GainEffect",
            "PluginEffectAdapter",
            "LimiterEffect",
        ]
        assert "FakeVerb" in panel.name_label.text()
        assert panel.bypass_button.isEnabled()
        assert panel.remove_button.isEnabled()
        assert panel.summary() == "Plugin: FakeVerb (active)"

    def test_it_appends_when_the_rack_has_no_limiter(self, host: FakeHost) -> None:
        chain = EffectChain([GainEffect()])
        panel = PluginPanel(chain, loader=lambda _path: PluginEffectAdapter(host))

        panel.load_plugin("/plugins/FakeVerb.vst3")

        assert isinstance(chain[-1], PluginEffectAdapter)

    def test_sliders_are_generated_from_the_parameter_snapshot(
        self, panel: PluginPanel
    ) -> None:
        panel.load_plugin("/plugins/FakeVerb.vst3")

        assert set(panel.parameter_rows) == {"drive", "mix"}
        drive = panel.parameter_rows["drive"]
        assert isinstance(drive, _ParameterSlider)
        assert drive.value == pytest.approx(0.25)
        assert panel.parameter_rows["mix"].value == pytest.approx(1.0)

    def test_moving_a_slider_writes_through_to_the_plugin(
        self, panel: PluginPanel, host: FakeHost
    ) -> None:
        panel.load_plugin("/plugins/FakeVerb.vst3")
        changes = []
        panel.pluginChanged.connect(lambda: changes.append(True))

        panel.parameter_rows["drive"].slider.setValue(750)

        assert host.parameters()["drive"] == pytest.approx(0.75)
        assert panel.parameter_rows["drive"].readout.text() == "0.750"
        assert changes

    def test_a_read_only_parameter_write_is_reported_not_raised(
        self, chain: EffectChain
    ) -> None:
        host = FakeHost(writable=False)
        panel = PluginPanel(chain, loader=lambda _path: PluginEffectAdapter(host))
        panel.load_plugin("/plugins/FakeVerb.vst3")

        panel.parameter_rows["drive"].slider.setValue(500)

        assert "Could not set drive" in panel.message.text()

    def test_values_off_the_normalised_scale_stay_read_only(
        self, chain: EffectChain
    ) -> None:
        """A host may report display values; the panel must not guess a scale."""
        host = FakeHost(parameters={"cutoff_hz": 4800.0, "shape": "bell", "mix": 0.5})
        panel = PluginPanel(chain, loader=lambda _path: PluginEffectAdapter(host))

        panel.load_plugin("/plugins/FakeVerb.vst3")

        assert isinstance(panel.parameter_rows["cutoff_hz"], _ParameterReadout)
        assert isinstance(panel.parameter_rows["shape"], _ParameterReadout)
        assert isinstance(panel.parameter_rows["mix"], _ParameterSlider)
        assert panel.parameter_rows["cutoff_hz"].readout.text() == "4800.0"

    def test_a_huge_parameter_list_is_capped(self, chain: EffectChain) -> None:
        host = FakeHost(parameters={f"p{i}": 0.5 for i in range(MAX_PARAMETER_ROWS + 7)})
        panel = PluginPanel(chain, loader=lambda _path: PluginEffectAdapter(host))

        panel.load_plugin("/plugins/FakeVerb.vst3")

        assert len(panel.parameter_rows) == MAX_PARAMETER_ROWS

    def test_bypass_takes_the_plugin_out_of_the_chain_path(
        self, panel: PluginPanel, chain: EffectChain
    ) -> None:
        panel.load_plugin("/plugins/FakeVerb.vst3")

        panel.bypass_button.setChecked(True)

        assert panel.adapter is not None and panel.adapter.bypass
        assert panel.adapter not in chain.active
        assert panel.summary() == "Plugin: FakeVerb (bypassed)"
        np.testing.assert_allclose(
            chain.process_block(np.ones((2, 16), dtype=np.float32), 48_000),
            np.ones((2, 16), dtype=np.float32),
        )

    def test_remove_empties_the_slot(self, panel: PluginPanel, chain: EffectChain) -> None:
        panel.load_plugin("/plugins/FakeVerb.vst3")

        assert panel.remove_plugin()

        assert not panel.has_plugin
        assert not any(isinstance(effect, PluginEffectAdapter) for effect in chain)
        assert panel.parameter_rows == {}
        assert not panel.bypass_button.isEnabled()
        assert panel.remove_plugin() is False

    def test_there_is_only_one_slot(self, chain: EffectChain) -> None:
        hosts = [FakeHost("/plugins/First.vst3"), FakeHost("/plugins/Second.vst3")]
        panel = PluginPanel(chain, loader=lambda _path: PluginEffectAdapter(hosts.pop(0)))

        panel.load_plugin("/plugins/First.vst3")
        panel.load_plugin("/plugins/Second.vst3")

        adapters = [e for e in chain if isinstance(e, PluginEffectAdapter)]
        assert len(adapters) == 1
        assert adapters[0].plugin_name == "Second"
        assert panel.plugin_name == "Second"

    def test_a_failed_load_keeps_the_working_plugin(self, chain: EffectChain) -> None:
        host = FakeHost()

        def loader(path: str | Path) -> PluginEffectAdapter:
            if "Broken" in str(path):
                raise PluginLoadError("pedalboard could not load Broken.vst3")
            return PluginEffectAdapter(host)

        panel = PluginPanel(chain, loader=loader)
        panel.load_plugin("/plugins/FakeVerb.vst3")

        assert panel.load_plugin("/plugins/Broken.vst3") is False

        assert panel.plugin_name == "FakeVerb"
        assert "Broken.vst3" in panel.message.text()
        assert len([e for e in chain if isinstance(e, PluginEffectAdapter)]) == 1

    def test_read_parameters_pulls_the_controls_back_from_the_plugin(
        self, panel: PluginPanel, host: FakeHost
    ) -> None:
        panel.load_plugin("/plugins/FakeVerb.vst3")
        host.set_parameter("drive", 0.9)

        panel.read_parameters()

        assert panel.parameter_rows["drive"].value == pytest.approx(0.9)

    def test_switching_chains_carries_the_plugin_over(
        self, panel: PluginPanel, chain: EffectChain
    ) -> None:
        panel.load_plugin("/plugins/FakeVerb.vst3")
        other = EffectChain([GainEffect()])

        panel.set_chain(other)

        assert not any(isinstance(effect, PluginEffectAdapter) for effect in chain)
        assert isinstance(other[-1], PluginEffectAdapter)

    def test_a_panel_without_a_chain_still_loads(self, host: FakeHost) -> None:
        panel = PluginPanel(loader=lambda _path: PluginEffectAdapter(host))
        assert panel.load_plugin("/plugins/FakeVerb.vst3")
        assert panel.remove_plugin()


# -- the missing extra -------------------------------------------------------


@pytest.fixture()
def no_pedalboard(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make ``import pedalboard`` raise ImportError even when it is installed."""
    monkeypatch.setitem(sys.modules, "pedalboard", None)


class TestMissingExtra:
    def test_the_factory_raises_an_actionable_error(self, no_pedalboard: None) -> None:
        with pytest.raises(PluginLoadError) as excinfo:
            create_plugin_effect("/plugins/Reverb.vst3")
        message = str(excinfo.value)
        assert 'pip install "audio-studio[plugins]"' in message
        assert "GPL-3.0" in message

    def test_the_factory_still_rejects_unknown_backends(self) -> None:
        with pytest.raises(ValueError, match="carla"):
            create_plugin_effect("/plugins/Reverb.vst3", backend="carla")

    def test_the_panel_explains_the_extra_instead_of_raising(
        self, chain: EffectChain, no_pedalboard: None
    ) -> None:
        panel = PluginPanel(chain)  # the real loader, with pedalboard blocked

        assert panel.load_plugin("/plugins/Reverb.vst3") is False

        message = panel.message.text()
        assert 'pip install "audio-studio[plugins]"' in message
        assert "GPL-3.0" in message
        assert not panel.has_plugin
        assert not any(isinstance(effect, PluginEffectAdapter) for effect in chain)

    def test_the_panel_says_so_before_a_file_is_even_picked(
        self, no_pedalboard: None
    ) -> None:
        assert plugins_extra_installed() is False
        assert 'pip install "audio-studio[plugins]"' in PluginPanel().message.text()

    def test_the_module_imports_without_pedalboard(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The panel is in the default import graph; it must not need the extra."""
        monkeypatch.setitem(sys.modules, "pedalboard", None)
        for name in [
            n
            for n in sys.modules
            if n.startswith(("audio_studio.plugins", "audio_studio.ui.plugin_panel"))
        ]:
            monkeypatch.delitem(sys.modules, name)

        module = importlib.import_module("audio_studio.ui.plugin_panel")

        assert module.plugins_extra_installed() is False


# -- the dock ----------------------------------------------------------------


@pytest.fixture()
def window() -> MainWindow:
    main = MainWindow(AudioEngine(NullOutput(realtime=False), block_size=256))
    yield main
    main._mark_project_saved()  # noqa: SLF001 - avoid blocking close prompts in tests
    main.close()


class TestMainWindowIntegration:
    def test_the_dock_sits_beside_the_effects_rack(self, window: MainWindow) -> None:
        assert window.plugin_dock.windowTitle() == "VST3 Plugin"
        assert window.plugin_dock.widget() is window.plugin_panel
        assert window.plugin_panel.chain is window.effect_chain
        assert window.tabifiedDockWidgets(window.effects_dock) == [window.plugin_dock]

    def test_the_dock_is_toggleable_from_the_view_menu(self, window: MainWindow) -> None:
        titles = [action.text() for action in window.menuBar().actions()]
        view = window.menuBar().actions()[titles.index("&View")].menu()
        assert window.plugin_dock.toggleViewAction() in view.actions()

    def test_a_loaded_plugin_shows_up_in_the_rack_summary(
        self, window: MainWindow, host: FakeHost
    ) -> None:
        window.plugin_panel._loader = lambda _path: PluginEffectAdapter(  # noqa: SLF001
            host
        )

        window.plugin_panel.load_plugin("/plugins/FakeVerb.vst3")

        assert "VST3: FakeVerb" in window.effect_rack.summary()
        assert "VST3: FakeVerb" in window.status_fx.text()

        window.plugin_panel.remove_plugin()

        assert "VST3" not in window.status_fx.text()

    def test_the_plugin_processes_on_the_preview_path(
        self, window: MainWindow, host: FakeHost
    ) -> None:
        window.plugin_panel._loader = lambda _path: PluginEffectAdapter(  # noqa: SLF001
            host
        )
        window.plugin_panel.load_plugin("/plugins/FakeVerb.vst3")

        block = np.ones((16, 2), dtype=np.float32)
        out = window.preview.process_block(block, 48_000)

        np.testing.assert_allclose(out, block * 0.5)
        assert host.process_calls


# -- real pedalboard (only with the plugins extra installed) -----------------


@requires_pedalboard
def test_the_extra_is_detected_when_installed() -> None:
    assert plugins_extra_installed() is True


@requires_pedalboard
def test_a_missing_plugin_file_reaches_the_panel_as_a_message(
    chain: EffectChain, tmp_path: Path
) -> None:
    panel = PluginPanel(chain)

    assert panel.load_plugin(tmp_path / "does-not-exist.vst3") is False

    assert "does-not-exist" in panel.message.text()
