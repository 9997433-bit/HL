"""Dark studio palette and stylesheet.

Colours are kept in one place so the waveform renderer, the meters and the
widget chrome stay visually consistent, and so a light theme can later be
added by swapping a single :class:`Palette` instance.

Contrast budget (WCAG 2.2 level AA)
-----------------------------------

Every pair below is measured with :func:`contrast_ratio`, which implements the
WCAG 2.x relative-luminance formula, and is asserted in
``tests/test_accessibility.py`` — the numbers in this docstring are checked
against the live palette, so they cannot drift away from the colours.

Pairs that carry **normal-size text** (12 px body type) must reach 4.5:1,
SC 1.4.3 *Contrast (Minimum)*:

| foreground   | background    | ratio  | where it appears                     |
|--------------|---------------|--------|--------------------------------------|
| `text`       | `window`      | 12.03  | body text on the window canvas       |
| `text`       | `surface`     | 10.84  | menus, toolbar, dock titles          |
| `text`       | `surface_alt` |  9.62  | buttons, combo boxes                 |
| `text`       | `border`      |  7.57  | hovered button fill                  |
| `text`       | `accent_dim`  |  4.99  | pressed and checked buttons          |
| `window`     | `accent`      |  6.77  | text on a selected menu or list row  |
| `text`       | `meter_bg`    | 13.38  | readouts over the meter well         |
| `text_dim`   | `window`      |  6.46  | group-box titles, check-box labels   |
| `text_dim`   | `surface`     |  5.82  | status bar, dock titles              |
| `text_dim`   | `surface_alt` |  5.16  | disabled control labels              |
| `text_dim`   | `waveform_bg` |  6.87  | time-ruler and lane annotations      |
| `text_dim`   | `meter_bg`    |  7.18  | meter scale legend                   |
| `accent`     | `meter_bg`    |  7.54  | the 22 px timecode readout           |

Pairs that carry **graphics and control boundaries** must reach 3:1,
SC 1.4.11 *Non-text Contrast*:

| foreground       | background    | ratio | where it appears                   |
|------------------|---------------|-------|------------------------------------|
| `accent`         | `window`      |  6.77 | keyboard focus ring                |
| `accent`         | `surface`     |  6.11 | keyboard focus ring                |
| `accent`         | `surface_alt` |  5.41 | focus ring, checked-state outline  |
| `control_border` | `window`      |  3.94 | button and combo-box outline       |
| `control_border` | `surface`     |  3.55 | outline against toolbar/menu fill  |
| `control_border` | `surface_alt` |  3.15 | outline against its own fill       |
| `waveform_peak`  | `waveform_bg` |  8.96 | peak envelope                      |
| `waveform_rms`   | `waveform_bg` | 11.84 | RMS body                           |
| `selection_edge` | `waveform_bg` | 10.92 | selection boundary                 |
| `playhead`       | `waveform_bg` | 10.01 | playhead                           |
| `cursor`         | `waveform_bg` | 12.80 | edit cursor                        |
| `marker`         | `waveform_bg` |  9.61 | marker flags                       |
| `region`         | `waveform_bg` |  5.98 | region spans                       |
| `waveform_clip`  | `waveform_bg` |  6.01 | clipping indicators                |
| `meter_low`      | `meter_bg`    |  6.75 | meter bar, safe zone               |
| `meter_mid`      | `meter_bg`    | 11.52 | meter bar, caution zone            |
| `meter_high`     | `meter_bg`    |  5.10 | meter bar, over zone               |

Two consequences of that budget are visible in the stylesheet. A selected menu
or list row is filled with full-strength ``accent`` and inverts its label to
the near-black ``window`` colour, because the ordinary ``text`` grey over
``accent`` is only 1.78:1; the fill that stays *under* unchanged ``text`` —
a pressed or checked button — is the darker ``accent_dim`` instead. And
control outlines use ``control_border`` rather than the ``border`` separator
colour: a hairline dividing two chrome panels is decorative and may stay
quiet, but the outline that says "this is a button" is a component boundary
and has to be seen.

Known deviation: the *fills* of the chrome layers (``window`` → ``surface`` →
``surface_alt``) differ by about 1.2:1. Depth is conveyed by luminance
ordering, not contrast, which is why controls are given an explicit outline
and a focus ring rather than being identified by their fill alone. Colour is
never the only channel for state: recording, clipping and bypass all carry a
glyph or a text label beside the colour (SC 1.4.1).
"""

