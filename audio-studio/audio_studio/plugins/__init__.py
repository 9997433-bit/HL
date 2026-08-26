"""External plugin hosting (VST3) — optional, not enabled by default.

Importing this package is always safe: the GPL-3.0 pedalboard backend is
imported lazily, and only when a plugin is actually loaded. Without the
``plugins`` extra installed (``pip install "audio-studio[plugins]"``), any
attempt to load a plugin raises
:class:`~audio_studio.plugins.pedalboard_bridge.PluginLoadError` with
installation instructions.

A loaded plugin reaches the effect rack through
:class:`~audio_studio.plugins.adapter.PluginEffectAdapter`, which presents a
host as an ordinary :class:`~audio_studio.dsp.effects.base.Effect`; the
:class:`~audio_studio.ui.plugin_panel.PluginPanel` dock drives three such slots.
:mod:`audio_studio.plugins.scanner` finds the bundles those slots can load,
reading only the filesystem — a scan never loads plugin code and never touches
pedalboard. Projects remember which bundles were loaded, by path; plugin
parameter state is still not persisted.
"""

from .adapter import PluginEffectAdapter, create_plugin_effect
from .host import PluginHost, available_backends, create_plugin_host
from .pedalboard_bridge import PluginLoadError, VST3PluginWrapper
from .scanner import PluginDescriptor, PluginScanError, ScanCache, discover_plugins

__all__ = [
    "PluginDescriptor",
    "PluginEffectAdapter",
    "PluginHost",
    "PluginLoadError",
    "PluginScanError",
    "ScanCache",
    "VST3PluginWrapper",
    "available_backends",
    "create_plugin_effect",
    "create_plugin_host",
    "discover_plugins",
]
