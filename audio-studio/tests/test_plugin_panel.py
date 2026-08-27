"""The VST3 plugin rack: adapters, the three slots, the dock, the missing extra.

pedalboard (GPL-3.0) is not a test dependency. Every test here runs without it:
the panel is driven through an injected loader that returns a fake host, scans
are injected too, and the error paths block ``import pedalboard`` outright. The
two tests that need the real package are skipped unless the ``plugins`` extra is
installed.
"""

from __future__ import annotations

import base64
import importlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from audio_studio.core.engine import AudioEngine
from audio_studio.core.output import NullOutput
from audio_studio.core.session import MultitrackSession
from audio_studio.dsp.effects import EffectChain, GainEffect, LimiterEffect
from audio_studio.plugins import PluginEffectAdapter, PluginHost, PluginLoadError
from audio_studio.plugins.adapter import create_plugin_effect
from audio_studio.plugins.scanner import PluginDescriptor
from audio_studio.project.store import ProjectStore, load_project
from audio_studio.ui.main_window import MainWindow
from audio_studio.ui.plugin_panel import (
    MAX_PARAMETER_ROWS,
    SLOT_COUNT,
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
        latency: int = 128,
    ) -> None:
        self._path = Path(path)
        self._parameters = dict(
            parameters if parameters is not None else {"drive": 0.25, "mix": 1.0}
        )
        self._writable = writable
        self._latency = int(latency)
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
        return self._latency

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
    """A panel whose every slot loads the one fake host, for parameter tests."""
    return PluginPanel(chain, loader=lambda _path: PluginEffectAdapter(host))


class FakeLoader:
    """Mints one :class:`FakeHost` per path and remembers it by plugin name."""

    def __init__(self, **host_kwargs: Any) -> None:
        self.hosts: dict[str, FakeHost] = {}
        self._host_kwargs = host_kwargs

    def __call__(self, path: str | Path) -> PluginEffectAdapter:
        host = FakeHost(path, **self._host_kwargs)
        self.hosts[host.name] = host
        return PluginEffectAdapter(host)


@pytest.fixture()
def rack(chain: EffectChain) -> PluginPanel:
    """A panel where each loaded path becomes a distinct plugin."""
    return PluginPanel(chain, loader=FakeLoader())


def plugin_names(chain: EffectChain) -> list[str]:
    """The plugins in the chain, in the order they process."""
    return [
        effect.plugin_name for effect in chain if isinstance(effect, PluginEffectAdapter)
    ]


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
    def test_it_starts_with_three_empty_slots(self, panel: PluginPanel) -> None:
        assert len(panel.slots) == SLOT_COUNT == 3
        assert not panel.has_plugin
        assert panel.plugin_name is None
        assert panel.adapters == []
        assert panel.summary() == "Plugins: none"
        for slot in panel.slots:
            assert not slot.has_plugin
            assert slot.name_label.text() == "Empty"
            assert slot.load_button.isEnabled()
            assert not slot.bypass_button.isEnabled()
            assert not slot.remove_button.isEnabled()
            assert not slot.up_button.isEnabled()
            assert not slot.down_button.isEnabled()

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
        assert "FakeVerb" in panel.slots[0].name_label.text()
        assert panel.slots[0].bypass_button.isEnabled()
        assert panel.slots[0].remove_button.isEnabled()
        assert panel.summary() == "Plugins: FakeVerb (active)"

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

        panel.slots[0].bypass_button.setChecked(True)

        assert panel.adapter is not None and panel.adapter.bypass
        assert panel.adapter not in chain.active
        assert panel.summary() == "Plugins: FakeVerb (bypassed)"
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
        assert not panel.slots[0].bypass_button.isEnabled()
        assert panel.remove_plugin() is False

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


# -- three slots -------------------------------------------------------------


