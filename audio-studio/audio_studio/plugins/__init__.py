"""External plugin hosting (VST3) — optional, not enabled by default.

Importing this package is always safe: the GPL-3.0 pedalboard backend is
imported lazily, and only when a plugin is actually loaded. Without the
``plugins`` extra installed (``pip install "audio-studio[plugins]"``), any
attempt to load a plugin raises
:class:`~audio_studio.plugins.pedalboard_bridge.PluginLoadError` with
installation instructions. Nothing in the default application imports this
package; the effect rack and UI integration are intentionally not wired yet.
"""

from .host import PluginHost, available_backends, create_plugin_host
from .pedalboard_bridge import PluginLoadError, VST3PluginWrapper

__all__ = [
    "PluginHost",
    "PluginLoadError",
    "VST3PluginWrapper",
    "available_backends",
    "create_plugin_host",
]
