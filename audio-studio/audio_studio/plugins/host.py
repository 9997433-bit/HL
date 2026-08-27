"""Abstract external-plugin host contract and the backend factory.

Audio Studio's own processors live in :mod:`audio_studio.dsp.effects`.
External plugin formats (VST3 today, possibly AU later) are reached through a
:class:`PluginHost` implementation instead. Hosts follow the same
``prepare`` / ``process_block`` streaming discipline as native effects so a
later adapter can slot one into an :class:`~audio_studio.dsp.effects.base.EffectChain`,
but they are deliberately *not* ``Effect`` subclasses yet: plugin channel
negotiation, latency reporting and state persistence need to stabilise before
the rack wiring lands.

The only backend today is the optional pedalboard bridge, which is GPL-3.0
and therefore isolated behind the ``plugins`` extra; the licensing boundary is
documented in :mod:`audio_studio.plugins.pedalboard_bridge` and in
``THIRD_PARTY_LICENSES.md``. Importing this module never imports pedalboard.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import numpy as np

__all__ = ["PluginHost", "available_backends", "create_plugin_host"]

#: Backend identifiers accepted by :func:`create_plugin_host`.
_BACKENDS: tuple[str, ...] = ("pedalboard",)


class PluginHost(ABC):
    """Streaming contract implemented by every external-plugin host.

    The life cycle mirrors :class:`audio_studio.dsp.effects.base.Effect`:
    :meth:`prepare` fixes the stream format and clears processor state, then
    :meth:`process_block` is called with consecutive blocks and must carry
    plugin state across calls. Implementations are not real-time safe and
    must only be used on render/preview threads, never inside a device
    callback.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Display name of the loaded plugin."""

    @property
    @abstractmethod
    def plugin_path(self) -> Path:
        """Path the plugin binary was loaded from."""

    @abstractmethod
    def prepare(self, sample_rate: float, n_channels: int) -> None:
        """Fix the stream format and reset processor state."""

    @abstractmethod
    def process_block(self, block: np.ndarray, sample_rate: float) -> np.ndarray:
        """Process one planar ``(n_channels, n_samples)`` block, keeping state."""

    @abstractmethod
    def latency_samples(self) -> int:
        """Processing latency reported by the plugin, in samples."""

    @abstractmethod
    def parameters(self) -> dict[str, Any]:
        """Snapshot of the plugin's parameters, ``{name: value}``."""

    def set_parameter(self, name: str, value: Any) -> None:
        """Write one parameter back to the plugin.

        Optional: a backend that can only read parameters keeps this default,
        which tells the caller so rather than silently dropping the write. A UI
        offering parameter controls is expected to catch it.

        Raises
        ------
        NotImplementedError
            When the backend cannot write parameters.
        KeyError
            When the plugin has no parameter called ``name``.
        """
        raise NotImplementedError(
            f"{type(self).__name__} cannot write plugin parameters"
        )

    def reset(self) -> None:  # noqa: B027 - hosts without state legitimately do nothing
        """Clear streaming state without changing parameters."""

    # -- state persistence ---------------------------------------------------

    def state_blob(self) -> bytes | None:
        """Opaque snapshot of the plugin's settings, for project persistence.

        The default serialises :meth:`parameters` as canonical JSON — the
        portable fallback every host has. A backend with a native state
        format (a VST3 state chunk, say) overrides this and returns that
        instead, because the chunk captures settings the parameter list does
        not (internal routing, sample data, unautomatable options).

        Returns ``None`` when there is nothing worth writing — the caller
        then simply omits the state from the project.
        """
        try:
            return json.dumps(self.parameters(), sort_keys=True).encode("utf-8")
        except (TypeError, ValueError):
            # A parameter value JSON cannot express (an object, NaN with a
            # strict encoder) means no portable snapshot, not an error.
            return None

    def restore_state(self, blob: bytes) -> bool:
        """Apply a :meth:`state_blob` snapshot back to the plugin.

        The default understands the parameter-dict JSON the default
        :meth:`state_blob` writes: each entry is written through
        :meth:`set_parameter`, and entries the plugin no longer has (or a
        backend that cannot write at all) are skipped rather than raised —
        restoring most of a preset beats refusing all of it.

        Returns ``True`` when at least one parameter was applied, ``False``
        when the blob was unreadable or nothing could be written. Never
        raises: state restoration is best-effort by design, because the blob
        was written by a possibly different plugin version on a possibly
        different machine.
        """
        try:
            decoded = json.loads(bytes(blob).decode("utf-8"))
        except (TypeError, ValueError, UnicodeDecodeError):
            return False
        if not isinstance(decoded, dict):
            return False
        restored = False
        for name, value in decoded.items():
            try:
                self.set_parameter(str(name), value)
                restored = True
            except (NotImplementedError, KeyError, TypeError, ValueError):
                continue
        return restored

    def __repr__(self) -> str:
        return f"{type(self).__name__}({str(self.plugin_path)!r})"


def available_backends() -> tuple[str, ...]:
    """Backend identifiers :func:`create_plugin_host` understands.

    A backend being listed does not mean it is installed: the pedalboard
    backend additionally needs the ``plugins`` extra at plugin-load time.
    """
    return _BACKENDS


def create_plugin_host(
    plugin_path: str | Path,
    *,
    backend: str = "pedalboard",
    **kwargs: Any,
) -> PluginHost:
    """Load an external plugin and return the host wrapping it.

    Parameters
    ----------
    plugin_path:
        Path to the plugin binary (a ``.vst3`` bundle for the pedalboard
        backend).
    backend:
        Which host implementation to use; see :func:`available_backends`.
    kwargs:
        Passed through to the backend constructor
        (:class:`~audio_studio.plugins.pedalboard_bridge.VST3PluginWrapper`
        accepts ``plugin_name`` and ``parameter_values``).

    Raises
    ------
    ValueError
        For an unknown ``backend`` identifier.
    PluginLoadError
        When the selected backend's optional dependency is not installed or
        the plugin itself cannot be loaded.
    """
    if backend not in _BACKENDS:
        raise ValueError(
            f"unknown plugin backend {backend!r}; available backends: {_BACKENDS}"
        )
    # Imported here, not at module level: the bridge module is the GPL
    # isolation point and must stay out of import paths that never load
    # plugins (it is still pedalboard-free to import, but keeping the edge
    # lazy makes the boundary auditable).
    from .pedalboard_bridge import VST3PluginWrapper

    return VST3PluginWrapper(plugin_path, **kwargs)