class TestThreeSlots:
    def test_each_slot_loads_independently(
        self, rack: PluginPanel, chain: EffectChain
    ) -> None:
        assert rack.load_plugin("/plugins/First.vst3")
        assert rack.load_plugin("/plugins/Second.vst3")
        assert rack.load_plugin("/plugins/Third.vst3")

        assert [slot.adapter.plugin_name for slot in rack.slots] == [
            "First",
            "Second",
            "Third",
        ]
        assert rack.summary() == (
            "Plugins: First (active), Second (active), Third (active)"
        )

    def test_a_load_without_a_slot_fills_the_first_free_one(
        self, rack: PluginPanel
    ) -> None:
        rack.load_plugin("/plugins/First.vst3", slot=2)
        rack.load_plugin("/plugins/Second.vst3")

        assert rack.slots[0].adapter is not None
        assert rack.slots[0].adapter.plugin_name == "Second"
        assert rack.slots[1].adapter is None

    def test_a_full_rack_replaces_the_selected_slot(self, rack: PluginPanel) -> None:
        for name in ("First", "Second", "Third"):
            rack.load_plugin(f"/plugins/{name}.vst3")
        rack.set_active_slot(1)

        rack.load_plugin("/plugins/Fourth.vst3")

        assert [slot.adapter.plugin_name for slot in rack.slots] == [
            "First",
            "Fourth",
            "Third",
        ]

    def test_the_slots_run_in_order_ahead_of_the_limiter(
        self, rack: PluginPanel, chain: EffectChain
    ) -> None:
        rack.load_plugin("/plugins/Third.vst3", slot=2)
        rack.load_plugin("/plugins/First.vst3", slot=0)
        rack.load_plugin("/plugins/Second.vst3", slot=1)

        assert plugin_names(chain) == ["First", "Second", "Third"]
        assert [type(effect).__name__ for effect in chain][-1] == "LimiterEffect"

    def test_an_empty_slot_leaves_no_gap_in_the_chain(
        self, rack: PluginPanel, chain: EffectChain
    ) -> None:
        rack.load_plugin("/plugins/First.vst3", slot=0)
        rack.load_plugin("/plugins/Third.vst3", slot=2)

        assert plugin_names(chain) == ["First", "Third"]

    def test_replacing_a_slot_drops_the_plugin_it_held(
        self, rack: PluginPanel, chain: EffectChain
    ) -> None:
        rack.load_plugin("/plugins/First.vst3", slot=0)
        rack.load_plugin("/plugins/Replacement.vst3", slot=0)

        assert plugin_names(chain) == ["Replacement"]

    def test_removing_one_slot_leaves_the_others_running(
        self, rack: PluginPanel, chain: EffectChain
    ) -> None:
        for name in ("First", "Second", "Third"):
            rack.load_plugin(f"/plugins/{name}.vst3")

        assert rack.remove_plugin(1)

        assert plugin_names(chain) == ["First", "Third"]
        assert rack.slots[1].name_label.text() == "Empty"

    def test_each_slot_bypasses_on_its_own(
        self, rack: PluginPanel, chain: EffectChain
    ) -> None:
        rack.load_plugin("/plugins/First.vst3")
        rack.load_plugin("/plugins/Second.vst3")

        rack.slots[0].bypass_button.setChecked(True)

        assert rack.slots[0].adapter.bypass
        assert not rack.slots[1].adapter.bypass
        assert rack.summary() == "Plugins: First (bypassed), Second (active)"
        # One bypassed plugin, one halving the signal.
        np.testing.assert_allclose(
            chain.process_block(np.ones((2, 8), dtype=np.float32), 48_000),
            np.full((2, 8), 0.5, dtype=np.float32),
        )

    def test_all_three_plugins_process_in_series(
        self, rack: PluginPanel, chain: EffectChain
    ) -> None:
        for name in ("First", "Second", "Third"):
            rack.load_plugin(f"/plugins/{name}.vst3")

        out = chain.process_block(np.ones((2, 8), dtype=np.float32), 48_000)

        np.testing.assert_allclose(out, np.full((2, 8), 0.125, dtype=np.float32))

    def test_an_out_of_range_slot_is_refused(self, rack: PluginPanel) -> None:
        with pytest.raises(IndexError, match="outside 0..2"):
            rack.load_plugin("/plugins/First.vst3", slot=SLOT_COUNT)

    def test_the_selected_slot_owns_the_parameter_view(self, rack: PluginPanel) -> None:
        rack.load_plugin("/plugins/First.vst3")
        rack.load_plugin("/plugins/Second.vst3")
        loader = rack._loader  # noqa: SLF001 - the FakeLoader the fixture installed
        loader.hosts["First"].set_parameter("drive", 0.9)

        rack.set_active_slot(0)

        assert rack.plugin_name == "First"
        assert rack.parameter_rows["drive"].value == pytest.approx(0.9)
        assert rack.parameter_box.title() == "Parameters — Slot 1"

    def test_clicking_a_slot_selects_it(self, rack: PluginPanel) -> None:
        rack.load_plugin("/plugins/First.vst3")
        rack.load_plugin("/plugins/Second.vst3")

        rack.slots[0].selected.emit(0)

        assert rack.active_slot == 0
        assert rack.plugin_name == "First"

    def test_switching_chains_carries_every_slot_over(
        self, rack: PluginPanel, chain: EffectChain
    ) -> None:
        rack.load_plugin("/plugins/First.vst3")
        rack.load_plugin("/plugins/Second.vst3")
        other = EffectChain([GainEffect(), LimiterEffect(enabled=False)])

        rack.set_chain(other)

        assert plugin_names(chain) == []
        assert plugin_names(other) == ["First", "Second"]


