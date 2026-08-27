"""Isolated pedalboard bridge — the GPL boundary of the plugin host.

`pedalboard <https://github.com/spotify/pedalboard>`_ is GPL-3.0 and
incorporates GPL/commercial components (JUCE, Rubber Band, FFTW), while Audio
Studio itself is MIT. Per ``THIRD_PARTY_LICENSES.md`` the entire contact
surface with pedalboard is confined to this one module:

* pedalboard is **never** imported at module import time — only inside
  :func:`load_pedalboard`, the first time a plugin is actually loaded;
* this module is the only one that names pedalboard at all. The plugin panel
  is part of the default application and therefore imports *this* module, but
  importing it does not import pedalboard, and the panel probes for the extra
  with :func:`importlib.util.find_spec` rather than by trying an import;
* the dependency is installed only by an explicit user action:
  ``pip install "audio-studio[plugins]"``.

Installing pedalboard for private use does not change the license of this
repository's source. Distributing Audio Studio *together with* pedalboard in
one wheel, installer or application bundle creates a combined work that must
be distributed under GPL-3.0 as a whole; official MIT binary artifacts must
not include it.
"""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any

import numpy as np

from .host import PluginHost

__all__ = ["PluginLoadError", "VST3PluginWrapper", "load_pedalboard"]

_INSTALL_HINT = (
    "The VST3 plugin host needs the optional 'pedalboard' package, which is "
    "not installed. Install the plugins extra with:\n\n"
    '    pip install "audio-studio[plugins]"\n\n'
    "Note: pedalboard is GPL-3.0. Installing it for private use is fine, but "
    "any artifact that bundles it with Audio Studio must be distributed under "
    "GPL-3.0 as a whole (see THIRD_PARTY_LICENSES.md)."
)


class PluginLoadError(RuntimeError):
    """An external plugin (or its host backend) could not be loaded."""


def load_pedalboard() -> ModuleType:
    """Import and return the pedalboard module.

    This is the only place in the code base that imports pedalboard.

    Raises
    ------
    PluginLoadError
        When the ``plugins`` extra is not installed, with installation
        instructions and the GPL distribution notice.
    """
    try:
        import pedalboard
    except ImportError as exc:
        raise PluginLoadError(_INSTALL_HINT) from exc
    return pedalboard


