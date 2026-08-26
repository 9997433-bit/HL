"""Accessibility guarantees: palette contrast, keyboard reach, HiDPI scaling.

These are regression tests for promises the UI makes to users who need them —
a colour pair that quietly drifts under 4.5:1, a command that becomes
mouse-only, or a scale factor that stops reaching Qt are all invisible to the
rest of the suite.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import textwrap

import pytest
from PySide6.QtGui import QKeySequence

from audio_studio.app import (
    MAX_SCALE_FACTOR,
    MIN_SCALE_FACTOR,
    SCALE_FACTOR_ENV_VAR,
    apply_scale_factor,
    build_parser,
    scale_factor,
)
from audio_studio.core.engine import AudioEngine
from audio_studio.core.output import NullOutput
from audio_studio.ui import theme
from audio_studio.ui.main_window import MainWindow, strip_mnemonic
from audio_studio.ui.theme import (
    GRAPHIC_PAIRS,
    PALETTE,
    TEXT_PAIRS,
    WCAG_AA_NON_TEXT,
    WCAG_AA_NORMAL_TEXT,
    Palette,
    contrast_ratio,
    failing_pairs,
    relative_luminance,
    stylesheet,
)

BLACK = "#000000"
WHITE = "#ffffff"


class TestContrastMath:
    """The WCAG 2.x formulae the palette budget is measured with."""

    @pytest.mark.parametrize(
        ("color", "expected"),
        [(BLACK, 0.0), (WHITE, 1.0), ("#808080", 0.2159), ("#767676", 0.1812)],
    )
    def test_relative_luminance_matches_the_specification(
        self, color: str, expected: float
    ) -> None:
        assert relative_luminance(color) == pytest.approx(expected, abs=5e-4)

    def test_the_extremes_are_21_to_1_and_1_to_1(self) -> None:
        assert contrast_ratio(BLACK, WHITE) == pytest.approx(21.0)
        assert contrast_ratio(WHITE, WHITE) == pytest.approx(1.0)

    def test_the_ratio_does_not_depend_on_argument_order(self) -> None:
        assert contrast_ratio(BLACK, "#3daee9") == pytest.approx(
            contrast_ratio("#3daee9", BLACK)
        )

    def test_the_reference_mid_grey_sits_just_over_the_aa_floor(self) -> None:
        """#767676 on white is the canonical smallest AA-passing grey."""
        assert contrast_ratio("#767676", WHITE) == pytest.approx(4.54, abs=0.01)
        assert contrast_ratio("#777777", WHITE) < WCAG_AA_NORMAL_TEXT

    def test_a_qcolor_and_its_hex_string_measure_the_same(self) -> None:
        assert contrast_ratio(PALETTE.color("text"), PALETTE.surface) == pytest.approx(
            contrast_ratio(PALETTE.text, PALETTE.surface)
        )


class TestPaletteContrast:
    """WCAG 2.2 AA over the shipped palette (SC 1.4.3 and SC 1.4.11)."""

    @pytest.mark.parametrize(("foreground", "background"), TEXT_PAIRS)
    def test_text_pairs_clear_4_5_to_1(self, foreground: str, background: str) -> None:
        ratio = contrast_ratio(PALETTE.color(foreground), PALETTE.color(background))
        assert ratio >= WCAG_AA_NORMAL_TEXT, (
            f"{foreground} on {background} is {ratio:.2f}:1, "
            f"under the {WCAG_AA_NORMAL_TEXT}:1 minimum for normal text"
        )

    @pytest.mark.parametrize(("foreground", "background"), GRAPHIC_PAIRS)
    def test_graphic_pairs_clear_3_to_1(self, foreground: str, background: str) -> None:
        ratio = contrast_ratio(PALETTE.color(foreground), PALETTE.color(background))
        assert ratio >= WCAG_AA_NON_TEXT, (
            f"{foreground} on {background} is {ratio:.2f}:1, "
            f"under the {WCAG_AA_NON_TEXT}:1 minimum for graphics"
        )

    def test_the_shipped_palette_reports_no_failures(self) -> None:
        assert failing_pairs(PALETTE) == []

    def test_a_regressed_palette_is_caught(self) -> None:
        """The audit has to fail when a colour actually goes bad."""
        washed_out = Palette(text_dim="#5a5f64")

        failures = failing_pairs(washed_out)

        assert ("text_dim", "surface") in [pair for pair, _ratio, _floor in failures]

    @pytest.mark.parametrize(("foreground", "background"), TEXT_PAIRS + GRAPHIC_PAIRS)
    def test_every_audited_role_exists_in_the_palette(
        self, foreground: str, background: str
    ) -> None:
        names = PALETTE.names()
        assert foreground in names and background in names

    def test_the_documented_table_matches_the_measured_palette(self) -> None:
        """The ratios written into ``theme``'s docstring are not decoration."""
        documented = _documented_ratios(theme.__doc__ or "")

        assert len(documented) >= len(TEXT_PAIRS)
        for (foreground, background), claimed in documented.items():
            measured = contrast_ratio(
                PALETTE.color(foreground), PALETTE.color(background)
            )
            assert measured == pytest.approx(claimed, abs=0.01), (
                f"docstring claims {foreground}/{background} is {claimed}:1 "
                f"but the palette measures {measured:.2f}:1"
            )

    def test_the_stylesheet_only_names_palette_colours(self) -> None:
        """No hard-coded hex slipping past the contrast audit."""
        sheet = stylesheet(PALETTE)
        known = {getattr(PALETTE, name).lower() for name in PALETTE.names()}

        assert {value.lower() for value in re.findall(r"#[0-9a-fA-F]{3,8}", sheet)} <= known

    def test_the_focus_ring_is_drawn_in_the_accent_colour(self) -> None:
        """SC 2.4.11: Qt's dotted default all but vanishes on a dark fill."""
        sheet = stylesheet(PALETTE)

        assert ":focus" in sheet
        focus_rules = [line for line in sheet.splitlines() if "border: 2px" in line]
        assert focus_rules and all(PALETTE.accent in line for line in focus_rules)