from __future__ import annotations

from dataclasses import dataclass, fields

from PySide6.QtGui import QColor

#: WCAG 2.2 SC 1.4.3 minimum for text below 18 pt / 14 pt bold.
WCAG_AA_NORMAL_TEXT: float = 4.5

#: WCAG 2.2 SC 1.4.3 minimum for large text (≥ 18 pt, or 14 pt bold).
WCAG_AA_LARGE_TEXT: float = 3.0

#: WCAG 2.2 SC 1.4.11 minimum for graphics and control boundaries.
WCAG_AA_NON_TEXT: float = 3.0


@dataclass(frozen=True, slots=True)
class Palette:
    """Named colours used across the application."""

    window: str = "#1b1d21"
    surface: str = "#232629"
    surface_alt: str = "#2b2f33"
    #: Hairline between chrome panels; decorative, not a component boundary.
    border: str = "#3a3f45"
    #: Outline of an interactive control — held at 3:1 against every fill it
    #: is drawn over, so a button is identifiable without relying on colour.
    control_border: str = "#747b83"
    text: str = "#d7dade"
    text_dim: str = "#9aa1a8"
    accent: str = "#3daee9"
    #: Selection fill *behind* normal text, so it is dark enough for 4.5:1
    #: against :attr:`text` rather than as bright as :attr:`accent`.
    accent_dim: str = "#1f5f7f"

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
    marker: str = "#9ccc65"
    region: str = "#ab7df6"

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

    def names(self) -> tuple[str, ...]:
        """Every colour role in declaration order."""
        return tuple(field.name for field in fields(self))


PALETTE = Palette()

#: Foreground/background roles that carry normal-size text; 4.5:1 (SC 1.4.3).
TEXT_PAIRS: tuple[tuple[str, str], ...] = (
    ("text", "window"),
    ("text", "surface"),
    ("text", "surface_alt"),
    ("text", "border"),
    ("text", "accent_dim"),
    ("text", "meter_bg"),
    ("window", "accent"),
    ("text_dim", "window"),
    ("text_dim", "surface"),
    ("text_dim", "surface_alt"),
    ("text_dim", "waveform_bg"),
    ("text_dim", "meter_bg"),
    ("accent", "meter_bg"),
)

#: Ink and control boundaries that must stay legible; 3:1 (SC 1.4.11).
GRAPHIC_PAIRS: tuple[tuple[str, str], ...] = (
    ("accent", "window"),
    ("accent", "surface"),
    ("accent", "surface_alt"),
    ("control_border", "window"),
    ("control_border", "surface"),
    ("control_border", "surface_alt"),
    ("waveform_peak", "waveform_bg"),
    ("waveform_rms", "waveform_bg"),
    ("selection_edge", "waveform_bg"),
    ("playhead", "waveform_bg"),
    ("cursor", "waveform_bg"),
    ("marker", "waveform_bg"),
    ("region", "waveform_bg"),
    ("waveform_clip", "waveform_bg"),
    ("meter_low", "meter_bg"),
    ("meter_mid", "meter_bg"),
    ("meter_high", "meter_bg"),
)


def relative_luminance(color: QColor | str) -> float:
    """WCAG 2.x relative luminance of ``color``, in ``[0, 1]``.

    The sRGB channels are linearised with the piecewise transfer function from
    the specification — *not* a plain 2.2 gamma — because the ratios below are
    compared against thresholds defined in those exact terms.
    """
    qcolor = color if isinstance(color, QColor) else QColor(color)
    channels = []
    for raw in (qcolor.red(), qcolor.green(), qcolor.blue()):
        value = raw / 255.0
        channels.append(value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4)
    red, green, blue = channels
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast_ratio(first: QColor | str, second: QColor | str) -> float:
    """Contrast ratio between two opaque colours: 1.0 (identical) to 21.0.

    Symmetric in its arguments, as the WCAG definition is — the lighter colour
    is always the numerator.
    """
    a, b = relative_luminance(first), relative_luminance(second)
    lighter, darker = max(a, b), min(a, b)
    return (lighter + 0.05) / (darker + 0.05)


