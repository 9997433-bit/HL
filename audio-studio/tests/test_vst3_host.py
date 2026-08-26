"""VST3 host scaffold: factory dispatch, missing-extra error paths, and the
pedalboard bridge contract exercised against a fake backend.

pedalboard (GPL-3.0) is intentionally not a test dependency: every test in
this module runs without it, either by blocking the import outright or by
installing a fake ``pedalboard`` module into ``sys.modules``. The handful of
tests that need the real package are skipped unless the ``plugins`` extra is
installed.
"""

from __future__ import annotations

import importlib
import importlib.util
import sys
import types
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from audio_studio.plugins import (
    PluginHost,
    PluginLoadError,
    VST3PluginWrapper,
    available_backends,
    create_plugin_host,
    pedalboard_bridge,
)

PEDALBOARD_INSTALLED = importlib.util.find_spec("pedalboard") is not None

requires_pedalboard = pytest.mark.skipif(
    not PEDALBOARD_INSTALLED,
    reason="pedalboard is not installed (needs the 'plugins' extra)",
)


# -- fake pedalboard backend --------------------------------------------------


class FakeParameter:
    def __init__(self, raw_value: float) -> None:
        self.raw_value = raw_value


class FakeVST3Plugin:
    """Stands in for ``pedalboard.VST3Plugin``: records calls, halves gain."""

    def __init__(
        self,
        path: str,
        parameter_values: dict[str, Any] | None = None,
        plugin_name: str | None = None,
    ) -> None:
        if not str(path).endswith(".vst3"):
            # Mirrors pedalboard, which raises ImportError for unloadable files.
            raise ImportError(f"Unable to load plugin {path}")
        self.name = plugin_name or "FakeVerb"
        self.parameter_values = dict(parameter_values or {})
        self.parameters = {"drive": FakeParameter(0.25), "mix": FakeParameter(1.0)}
        self.reset_calls = 0
        self.process_calls: list[tuple[tuple[int, ...], float, bool]] = []

    def reset(self) -> None:
        self.reset_calls += 1

    def process(
        self, audio: np.ndarray, sample_rate: float, reset: bool = True
    ) -> np.ndarray:
        self.process_calls.append((audio.shape, float(sample_rate), bool(reset)))
        return audio * 0.5


@pytest.fixture()
def fake_pedalboard(monkeypatch: pytest.MonkeyPatch) -> types.ModuleType:
    module = types.ModuleType("pedalboard")
    module.VST3Plugin = FakeVST3Plugin  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "pedalboard", module)
    return module