def _documented_ratios(docstring: str) -> dict[tuple[str, str], float]:
    """Parse the ``| `fg` | `bg` | ratio |`` rows out of a docstring table."""
    row = re.compile(
        r"^\|\s*`(\w+)`\s*\|\s*`(\w+)`\s*\|\s*([0-9]+\.[0-9]+)\s*\|", re.MULTILINE
    )
    return {(fg, bg): float(ratio) for fg, bg, ratio in row.findall(docstring)}


@pytest.fixture()
def window(qapp) -> MainWindow:
    main = MainWindow(AudioEngine(NullOutput(realtime=False), block_size=256))
    yield main
    main.close()


def _menu_actions(window: MainWindow) -> list:
    """Every command reachable from the menu bar, each listed once."""
    seen: dict[int, object] = {}
    for menu_action in window.menuBar().actions():
        menu = menu_action.menu()
        if menu is None:
            continue
        for act in menu.actions():
            if act.isSeparator() or act.menu() is not None:
                continue
            seen.setdefault(id(act), act)
    return list(seen.values())


class TestKeyboardReach:
    """Every menu command has a key, and no key means two different things."""

    def test_no_menu_command_is_mouse_only(self, window: MainWindow) -> None:
        unbound = [
            strip_mnemonic(act.text()) for act in _menu_actions(window) if act.shortcut().isEmpty()
        ]

        assert unbound == []

    def test_no_two_commands_share_a_sequence(self, window: MainWindow) -> None:
        """Qt resolves an overloaded sequence by refusing to fire either action."""
        bound: dict[str, list[str]] = {}
        for act in _menu_actions(window):
            keys = act.shortcut().toString(QKeySequence.SequenceFormat.PortableText)
            bound.setdefault(keys, []).append(strip_mnemonic(act.text()))

        assert {keys: names for keys, names in bound.items() if len(names) > 1} == {}

    @pytest.mark.parametrize(
        ("attribute", "keys"),
        [
            ("action_open", "Ctrl+O"),
            ("action_close", "Ctrl+W"),
            ("action_quit", "Ctrl+Q"),
            ("action_save_project", "Ctrl+S"),
            ("action_export", "Ctrl+Shift+S"),
            ("action_play", "Space"),
            ("action_stop", "Esc"),
            ("action_shortcuts", "F1"),
        ],
    )
    def test_the_documented_bindings_are_the_real_ones(
        self, window: MainWindow, attribute: str, keys: str
    ) -> None:
        action = getattr(window, attribute)
        assert action.shortcut() == QKeySequence(keys)

    def test_the_dock_toggles_are_bound_too(self, window: MainWindow) -> None:
        toggles = [
            window.spectrum_dock.toggleViewAction(),
            window.effects_dock.toggleViewAction(),
            window.plugin_dock.toggleViewAction(),
            window.markers_dock.toggleViewAction(),
        ]

        assert all(not act.shortcut().isEmpty() for act in toggles)

    def test_every_menu_carries_an_alt_mnemonic(self, window: MainWindow) -> None:
        titles = [act.text() for act in window.menuBar().actions() if act.menu() is not None]

        assert titles and all("&" in title for title in titles)


