"""Adapter that lets a :class:`~audio_studio.plugins.host.PluginHost` sit in a rack.

:mod:`audio_studio.plugins.host` deliberately keeps external plugins outside the
:class:`~audio_studio.dsp.effects.base.Effect` hierarchy: channel negotiation,
latency reporting and state persistence differ enough from a native processor
that conflating the two would push plugin quirks into every effect. This module
is the one-way bridge instead — an ``Effect`` that owns a host and forwards
blocks to it, so a loaded VST3 can be inserted into the preview chain the effect
rack already drives.

Importing this module is safe without the ``plugins`` extra: it touches only the
abstract host contract. pedalboard is reached lazily through
:func:`~audio_studio.plugins.host.create_plugin_host`, which
:func:`create_plugin_effect` calls at load time and not before.

The adapter is a *preview* insert like the rest of the rack, and inherits the
host's thread contract: plugins run on the render/preview thread, never inside a
device callback.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from ..dsp.effects.base import Effect
from .host import PluginHost, create_plugin_host

__all__ = ["PluginEffectAdapter", "create_plugin_effect"]


class PluginEffectAdapter(Effect):
    """An :class:`Effect` that processes through a hosted external plugin.

    The adapter adds the two controls the rack expects — :attr:`Effect.enabled`
    (bypass) and :attr:`Effect.mix` — on top of a host that has neither, and
    keeps the host's streaming state intact: :meth:`prepare` and :meth:`reset`
    are forwarded, so block-to-block continuity is the plugin's own.

    Parameters
    ----------
    host:
        The loaded plugin. The adapter takes no ownership beyond calling the
        :class:`PluginHost` contract.
    enabled, mix:
        Standard :class:`Effect` insert controls.

    Examples
    --------
    >>> import numpy as np
    >>> class DoublingHost(PluginHost):
    ...     name = "Doubler"
    ...     plugin_path = Path("/plugins/Doubler.vst3")
    ...     def prepare(self, sample_rate, n_channels): pass
    ...     def process_block(self, block, sample_rate): return block * 2.0
    ...     def latency_samples(self): return 0
    ...     def parameters(self): return {"drive": 0.5}
    >>> adapter = PluginEffectAdapter(DoublingHost())
    >>> adapter.name
    'VST3: Doubler'
    >>> float(adapter.process_block(np.ones(4, dtype=np.float32), 48_000)[0])
    2.0
    >>> adapter.bypass = True
    >>> float(adapter.process_block(np.ones(4, dtype=np.float32), 48_000)[0])
    1.0
    """

    #: A plugin's bypass is a live A/B toggle: the delay-compensated preview
    #: keeps padding for a bypassed plugin so toggling it does not move the
    #: stream in time. See :meth:`EffectChain.latency_samples`.
    compensate_when_bypassed = True

    def __init__(self, host: PluginHost, enabled: bool = True, mix: float = 1.0) -> None:
        super().__init__(enabled=enabled, mix=mix)
        self.host = host
        self.name = f"VST3: {host.name}"

    # -- host access -------------------------------------------------------

    @property
    def plugin_name(self) -> str:
        """Display name reported by the plugin itself."""
        return self.host.name

    @property
    def plugin_path(self) -> Path:
        """Bundle the plugin was loaded from."""
        return self.host.plugin_path

    def latency_samples(self) -> int:
        """Processing delay the plugin reports, in samples."""
        return int(self.host.latency_samples())

    def plugin_parameters(self) -> dict[str, Any]:
        """The plugin's own parameter snapshot, without the insert controls."""
        return dict(self.host.parameters())

    def set_parameter(self, name: str, value: Any) -> None:
        """Write one plugin parameter through to the host.

        Raises
        ------
        NotImplementedError
            When the backend cannot write parameters.
        KeyError
            When the plugin has no parameter called ``name``.
        """
        self.host.set_parameter(name, value)

    def state_blob(self) -> bytes | None:
        """The host's opaque state snapshot, for project persistence."""
        return self.host.state_blob()

    def restore_state(self, blob: bytes) -> bool:
        """Apply a saved :meth:`state_blob` back to the host; best-effort."""
        return bool(self.host.restore_state(blob))

    # -- Effect ------------------------------------------------------------

    def prepare(self, sample_rate: float, n_channels: int) -> None:
        super().prepare(sample_rate, n_channels)
        self.host.prepare(float(sample_rate), int(n_channels))

    def reset(self) -> None:
        self.host.reset()

    def parameters(self) -> dict[str, Any]:
        return {
            **super().parameters(),
            "plugin": self.host.name,
            "plugin_path": str(self.host.plugin_path),
            "plugin_parameters": self.plugin_parameters(),
        }

    def _process_planar(self, audio: np.ndarray, sample_rate: float) -> np.ndarray:
        out = np.asarray(
            self.host.process_block(audio, float(sample_rate)), dtype=np.float32
        )
        if out.shape != audio.shape:
            # A plugin that changes the block geometry cannot be spliced into a
            # rack: the chain's dry/wet mix and the ring buffer both assume the
            # block it handed over comes back the same size.
            raise ValueError(
                f"plugin {self.host.name!r} returned {out.shape} for a "
                f"{audio.shape} block; block geometry must be preserved"
            )
        return out


def create_plugin_effect(
    plugin_path: str | Path,
    *,
    backend: str = "pedalboard",
    **kwargs: Any,
) -> PluginEffectAdapter:
    """Load an external plugin and return it wrapped as an :class:`Effect`.

    Thin composition of :func:`~audio_studio.plugins.host.create_plugin_host`
    and :class:`PluginEffectAdapter`; it raises exactly what the factory raises.

    Raises
    ------
    ValueError
        For an unknown ``backend`` identifier.
    PluginLoadError
        When the ``plugins`` extra is not installed or the plugin cannot be
        loaded.
    """
    return PluginEffectAdapter(create_plugin_host(plugin_path, backend=backend, **kwargs))
