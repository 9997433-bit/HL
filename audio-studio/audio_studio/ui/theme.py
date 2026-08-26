"""Dark studio palette and stylesheet.

Colours are kept in one place so the waveform renderer, the meters and the
widget chrome stay visually consistent, and so a light theme can later be
added by swapping a single :class:`Palette` instance.
"""

from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtGui import QColor


@dataclass(frozen=True, slots=True)
class Palette:
    """Named colours used across the application."""

    window: str = "#1b1d21"
    surface: str = "#232629"
    surface_alt: str = "#2b2f33"
    border: str = "#3a3f45"
    text: str = "#d7dade"
    text_dim: str = "#8b9299"
    accent: str = "#3daee9"
    accent_dim: str = "#2a7fa8"

    waveform_bg: str = "#15171a"
    waveform_peak: str = "#4fc3f7"
    waveform_rms: str = "#8fdcff"
    waveform_center: str = "#3a3f45"
    waveform_grid: str = "#282c31"
    waveform_clip: str = "#ff5f56"

    selection_fill: str = "#3daee9"
    selection_edge: str = "#7fd4ff"
    playhead: str = "#ffb300"
    cursor: str = "#d7dade"

    meter_low: str = "#4caf50"
    meter_mid: str = "#ffc107"
    meter_high: str = "#f44336"
    meter_bg: str = "#101214"

    def color(self, name: str, alpha: int | None = None) -> QColor:
        """Look up a palette entry as a :class:`QColor`, optionally with alpha."""
        value = getattr(self, name)
        qcolor = QColor(value)
        if alpha is not None:
            qcolor.setAlpha(alpha)
        return qcolor


PALETTE = Palette()


def stylesheet(palette: Palette = PALETTE) -> str:
    """Application-wide Qt stylesheet for the given palette."""
    p = palette
    return f"""
    QWidget {{
        background-color: {p.window};
        color: {p.text};
        font-size: 12px;
    }}
    QMainWindow::separator {{
        background: {p.border};
        width: 1px;
        height: 1px;
    }}
    QMenuBar, QMenu {{
        background-color: {p.surface};
        color: {p.text};
        border: none;
    }}
    QMenuBar::item:selected, QMenu::item:selected {{
        background-color: {p.accent_dim};
    }}
    QMenu {{
        border: 1px solid {p.border};
    }}
    QToolBar {{
        background-color: {p.surface};
        border-bottom: 1px solid {p.border};
        spacing: 4px;
        padding: 3px;
    }}
    QStatusBar {{
        background-color: {p.surface};
        border-top: 1px solid {p.border};
        color: {p.text_dim};
    }}
    QStatusBar::item {{ border: none; }}
    QGroupBox {{
        border: 1px solid {p.border};
        border-radius: 4px;
        margin-top: 12px;
        padding-top: 8px;
        color: {p.text_dim};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 8px;
        padding: 0 4px;
    }}
    QPushButton, QToolButton {{
        background-color: {p.surface_alt};
        border: 1px solid {p.border};
        border-radius: 3px;
        padding: 4px 10px;
        color: {p.text};
    }}
    QPushButton:hover, QToolButton:hover {{
        background-color: {p.border};
    }}
    QPushButton:pressed, QToolButton:pressed {{
        background-color: {p.accent_dim};
    }}
    QPushButton:checked, QToolButton:checked {{
        background-color: {p.accent_dim};
        border-color: {p.accent};
    }}
    QPushButton:disabled, QToolButton:disabled {{
        color: {p.text_dim};
        background-color: {p.surface};
    }}
    QLabel#TimecodeDisplay {{
        font-family: "DejaVu Sans Mono", "Menlo", monospace;
        font-size: 22px;
        color: {p.accent};
        background-color: {p.meter_bg};
        border: 1px solid {p.border};
        border-radius: 3px;
        padding: 2px 10px;
    }}
    QLabel#SecondaryTimecode {{
        font-family: "DejaVu Sans Mono", "Menlo", monospace;
        color: {p.text_dim};
    }}
    QLabel#TrackTitle {{
        font-weight: bold;
        color: {p.text};
    }}
    QSlider::groove:horizontal {{
        height: 4px;
        background: {p.border};
        border-radius: 2px;
    }}
    QSlider::handle:horizontal {{
        background: {p.accent};
        width: 12px;
        margin: -5px 0;
        border-radius: 6px;
    }}
    QSlider::sub-page:horizontal {{
        background: {p.accent_dim};
        border-radius: 2px;
    }}
    QScrollBar:horizontal {{
        background: {p.surface};
        height: 12px;
        margin: 0;
    }}
    QScrollBar::handle:horizontal {{
        background: {p.border};
        min-width: 24px;
        border-radius: 6px;
    }}
    QScrollBar::handle:horizontal:hover {{ background: {p.accent_dim}; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
    QSplitter::handle {{ background: {p.border}; }}
    """