def contrast_report(
    palette: Palette = PALETTE,
    pairs: tuple[tuple[str, str], ...] = TEXT_PAIRS + GRAPHIC_PAIRS,
) -> dict[tuple[str, str], float]:
    """Measure ``pairs`` of colour roles against ``palette``."""
    return {
        (fg, bg): contrast_ratio(palette.color(fg), palette.color(bg)) for fg, bg in pairs
    }


def failing_pairs(
    palette: Palette = PALETTE,
) -> list[tuple[tuple[str, str], float, float]]:
    """Pairs of ``palette`` below their WCAG AA floor, as (pair, ratio, floor).

    Empty for the shipped palette; useful when editing colours or adding a
    second theme, and the assertion the accessibility tests are built on.
    """
    failures = []
    for pairs, floor in ((TEXT_PAIRS, WCAG_AA_NORMAL_TEXT), (GRAPHIC_PAIRS, WCAG_AA_NON_TEXT)):
        for pair, ratio in contrast_report(palette, pairs).items():
            if ratio < floor:
                failures.append((pair, ratio, floor))
    return failures


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
        background-color: {p.accent};
        color: {p.window};
    }}
    QMenu::item:disabled {{ color: {p.text_dim}; }}
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
        border: 1px solid {p.control_border};
        border-radius: 3px;
        padding: 4px 10px;
        color: {p.text};
    }}
    QPushButton:hover, QToolButton:hover {{
        background-color: {p.border};
    }}
    QPushButton:pressed, QToolButton:pressed {{
        background-color: {p.accent_dim};
        border-color: {p.accent};
    }}
    QPushButton:checked, QToolButton:checked {{
        background-color: {p.accent_dim};
        border-color: {p.accent};
    }}
    QPushButton:disabled, QToolButton:disabled {{
        color: {p.text_dim};
        background-color: {p.surface};
    }}
    /* Keyboard focus is drawn as a two-pixel accent ring rather than Qt's
       default dotted outline, which all but vanishes on a dark fill
       (WCAG 2.2 SC 2.4.11 / 2.4.13). */
    QPushButton:focus, QToolButton:focus, QComboBox:focus, QSpinBox:focus,
    QLineEdit:focus, QAbstractItemView:focus {{
        border: 2px solid {p.accent};
    }}
    QCheckBox::indicator:focus, QSlider::handle:horizontal:focus {{
        border: 2px solid {p.accent};
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
    QDockWidget {{
        color: {p.text_dim};
        titlebar-close-icon: none;
    }}
    QDockWidget::title {{
        background: {p.surface};
        border-bottom: 1px solid {p.border};
        padding: 4px 8px;
        text-align: left;
    }}
    QWidget#SpectrumControls {{
        background-color: {p.surface};
        border-bottom: 1px solid {p.border};
    }}
    QComboBox {{
        background-color: {p.surface_alt};
        border: 1px solid {p.control_border};
        border-radius: 3px;
        padding: 2px 6px;
        color: {p.text};
    }}
    QComboBox:hover {{ border-color: {p.accent}; }}
    QComboBox QAbstractItemView {{
        background-color: {p.surface};
        selection-background-color: {p.accent};
        selection-color: {p.window};
        border: 1px solid {p.control_border};
    }}
    QCheckBox {{ color: {p.text_dim}; }}
    QCheckBox::indicator {{
        width: 12px;
        height: 12px;
        border: 1px solid {p.control_border};
        border-radius: 2px;
        background: {p.surface_alt};
    }}
    QCheckBox::indicator:checked {{
        background: {p.accent};
        border-color: {p.accent};
    }}
    QScrollBar:horizontal {{
        background: {p.surface};
        height: 12px;
        margin: 0;
    }}
    QScrollBar::handle:horizontal {{
        background: {p.control_border};
        min-width: 24px;
        border-radius: 6px;
    }}
    QScrollBar::handle:horizontal:hover {{ background: {p.accent}; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
    QSplitter::handle {{ background: {p.border}; }}
    QTextBrowser {{
        background-color: {p.surface};
        border: 1px solid {p.control_border};
        color: {p.text};
        selection-background-color: {p.accent};
        selection-color: {p.window};
    }}
    """