class TestReordering:
    def test_moving_a_plugin_down_swaps_the_chain_order(
        self, rack: PluginPanel, chain: EffectChain
    ) -> None:
        rack.load_plugin("/plugins/First.vst3")
        rack.load_plugin("/plugins/Second.vst3")

        assert rack.move_slot(0, 1)

        assert plugin_names(chain) == ["Second", "First"]
        assert rack.active_slot == 1
        assert rack.plugin_name == "First"

    def test_moving_up_is_the_inverse(self, rack: PluginPanel, chain: EffectChain) -> None:
        rack.load_plugin("/plugins/First.vst3")
        rack.load_plugin("/plugins/Second.vst3")

        rack.move_slot(1, -1)

        assert plugin_names(chain) == ["Second", "First"]

    def test_moving_into_an_empty_slot_just_moves(
        self, rack: PluginPanel, chain: EffectChain
    ) -> None:
        rack.load_plugin("/plugins/First.vst3", slot=0)

        assert rack.move_slot(0, 1)

        assert rack.slots[0].adapter is None
        assert rack.slots[1].adapter is not None
        assert plugin_names(chain) == ["First"]

    def test_the_buttons_drive_the_move(self, rack: PluginPanel, chain: EffectChain) -> None:
        rack.load_plugin("/plugins/First.vst3")
        rack.load_plugin("/plugins/Second.vst3")

        rack.slots[1].up_button.click()

        assert plugin_names(chain) == ["Second", "First"]

    def test_the_ends_of_the_rack_cannot_move_further(self, rack: PluginPanel) -> None:
        rack.load_plugin("/plugins/First.vst3", slot=0)
        rack.load_plugin("/plugins/Third.vst3", slot=2)

        assert rack.move_slot(0, -1) is False
        assert rack.move_slot(2, 1) is False
        assert not rack.slots[0].up_button.isEnabled()
        assert not rack.slots[2].down_button.isEnabled()
        assert rack.slots[0].down_button.isEnabled()

    def test_an_empty_slot_has_nothing_to_move(self, rack: PluginPanel) -> None:
        assert rack.move_slot(0, 1) is False

    def test_reordering_survives_a_bypass(
        self, rack: PluginPanel, chain: EffectChain
    ) -> None:
        rack.load_plugin("/plugins/First.vst3")
        rack.load_plugin("/plugins/Second.vst3")
        rack.slots[0].bypass_button.setChecked(True)

        rack.move_slot(0, 1)

        assert plugin_names(chain) == ["Second", "First"]
        assert rack.slots[1].adapter.bypass
        assert rack.slots[1].bypass_button.isChecked()