@pytest.fixture()
def no_pedalboard(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make ``import pedalboard`` raise ImportError even when installed."""
    monkeypatch.setitem(sys.modules, "pedalboard", None)


# -- import safety and error paths (never need pedalboard) -------------------


def test_package_imports_without_pedalboard(monkeypatch: pytest.MonkeyPatch) -> None:
    """The plugins package must import cleanly when the extra is missing."""
    monkeypatch.setitem(sys.modules, "pedalboard", None)
    for name in [n for n in sys.modules if n.startswith("audio_studio.plugins")]:
        monkeypatch.delitem(sys.modules, name)
    module = importlib.import_module("audio_studio.plugins")
    assert module.available_backends() == ("pedalboard",)


def test_missing_extra_raises_actionable_error(no_pedalboard: None) -> None:
    with pytest.raises(PluginLoadError) as excinfo:
        VST3PluginWrapper("/plugins/Reverb.vst3")
    message = str(excinfo.value)
    assert 'pip install "audio-studio[plugins]"' in message
    assert "GPL-3.0" in message
    assert isinstance(excinfo.value.__cause__, ImportError)


def test_load_pedalboard_missing_extra(no_pedalboard: None) -> None:
    with pytest.raises(PluginLoadError):
        pedalboard_bridge.load_pedalboard()


def test_factory_missing_extra_raises(no_pedalboard: None) -> None:
    with pytest.raises(PluginLoadError):
        create_plugin_host("/plugins/Reverb.vst3")


def test_factory_rejects_unknown_backend() -> None:
    with pytest.raises(ValueError, match="carla"):
        create_plugin_host("/plugins/Reverb.vst3", backend="carla")


def test_available_backends_lists_pedalboard() -> None:
    assert available_backends() == ("pedalboard",)


# -- factory and wrapper behaviour against the fake backend ------------------


def test_factory_returns_plugin_host(fake_pedalboard: types.ModuleType) -> None:
    host = create_plugin_host("/plugins/Reverb.vst3")
    assert isinstance(host, VST3PluginWrapper)
    assert isinstance(host, PluginHost)
    assert host.plugin_path == Path("/plugins/Reverb.vst3")
    assert host.name == "FakeVerb"


def test_factory_forwards_kwargs(fake_pedalboard: types.ModuleType) -> None:
    host = create_plugin_host(
        "/plugins/Bundle.vst3",
        plugin_name="Second",
        parameter_values={"drive": 0.5},
    )
    assert host.name == "Second"
    assert host._plugin.parameter_values == {"drive": 0.5}  # type: ignore[attr-defined]


def test_unloadable_plugin_wrapped_in_plugin_load_error(
    fake_pedalboard: types.ModuleType,
) -> None:
    with pytest.raises(PluginLoadError, match="NotAPlugin.dll"):
        VST3PluginWrapper("/plugins/NotAPlugin.dll")


def test_process_block_streams_without_resetting(
    fake_pedalboard: types.ModuleType,
) -> None:
    host = VST3PluginWrapper("/plugins/Reverb.vst3")
    host.prepare(48_000, 2)
    plugin = host._plugin
    assert plugin.reset_calls == 1

    block = np.full((2, 256), 0.5, dtype=np.float32)
    out_a = host.process_block(block, 48_000)
    out_b = host.process_block(block, 48_000)

    assert out_a.shape == (2, 256)
    assert out_a.dtype == np.float32
    np.testing.assert_allclose(out_a, block * 0.5)
    np.testing.assert_allclose(out_b, block * 0.5)
    # State must carry across blocks: every call streams with reset=False and
    # the plugin is not re-reset between blocks.
    assert plugin.process_calls == [
        ((2, 256), 48_000.0, False),
        ((2, 256), 48_000.0, False),
    ]
    assert plugin.reset_calls == 1


def test_process_block_prepares_on_format_change(
    fake_pedalboard: types.ModuleType,
) -> None:
    host = VST3PluginWrapper("/plugins/Reverb.vst3")
    block = np.zeros((2, 128), dtype=np.float32)
    host.process_block(block, 44_100)  # auto-prepare on first block
    assert host._plugin.reset_calls == 1
    host.process_block(block, 48_000)  # sample-rate change resets state
    assert host._plugin.reset_calls == 2


def test_process_block_mono_roundtrip(fake_pedalboard: types.ModuleType) -> None:
    host = VST3PluginWrapper("/plugins/Reverb.vst3")
    mono = np.ones(64, dtype=np.float32)
    out = host.process_block(mono, 48_000)
    assert out.shape == (64,)
    np.testing.assert_allclose(out, mono * 0.5)


def test_process_block_rejects_bad_rank(fake_pedalboard: types.ModuleType) -> None:
    host = VST3PluginWrapper("/plugins/Reverb.vst3")
    with pytest.raises(ValueError, match="planar"):
        host.process_block(np.zeros((1, 2, 3), dtype=np.float32), 48_000)


def test_parameters_snapshot_uses_raw_values(
    fake_pedalboard: types.ModuleType,
) -> None:
    host = VST3PluginWrapper("/plugins/Reverb.vst3")
    assert host.parameters() == {"drive": 0.25, "mix": 1.0}


def test_latency_defaults_to_zero_and_probes_plugin(
    fake_pedalboard: types.ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    host = VST3PluginWrapper("/plugins/Reverb.vst3")
    assert host.latency_samples() == 0
    monkeypatch.setattr(host._plugin, "latency_samples", 512, raising=False)
    assert host.latency_samples() == 512


def test_name_falls_back_to_bundle_stem(
    fake_pedalboard: types.ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    host = VST3PluginWrapper("/plugins/GreatEQ.vst3")
    monkeypatch.setattr(host._plugin, "name", "", raising=False)
    assert host.name == "GreatEQ"
    assert repr(host) == "VST3PluginWrapper('/plugins/GreatEQ.vst3')"


# -- real pedalboard (only with the plugins extra installed) -----------------


@requires_pedalboard
def test_real_pedalboard_module_loads() -> None:
    module = pedalboard_bridge.load_pedalboard()
    assert hasattr(module, "VST3Plugin")


@requires_pedalboard
def test_real_missing_plugin_file_raises(tmp_path: Path) -> None:
    with pytest.raises(PluginLoadError, match="does-not-exist"):
        VST3PluginWrapper(tmp_path / "does-not-exist.vst3")
