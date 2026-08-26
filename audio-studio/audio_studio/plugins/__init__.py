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
:class:`~audio_studio.ui.plugin_panel.PluginPanel` dock drives one such slot.
Plugin state is still not persisted into projects.
"""

from .adapter import PluginEffectAdapter, create_plugin_effect
from .host import PluginHost, available_backends, create_plugin_host
from .pedalboard_bridge import PluginLoadError, VST3PluginWrapper

__all__ = [
    "PluginEffectAdapter",
    "PluginHost",
    "PluginLoadError",
    "VST3PluginWrapper",
    "available_backends",
    "create_plugin_effect",
    "create_plugin_host",
]
