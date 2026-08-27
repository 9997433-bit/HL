"""PySide6 front-end widgets."""

from __future__ import annotations

from .colormaps import COLORMAP_NAMES, DEFAULT_COLORMAP, colorize, get_colormap
from .effect_rack import EffectRackPanel, default_preview_chain
from .level_meter import LevelMeter
from .main_window import MainWindow, attach_preview
from .spectrogram_widget import DisplayMode, FrequencyScale, SpectrogramWidget
from .spectrum_panel import SpectrumPanel
from .theme import PALETTE, Palette, stylesheet
from .time_ruler import TimeRuler
from .track_panel import TrackHeader, TrackPanel
from .transport_bar import TransportBar
from .waveform_view import WaveformView

__all__ = [
    "COLORMAP_NAMES",
    "DEFAULT_COLORMAP",
    "PALETTE",
    "DisplayMode",
    "EffectRackPanel",
    "FrequencyScale",
    "LevelMeter",
    "MainWindow",
    "Palette",
    "SpectrogramWidget",
    "SpectrumPanel",
    "TimeRuler",
    "TrackHeader",
    "TrackPanel",
    "TransportBar",
    "WaveformView",
    "attach_preview",
    "colorize",
    "default_preview_chain",
    "get_colormap",
    "stylesheet",
]