class TestLatencyReadout:
    def test_it_starts_at_zero(self, rack: PluginPanel) -> None:
        assert rack.total_latency_samples() == 0
        assert rack.latency_label.text() == "Plugin latency: 0 samples"

    def test_it_sums_every_loaded_plugin(self, chain: EffectChain) -> None:
        panel = PluginPanel(chain, loader=FakeLoader(latency=128))

        panel.load_plugin("/plugins/First.vst3")
        panel.load_plugin("/plugins/Second.vst3")

        assert panel.total_latency_samples() == 256
        assert panel.latency_label.text() == "Plugin latency: 256 samples (compensated)"

    def test_with_pdc_off_the_readout_warns_instead(self, chain: EffectChain) -> None:
        panel = PluginPanel(chain, loader=FakeLoader(latency=128))
        panel.load_plugin("/plugins/First.vst3")
        panel.load_plugin("/plugins/Second.vst3")

        panel.set_pdc_enabled(False)

        assert panel.latency_label.text() == "Plugin latency: 256 samples (not compensated)"

    def test_a_bypassed_plugin_adds_no_delay(self, chain: EffectChain) -> None:
        """Bypass takes the plugin out of the path, latency included."""
        panel = PluginPanel(chain, loader=FakeLoader(latency=128))
        panel.load_plugin("/plugins/First.vst3")
        panel.load_plugin("/plugins/Second.vst3")

        panel.slots[0].bypass_button.setChecked(True)

        assert panel.total_latency_samples() == 128
        # The compensated figure is the constant the path is padded to, so a
        # bypassed slot stays in it — that is what makes the toggle seamless.
        assert panel.compensated_latency_samples() == 256

    def test_removing_a_plugin_takes_its_delay_with_it(self, chain: EffectChain) -> None:
        panel = PluginPanel(chain, loader=FakeLoader(latency=64))
        panel.load_plugin("/plugins/First.vst3")

        panel.remove_plugin(0)

        assert panel.total_latency_samples() == 0
        assert panel.latency_label.text() == "Plugin latency: 0 samples"

    def test_a_host_that_cannot_report_latency_counts_as_zero(
        self, chain: EffectChain
    ) -> None:
        host = FakeHost()
        host.latency_samples = lambda: None  # type: ignore[method-assign]
        panel = PluginPanel(chain, loader=lambda _path: PluginEffectAdapter(host))

        panel.load_plugin("/plugins/FakeVerb.vst3")

        assert panel.total_latency_samples() == 0


# -- scanning ----------------------------------------------------------------


def descriptor(name: str, *, vendor: str = "Acme Audio") -> PluginDescriptor:
    return PluginDescriptor(
        id=f"{name}-0000abcd", name=name, path=Path(f"/plugins/{name}.vst3"), vendor=vendor
    )


class TestScanBrowser:
    def test_the_combo_is_empty_until_something_is_scanned(
        self, rack: PluginPanel
    ) -> None:
        assert rack.discovered == []
        assert not rack.plugin_combo.isEnabled()
        assert not rack.scan_load_button.isEnabled()
        assert rack.selected_descriptor() is None

    def test_a_scan_fills_the_combo(self, chain: EffectChain, tmp_path: Path) -> None:
        found = [descriptor("Great Verb"), descriptor("Tiny Comp", vendor="Bolt")]
        panel = PluginPanel(chain, loader=FakeLoader(), scanner=lambda _dir: found)

        assert panel.scan_directory(tmp_path) == found

        assert panel.plugin_combo.count() == 2
        assert panel.plugin_combo.itemText(0) == "Great Verb — Acme Audio"
        assert panel.plugin_combo.isEnabled()
        assert panel.scan_load_button.isEnabled()
        assert f"Found 2 plugins in {tmp_path}" in panel.message.text()

    def test_an_empty_folder_says_so(self, chain: EffectChain, tmp_path: Path) -> None:
        panel = PluginPanel(chain, loader=FakeLoader(), scanner=lambda _dir: [])

        assert panel.scan_directory(tmp_path) == []

        assert not panel.plugin_combo.isEnabled()
        assert panel.plugin_combo.currentText() == "No plugins found"
        assert "No .vst3 plugins under" in panel.message.text()

    def test_a_real_scan_finds_a_bundle_on_disk(
        self, chain: EffectChain, tmp_path: Path
    ) -> None:
        """End to end through the scanner, with a bundle that is only files."""
        bundle = tmp_path / "GreatVerb.vst3" / "Contents"
        bundle.mkdir(parents=True)
        panel = PluginPanel(chain, loader=FakeLoader())

        found = panel.scan_directory(tmp_path)

        assert [item.name for item in found] == ["GreatVerb"]

    def test_loading_the_selection_fills_a_slot(
        self, chain: EffectChain, tmp_path: Path
    ) -> None:
        panel = PluginPanel(
            chain, loader=FakeLoader(), scanner=lambda _dir: [descriptor("GreatVerb")]
        )
        panel.scan_directory(tmp_path)

        assert panel.load_selected()

        assert plugin_names(chain) == ["GreatVerb"]

    def test_loading_with_nothing_scanned_is_a_message_not_a_crash(
        self, rack: PluginPanel
    ) -> None:
        assert rack.load_selected() is False
        assert "Scan a folder first" in rack.message.text()

    def test_a_scan_that_fails_is_reported(
        self, chain: EffectChain, tmp_path: Path
    ) -> None:
        def explode(_directory: Path) -> list[PluginDescriptor]:
            raise OSError("permission denied")

        panel = PluginPanel(chain, loader=FakeLoader(), scanner=explode)

        assert panel.scan_directory(tmp_path) == []
        assert "Could not scan" in panel.message.text()


