"""PySide6 front-end widgets."""

from __future__ import annotations

from .colormaps import COLORMAP_NAMES, DEFAULT_COLORMAP, colorize, get_colormap
from .level_meter import LevelMeter
from .main_window import MainWindow
from .spectrogram_widget import DisplayMode, FrequencyScale, SpectrogramWidget
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
    "FrequencyScale",
    "LevelMeter",
    "MainWindow",
    "Palette",
    "SpectrogramWidget",
    "TimeRuler",
    "TrackHeader",
    "TrackPanel",
    "TransportBar",
    "WaveformView",
    "colorize",
    "get_colormap",
    "stylesheet",
]