class VST3PluginWrapper(PluginHost):
    """A VST3 plugin hosted through ``pedalboard.VST3Plugin``.

    The wrapper follows the :class:`~audio_studio.plugins.host.PluginHost`
    streaming contract: :meth:`prepare` fixes the stream format and resets
    plugin state, then :meth:`process_block` feeds consecutive planar
    ``(n_channels, n_samples)`` float32 blocks with ``reset=False`` so the
    plugin's internal state (filters, delay lines, envelopes) carries across
    block boundaries. A 1-D mono block is accepted and returned as 1-D.

    Parameters
    ----------
    plugin_path:
        Path to the ``.vst3`` bundle.
    plugin_name:
        For container bundles that expose several plugins, which one to load.
    parameter_values:
        Initial parameter values handed to the plugin at load time.
    """

    def __init__(
        self,
        plugin_path: str | Path,
        *,
        plugin_name: str | None = None,
        parameter_values: dict[str, Any] | None = None,
    ) -> None:
        self._plugin_path = Path(plugin_path)
        pedalboard = load_pedalboard()
        try:
            self._plugin = pedalboard.VST3Plugin(
                str(self._plugin_path),
                parameter_values=dict(parameter_values or {}),
                plugin_name=plugin_name,
            )
        except Exception as exc:
            # pedalboard signals load failures inconsistently (ImportError,
            # OSError, RuntimeError depending on what went wrong), so funnel
            # everything into the one exception callers are told to expect.
            raise PluginLoadError(
                f"pedalboard could not load VST3 plugin {str(self._plugin_path)!r}: {exc}"
            ) from exc
        self._sample_rate: float | None = None
        self._n_channels: int | None = None

    # -- PluginHost ---------------------------------------------------------

    @property
    def name(self) -> str:
        reported = getattr(self._plugin, "name", None)
        return str(reported) if reported else self._plugin_path.stem

    @property
    def plugin_path(self) -> Path:
        return self._plugin_path

    def prepare(self, sample_rate: float, n_channels: int) -> None:
        self._sample_rate = float(sample_rate)
        self._n_channels = int(n_channels)
        self.reset()

    def reset(self) -> None:
        reset = getattr(self._plugin, "reset", None)
        if callable(reset):
            reset()

    def process_block(self, block: np.ndarray, sample_rate: float) -> np.ndarray:
        """Process one block, carrying plugin state across calls.

        Not real-time safe: pedalboard crosses into JUCE with the GIL held
        and may allocate, so this belongs on a render/preview thread, never
        in a device callback.
        """
        audio = np.asarray(block, dtype=np.float32)
        was_mono = audio.ndim == 1
        if was_mono:
            audio = audio[np.newaxis, :]
        elif audio.ndim != 2:
            raise ValueError(
                "expected mono (n,) or planar (n_channels, n_samples) audio, "
                f"got shape {audio.shape}"
            )
        rate = float(sample_rate)
        if self._sample_rate != rate or self._n_channels != audio.shape[0]:
            self.prepare(rate, audio.shape[0])
        out = np.asarray(self._plugin.process(audio, rate, reset=False), dtype=np.float32)
        return out[0] if was_mono else out

    def latency_samples(self) -> int:
        """Latency reported by the plugin, in samples; ``0`` when unreported.

        pedalboard ≥ 0.9 compensates ExternalPlugin latency inside
        ``process()`` and does not expose the raw JUCE figure in its public
        API, so ``0`` here means "already compensated upstream or unknown".
        The attribute probe keeps the wrapper forward-compatible with a
        pedalboard release that starts reporting it. A report that is not a
        usable non-negative integer (``None``, a raising property, garbage)
        also counts as ``0``: latency feeds the delay-compensation sum, where
        an unknown figure must degrade to "uncompensated", never to a crash.
        """
        for attr in ("latency_samples", "latency"):
            value = getattr(self._plugin, attr, None)
            if value is None:
                continue
            if callable(value):
                try:
                    value = value()
                except Exception:  # noqa: BLE001 - a broken probe is "unreported"
                    continue
            try:
                return max(int(value), 0)
            except (TypeError, ValueError):
                continue
        return 0

    def parameters(self) -> dict[str, Any]:
        """Normalised parameter snapshot, ``{name: raw_value}``.

        pedalboard exposes parameters as ``AudioProcessorParameter`` objects
        whose ``raw_value`` is the 0–1 normalised host value — the stable
        representation for presets and project state. Parameters without a
        ``raw_value`` are passed through untouched.
        """
        raw = getattr(self._plugin, "parameters", None) or {}
        return {
            str(key): getattr(parameter, "raw_value", parameter)
            for key, parameter in dict(raw).items()
        }

    def set_parameter(self, name: str, value: Any) -> None:
        """Write ``name`` back to the plugin on the same scale :meth:`parameters` reads.

        Parameters exposed as ``AudioProcessorParameter`` objects are written
        through ``raw_value`` (the 0–1 normalised host value); anything else is
        set as a plain attribute on the plugin, which is how pedalboard exposes
        its built-in processors.
        """
        raw = dict(getattr(self._plugin, "parameters", None) or {})
        if name not in raw:
            raise KeyError(f"{self.name!r} has no parameter {name!r}")
        parameter = raw[name]
        if hasattr(parameter, "raw_value"):
            parameter.raw_value = value
        else:
            setattr(self._plugin, name, value)

    # -- state persistence ----------------------------------------------------

    #: Attributes probed for a native state chunk, in preference order.
    #: ``raw_state`` is what pedalboard calls its VST3/AU state bytes; the
    #: plain ``state`` spelling keeps the probe forward-compatible.
    _STATE_ATTRS = ("raw_state", "state")

    def state_blob(self) -> bytes | None:
        """The plugin's own state chunk when pedalboard exposes one.

        A native chunk (``raw_state`` on recent pedalboard releases) captures
        everything the plugin saves — including settings that never appear in
        the parameter list — so it is preferred. A pedalboard build without
        it falls back to the base class's parameter-dict JSON, which restores
        the automatable parameters and nothing more.
        """
        for attr in self._STATE_ATTRS:
            value = getattr(self._plugin, attr, None)
            if callable(value):
                try:
                    value = value()
                except Exception:  # noqa: BLE001 - probe must not break saving
                    continue
            if isinstance(value, (bytes, bytearray)) and value:
                return bytes(value)
        return super().state_blob()

    def restore_state(self, blob: bytes) -> bool:
        """Apply a saved blob, whichever format :meth:`state_blob` wrote it in.

        The parameter-dict JSON fallback is tried first because it is
        self-describing (a JSON object with known parameter names); anything
        that is not that is treated as a native chunk and written back to the
        attribute it was read from. Both paths are best-effort and never
        raise — the blob may come from a different plugin version or a
        machine with a different pedalboard build.
        """
        blob = bytes(blob)
        if super().restore_state(blob):
            return True
        for attr in self._STATE_ATTRS:
            if not hasattr(self._plugin, attr):
                continue
            try:
                setattr(self._plugin, attr, blob)
            except Exception:  # noqa: BLE001 - a rejected chunk is "not restored"
                continue
            return True
        return False