# -- project state -----------------------------------------------------------


def placement(entries: list[dict]) -> list[dict]:
    """The slot/path/bypass triple of each entry, with the state blob left out."""
    return [{k: e[k] for k in ("slot", "path", "bypass")} for e in entries]


class TestProjectState:
    def test_an_empty_rack_writes_nothing(self, rack: PluginPanel) -> None:
        assert rack.project_state() == []

    def test_it_records_the_path_and_slot_of_each_plugin(self, rack: PluginPanel) -> None:
        rack.load_plugin("/plugins/First.vst3", slot=0)
        rack.load_plugin("/plugins/Third.vst3", slot=2)
        rack.slots[2].bypass_button.setChecked(True)

        assert placement(rack.project_state()) == [
            {"slot": 0, "path": "/plugins/First.vst3", "bypass": False},
            {"slot": 2, "path": "/plugins/Third.vst3", "bypass": True},
        ]

    def test_it_records_each_plugin_s_state_blob(self, rack: PluginPanel) -> None:
        """FakeHost has no native chunk, so the blob is its parameter JSON."""
        rack.load_plugin("/plugins/First.vst3", slot=0)
        loader = rack._loader  # noqa: SLF001 - the FakeLoader the fixture installed
        loader.hosts["First"].set_parameter("drive", 0.9)

        (entry,) = rack.project_state()

        decoded = json.loads(base64.b64decode(entry["state"]).decode("utf-8"))
        assert decoded == {"drive": 0.9, "mix": 1.0}

    def test_restoring_puts_the_plugins_back_where_they_were(
        self, rack: PluginPanel, chain: EffectChain
    ) -> None:
        state = [
            {"slot": 0, "path": "/plugins/First.vst3", "bypass": False},
            {"slot": 2, "path": "/plugins/Third.vst3", "bypass": True},
        ]

        assert rack.restore_project_state(state) == 2

        assert rack.slots[1].adapter is None
        assert plugin_names(chain) == ["First", "Third"]
        assert rack.slots[2].adapter.bypass
        assert placement(rack.project_state()) == state

    def test_restoring_applies_the_saved_state_blob(self, rack: PluginPanel) -> None:
        blob = base64.b64encode(json.dumps({"drive": 0.8}).encode("utf-8")).decode("ascii")

        rack.restore_project_state(
            [{"slot": 0, "path": "/plugins/First.vst3", "state": blob}]
        )

        loader = rack._loader  # noqa: SLF001
        assert loader.hosts["First"].parameters()["drive"] == pytest.approx(0.8)
        # The freshly built parameter view shows the restored value, not the default.
        assert rack.parameter_rows["drive"].value == pytest.approx(0.8)

    def test_a_corrupt_state_blob_costs_only_itself(self, rack: PluginPanel) -> None:
        """The slot still loads; the plugin just keeps its own defaults."""
        loaded = rack.restore_project_state(
            [{"slot": 0, "path": "/plugins/First.vst3", "state": "%%% not base64 %%%"}]
        )

        assert loaded == 1
        loader = rack._loader  # noqa: SLF001
        assert loader.hosts["First"].parameters() == {"drive": 0.25, "mix": 1.0}

    def test_restoring_replaces_whatever_was_loaded(self, rack: PluginPanel) -> None:
        rack.load_plugin("/plugins/Stale.vst3")

        rack.restore_project_state([{"slot": 0, "path": "/plugins/Fresh.vst3"}])

        assert [slot.adapter is not None for slot in rack.slots] == [True, False, False]
        assert rack.plugin_name == "Fresh"

    def test_restoring_an_empty_project_clears_the_rack(
        self, rack: PluginPanel, chain: EffectChain
    ) -> None:
        rack.load_plugin("/plugins/Stale.vst3")

        assert rack.restore_project_state([]) == 0

        assert not rack.has_plugin
        assert plugin_names(chain) == []

    def test_a_plugin_this_machine_does_not_have_is_reported(
        self, chain: EffectChain
    ) -> None:
        """A project can name a plugin that is not installed here."""

        def loader(path: str | Path) -> PluginEffectAdapter:
            if "Missing" in str(path):
                raise PluginLoadError("pedalboard could not load Missing.vst3")
            return PluginEffectAdapter(FakeHost(path))

        panel = PluginPanel(chain, loader=loader)

        loaded = panel.restore_project_state(
            [
                {"slot": 0, "path": "/plugins/Present.vst3"},
                {"slot": 1, "path": "/plugins/Missing.vst3"},
            ]
        )

        assert loaded == 1
        assert plugin_names(chain) == ["Present"]
        assert "Missing.vst3" in panel.message.text()

    def test_a_project_round_trips_through_the_bundle(
        self, rack: PluginPanel, tmp_path: Path
    ) -> None:
        rack.load_plugin("/plugins/First.vst3", slot=0)
        rack.load_plugin("/plugins/Third.vst3", slot=2)
        rack.slots[2].bypass_button.setChecked(True)
        root = tmp_path / "session.hlproj"

        ProjectStore(root).save(
            edit_session=None,
            editor_clip=None,
            multitrack=MultitrackSession(),
            workspace="waveform",
            view_mode="split",
            playhead=0,
            selection=None,
            plugins=rack.project_state(),
        )
        snapshot = load_project(root)

        assert placement(snapshot.plugins) == [
            {"slot": 0, "path": "/plugins/First.vst3", "bypass": False},
            {"slot": 2, "path": "/plugins/Third.vst3", "bypass": True},
        ]
        # The state blob survives the bundle byte for byte.
        saved = {entry["slot"]: entry.get("state") for entry in rack.project_state()}
        restored = {entry["slot"]: entry.get("state") for entry in snapshot.plugins}
        assert restored == saved
        assert all(state for state in restored.values())

    def test_a_bundle_without_plugins_restores_an_empty_rack(
        self, rack: PluginPanel, tmp_path: Path
    ) -> None:
        root = tmp_path / "session.hlproj"
        ProjectStore(root).save(
            edit_session=None,
            editor_clip=None,
            multitrack=MultitrackSession(),
            workspace="waveform",
            view_mode="split",
            playhead=0,
            selection=None,
        )

        snapshot = load_project(root)

        assert snapshot.plugins == []
        assert "plugins" not in (root / "project.json").read_text(encoding="utf-8")


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

    def test_scanning_still_works_without_the_extra(
        self, no_pedalboard: None, tmp_path: Path
    ) -> None:
        """Discovery reads the filesystem, so it needs no GPL backend at all."""
        (tmp_path / "GreatVerb.vst3").mkdir()
        panel = PluginPanel()

        found = panel.scan_directory(tmp_path)

        assert [item.name for item in found] == ["GreatVerb"]
        assert panel.scan_load_button.isEnabled()

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
        assert window.plugin_dock.windowTitle() == "VST3 Plugins"
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

    def test_three_plugins_process_on_the_preview_path(self, window: MainWindow) -> None:
        window.plugin_panel._loader = FakeLoader()  # noqa: SLF001
        for name in ("First", "Second", "Third"):
            window.plugin_panel.load_plugin(f"/plugins/{name}.vst3")

        out = window.preview.process_block(np.ones((16, 2), dtype=np.float32), 48_000)

        np.testing.assert_allclose(out, np.full((16, 2), 0.125, dtype=np.float32))
        assert plugin_names(window.effect_chain) == ["First", "Second", "Third"]

    def test_saving_and_reopening_a_project_restores_the_rack(
        self, window: MainWindow, tmp_path: Path
    ) -> None:
        window.plugin_panel._loader = FakeLoader()  # noqa: SLF001
        window.plugin_panel.load_plugin("/plugins/First.vst3", slot=0)
        window.plugin_panel.load_plugin("/plugins/Third.vst3", slot=2)
        root = tmp_path / "session.hlproj"

        window._write_project(root)  # noqa: SLF001 - no save dialog in a test
        window.plugin_panel.remove_plugin(0)
        window.plugin_panel.remove_plugin(2)
        window._apply_project(root, load_project(root))  # noqa: SLF001

        assert plugin_names(window.effect_chain) == ["First", "Third"]
        assert window.plugin_panel.slots[1].adapter is None


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