class TestShortcutsDialog:
    """Help ▸ Keyboard Shortcuts, built from the live actions."""

    def test_the_table_covers_every_menu(self, window: MainWindow) -> None:
        titles = [title for title, _rows in window.shortcut_table()]

        assert {"File", "Edit", "Markers", "View", "Transport", "Help"} <= set(titles)
        assert titles[0] == "File" and titles[-1] == "Help"
        assert all(rows for _title, rows in window.shortcut_table())

    def test_the_table_carries_no_mnemonic_ampersands(self, window: MainWindow) -> None:
        for _title, rows in window.shortcut_table():
            assert all("&" not in command for command, _keys in rows)

    def test_the_html_is_a_table_of_commands_and_keys(self, window: MainWindow) -> None:
        markup = window.shortcuts_html()

        assert "<table" in markup and markup.count("<tr>") > 30
        assert "Play / Pause" in markup and "Space" in markup
        assert "Attenuate Selection" in markup and "Ctrl+Alt+A" in markup

    def test_the_html_escapes_rather_than_injects(self, window: MainWindow) -> None:
        window.action_about.setText("&About <script>")

        assert "<script>" not in window.shortcuts_html()
        assert "&lt;script&gt;" in window.shortcuts_html()

    def test_opening_it_shows_a_browser_with_the_current_bindings(
        self, window: MainWindow
    ) -> None:
        dialog = window.show_shortcuts()

        assert dialog.windowTitle() == "Keyboard Shortcuts"
        assert not dialog.isModal()  # the shortcuts must stay usable
        text = dialog.browser.toPlainText()
        assert "Keyboard Shortcuts" in text
        assert "Ctrl+O" in text
        dialog.close()

    def test_reopening_reuses_the_dialog_and_refreshes_it(self, window: MainWindow) -> None:
        first = window.show_shortcuts()
        first.close()
        window.action_analyze.setText("&Analyze Everything")

        second = window.show_shortcuts()

        assert second is first
        assert "Analyze Everything" in second.browser.toPlainText()
        second.close()


class TestScaleFactor:
    """``--scale-factor`` reaching Qt through the environment."""

    @pytest.mark.parametrize("value", ["1.0", "1.25", "1.5", "2.0"])
    def test_supported_factors_parse(self, value: str) -> None:
        assert scale_factor(value) == pytest.approx(float(value))

    @pytest.mark.parametrize("value", ["0.5", "0.99", "2.01", "3", "-1", "big", ""])
    def test_out_of_range_and_nonsense_are_refused(self, value: str) -> None:
        with pytest.raises(argparse.ArgumentTypeError):
            scale_factor(value)

    def test_the_bounds_themselves_are_accepted(self) -> None:
        assert scale_factor(str(MIN_SCALE_FACTOR)) == MIN_SCALE_FACTOR
        assert scale_factor(str(MAX_SCALE_FACTOR)) == MAX_SCALE_FACTOR

    def test_the_flag_lands_on_the_parsed_arguments(self) -> None:
        args = build_parser().parse_args(["--scale-factor", "1.5"])
        assert args.scale_factor == pytest.approx(1.5)

        assert build_parser().parse_args([]).scale_factor is None

    def test_a_bad_flag_exits_with_a_usage_error(self, capsys: pytest.CaptureFixture) -> None:
        with pytest.raises(SystemExit) as exit_info:
            build_parser().parse_args(["--scale-factor", "4"])

        assert exit_info.value.code == 2
        assert "outside 1–2" in capsys.readouterr().err

    def test_the_factor_is_published_where_qt_reads_it(self) -> None:
        environ: dict[str, str] = {}

        assert apply_scale_factor(1.5, environ) == "1.5"
        assert environ[SCALE_FACTOR_ENV_VAR] == "1.5"

    def test_an_inherited_session_scale_survives_no_flag(self) -> None:
        environ = {SCALE_FACTOR_ENV_VAR: "1.25"}

        assert apply_scale_factor(None, environ) == "1.25"
        assert environ[SCALE_FACTOR_ENV_VAR] == "1.25"

    def test_an_explicit_flag_beats_the_session(self) -> None:
        environ = {SCALE_FACTOR_ENV_VAR: "1.25"}

        assert apply_scale_factor(2.0, environ) == "2"
        assert environ[SCALE_FACTOR_ENV_VAR] == "2"

    def test_without_a_flag_or_a_session_nothing_is_invented(self) -> None:
        environ: dict[str, str] = {}

        assert apply_scale_factor(None, environ) is None
        assert environ == {}

    def test_qt_actually_scales_by_the_published_factor(self) -> None:
        """End to end, in a fresh interpreter: Qt reads the variable once, at
        ``QGuiApplication`` construction, so it cannot be checked in-process."""
        probe = textwrap.dedent(
            """
            import os
            os.environ["QT_QPA_PLATFORM"] = "offscreen"
            from audio_studio.app import apply_scale_factor, configure_high_dpi

            apply_scale_factor(1.5)
            configure_high_dpi()

            from PySide6.QtCore import Qt
            from PySide6.QtGui import QGuiApplication
            from PySide6.QtWidgets import QApplication

            app = QApplication([])
            print(app.devicePixelRatio())
            print(
                QGuiApplication.highDpiScaleFactorRoundingPolicy()
                is Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
            )
            """
        )

        result = subprocess.run(
            [sys.executable, "-c", probe],
            capture_output=True,
            text=True,
            timeout=120,
            check=True,
        )

        ratio, pass_through = result.stdout.split()
        assert float(ratio) == pytest.approx(1.5)
        assert pass_through == "True"
