"""Spectral selection editing: masking a band out of a signal and undoing it.

Everything here is measured on a *narrow band removed from a two-tone signal*,
because that is the one case where the answer is known exactly: the tone inside
the rectangle should vanish, the tone outside it should come back at the
amplitude it went in with, and nothing outside the selected time range should
change by a single bit.

Tone levels are read by projection onto a complex phasor rather than out of an
FFT bin, so the number under test is the amplitude of that frequency in the
signal and not an artefact of the analysis window used to look for it.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from audio_studio.core.edit_session import (
    SPECTRAL_ATTENUATION_DB,
    EditError,
    EditSession,
    SpectralEditCommand,
)
from audio_studio.core.types import SAMPLE_DTYPE, TimeRange
from audio_studio.dsp.spectral_edit import (
    SpectralBand,
    apply_spectral_gain,
    attenuate_band,
    band_gain,
    remove_band,
)

SR = 48_000

#: The tone that gets removed, and the one that has to survive it.
NOTCHED_HZ = 5_000.0
KEPT_HZ = 1_000.0

#: A band 400 Hz wide around the notched tone — about 17 FFT bins at the
#: default 2048-point transform, so the tone sits well clear of both edges.
BAND = SpectralBand(NOTCHED_HZ - 200.0, NOTCHED_HZ + 200.0)

#: Samples ignored at each end of a measurement. A masked frame overlaps its
#: neighbours by three quarters of a window, so the notch takes about one
#: window to reach full depth at a boundary.
EDGE = 4_096


def two_tone(duration_s: float = 1.0, amplitude: float = 0.4) -> np.ndarray:
    """Mono ``KEPT_HZ + NOTCHED_HZ`` at equal amplitude."""
    t = np.arange(int(duration_s * SR)) / SR
    tones = np.sin(2 * np.pi * KEPT_HZ * t) + np.sin(2 * np.pi * NOTCHED_HZ * t)
    return (amplitude * tones).astype(SAMPLE_DTYPE)


def tone_level(signal: np.ndarray, frequency: float, sample_rate: int = SR) -> float:
    """Amplitude of one frequency in ``signal``, by projection onto its phasor."""
    body = np.asarray(signal, dtype=np.float64)
    phasor = np.exp(-2j * np.pi * frequency * np.arange(body.size) / sample_rate)
    return float(2.0 * abs(np.vdot(phasor, body)) / body.size)


def interior(signal: np.ndarray) -> np.ndarray:
    """The part of a processed buffer that is clear of the analysis edges."""
    return np.asarray(signal)[EDGE:-EDGE]


class TestSpectralBand:
    def test_edges_are_ordered_however_they_were_dragged(self) -> None:
        assert SpectralBand(900.0, 300.0) == SpectralBand(300.0, 900.0)

    def test_a_collapsed_band_is_empty_rather_than_invalid(self) -> None:
        assert SpectralBand(440.0, 440.0).is_empty
        assert not BAND.is_empty

    def test_negative_and_infinite_edges_are_refused(self) -> None:
        with pytest.raises(ValueError, match="non-negative"):
            SpectralBand(-10.0, 100.0)
        with pytest.raises(ValueError, match="finite"):
            SpectralBand(100.0, math.inf)

    def test_clamping_pulls_the_band_under_nyquist(self) -> None:
        clamped = SpectralBand(18_000.0, 40_000.0).clamped(24_000.0)
        assert clamped == SpectralBand(18_000.0, 24_000.0)

    def test_the_centre_is_geometric_so_it_reads_as_a_pitch(self) -> None:
        assert SpectralBand(1_000.0, 4_000.0).center_hz == pytest.approx(2_000.0)


class TestBandGain:
    """The per-bin multipliers a mask is made of."""

    frequencies = np.arange(0.0, 24_000.0, 100.0)

    def test_a_hard_mask_gains_the_band_and_nothing_else(self) -> None:
        mask = band_gain(self.frequencies, SpectralBand(1_000.0, 2_000.0), 0.0)

        inside = (self.frequencies >= 1_000.0) & (self.frequencies <= 2_000.0)
        assert np.all(mask[inside] == 0.0)
        assert np.all(mask[~inside] == 1.0)

    def test_the_skirt_sits_outside_the_requested_band(self) -> None:
        """The band asked for is always attenuated in full; the taper is extra."""
        band = SpectralBand(1_000.0, 2_000.0)
        mask = band_gain(self.frequencies, band, 0.0, transition_hz=300.0)

        inside = (self.frequencies >= band.low_hz) & (self.frequencies <= band.high_hz)
        assert np.all(mask[inside] == pytest.approx(0.0))
        assert mask[self.frequencies == 900.0] > 0.0  # part-way down the skirt
        assert mask[self.frequencies == 700.0] == pytest.approx(1.0)
        assert np.all((mask >= 0.0) & (mask <= 1.0))

    def test_an_empty_band_leaves_every_bin_alone(self) -> None:
        mask = band_gain(self.frequencies, SpectralBand(500.0, 500.0), 0.0)
        assert np.all(mask == 1.0)


class TestApplySpectralGain:
    def test_removing_a_narrow_band_takes_the_tone_inside_it(self) -> None:
        cleaned = interior(remove_band(two_tone(), SR, BAND))

        assert tone_level(cleaned, NOTCHED_HZ) < 1e-3  # better than -60 dB
        assert tone_level(cleaned, KEPT_HZ) == pytest.approx(0.4, rel=0.01)

    def test_attenuation_is_the_gain_that_was_asked_for(self) -> None:
        ducked = interior(attenuate_band(two_tone(), SR, BAND, -12.0))

        assert tone_level(ducked, NOTCHED_HZ) == pytest.approx(0.4 * 0.25, rel=0.02)
        assert tone_level(ducked, KEPT_HZ) == pytest.approx(0.4, rel=0.01)

    def test_unity_gain_is_a_no_op_rather_than_a_round_trip(self) -> None:
        signal = two_tone()
        assert np.array_equal(apply_spectral_gain(signal, SR, BAND, 0.0), signal)

    def test_an_empty_band_changes_nothing(self) -> None:
        signal = two_tone()
        untouched = remove_band(signal, SR, SpectralBand(3_000.0, 3_000.0))
        assert np.array_equal(untouched, signal)

    def test_a_band_the_signal_does_not_reach_leaves_it_intact(self) -> None:
        """Resynthesis of an unmasked spectrum has to give the input back."""
        signal = two_tone()
        quiet_band = SpectralBand(15_000.0, 16_000.0)

        assert interior(remove_band(signal, SR, quiet_band)) == pytest.approx(
            interior(signal), abs=1e-5
        )

    def test_interleaved_stereo_comes_back_interleaved(self) -> None:
        mono = two_tone()
        stereo = np.stack([mono, 0.5 * mono], axis=1)

        cleaned = remove_band(stereo, SR, BAND, channels_last=True)

        assert cleaned.shape == stereo.shape
        for channel, amplitude in enumerate((0.4, 0.2)):
            body = interior(cleaned[:, channel])
            assert tone_level(body, NOTCHED_HZ) < 1e-3
            assert tone_level(body, KEPT_HZ) == pytest.approx(amplitude, rel=0.01)

    def test_planar_stereo_keeps_its_layout_too(self) -> None:
        mono = two_tone()
        planar = np.stack([mono, mono])

        cleaned = remove_band(planar, SR, BAND, channels_last=False)

        assert cleaned.shape == planar.shape
        assert tone_level(interior(cleaned[0]), NOTCHED_HZ) < 1e-3

    def test_a_selection_shorter_than_the_transform_still_reconstructs(self) -> None:
        """A 10 ms rectangle is a legitimate thing to drag; it must not blow up."""
        short = two_tone(duration_s=0.01)

        cleaned = remove_band(short, SR, BAND)

        assert cleaned.shape == short.shape
        assert np.all(np.isfinite(cleaned))
        assert np.max(np.abs(cleaned)) < 1.0

    def test_an_empty_buffer_is_handled_as_an_empty_buffer(self) -> None:
        assert remove_band(np.zeros(0, dtype=SAMPLE_DTYPE), SR, BAND).size == 0


class TestSpectralEditCommand:
    """The undoable edit that carries a mask onto a document."""

    @pytest.fixture()
    def session(self) -> EditSession:
        mono = two_tone()
        return EditSession.from_array(np.stack([mono, mono], axis=1), SR)

    def test_removing_a_band_edits_the_document_in_place(
        self, session: EditSession
    ) -> None:
        frames = session.n_frames

        session.remove_band(TimeRange(0, frames), BAND.low_hz, BAND.high_hz)

        assert session.n_frames == frames  # a spectral edit is not a cut
        body = interior(session.read(0, frames)[:, 0])
        assert tone_level(body, NOTCHED_HZ) < 1e-3
        assert tone_level(body, KEPT_HZ) == pytest.approx(0.4, rel=0.01)

    def test_undo_restores_the_original_samples_exactly(
        self, session: EditSession
    ) -> None:
        original = session.read(0, session.n_frames)

        session.remove_band(TimeRange(0, session.n_frames), BAND.low_hz, BAND.high_hz)
        assert not np.array_equal(session.read(0, session.n_frames), original)

        assert session.undo()
        assert np.array_equal(session.read(0, session.n_frames), original)

        assert session.redo()
        assert not np.array_equal(session.read(0, session.n_frames), original)

    def test_only_the_selected_time_range_is_touched(self, session: EditSession) -> None:
        original = session.read(0, session.n_frames)
        half = session.n_frames // 2

        session.remove_band(TimeRange(0, half), BAND.low_hz, BAND.high_hz)

        edited = session.read(0, session.n_frames)
        assert np.array_equal(edited[half:], original[half:])
        assert tone_level(edited[EDGE : half - EDGE, 0], NOTCHED_HZ) < 1e-3

    def test_attenuation_uses_the_documented_default(self, session: EditSession) -> None:
        session.attenuate_band(TimeRange(0, session.n_frames), BAND.low_hz, BAND.high_hz)

        body = interior(session.read(0, session.n_frames)[:, 0])
        expected = 0.4 * 10.0 ** (SPECTRAL_ATTENUATION_DB / 20.0)
        assert tone_level(body, NOTCHED_HZ) == pytest.approx(expected, rel=0.02)

    def test_the_label_says_what_the_edit_did(self, session: EditSession) -> None:
        session.remove_band(TimeRange(0, 10_000), 4_800.0, 5_200.0)
        assert session.undo_stack.undo_label == "Remove 4800–5200 Hz"

        session.attenuate_band(TimeRange(0, 10_000), 4_800.0, 5_200.0)
        assert session.undo_stack.undo_label == "Attenuate 4800–5200 Hz"

    def test_an_empty_band_or_range_is_refused(self, session: EditSession) -> None:
        with pytest.raises(EditError, match="empty band"):
            session.execute(SpectralEditCommand(TimeRange(0, 1_000), 500.0, 500.0))
        with pytest.raises(EditError, match="empty selection"):
            session.remove_band(TimeRange(500, 500), 400.0, 800.0)

    def test_the_command_reports_what_it_was_built_with(self) -> None:
        command = SpectralEditCommand(TimeRange(0, 100), 300.0, 900.0, -math.inf)

        assert command.band == SpectralBand(300.0, 900.0)
        assert command.removes
        assert not SpectralEditCommand(TimeRange(0, 100), 300.0, 900.0, -6.0).removes


@pytest.mark.usefixtures("qapp")
class TestSpectralSelectionUI:
    """Dragging the rectangle that the commands above are driven from."""

    offset_s = 0.5

    @pytest.fixture()
    def panel(self):
        from audio_studio.ui.spectrum_panel import SpectrumPanel

        view = SpectrumPanel()
        view.resize(900, 320)
        mono = two_tone()
        view.analyze(np.stack([mono, mono], axis=1), SR, offset_s=self.offset_s)
        return view

    @staticmethod
    def drag(widget, first, second) -> None:
        """Press, move and release the left button over ``widget``."""
        from PySide6.QtCore import QPointF, Qt
        from PySide6.QtGui import QMouseEvent

        def event(kind, point, button, buttons):
            return QMouseEvent(
                kind,
                QPointF(point),
                QPointF(point),
                button,
                buttons,
                Qt.KeyboardModifier.NoModifier,
            )

        left, none = Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton
        widget.mousePressEvent(event(QMouseEvent.Type.MouseButtonPress, first, left, left))
        widget.mouseMoveEvent(event(QMouseEvent.Type.MouseMove, second, none, left))
        widget.mouseReleaseEvent(
            event(QMouseEvent.Type.MouseButtonRelease, second, left, none)
        )

    @staticmethod
    def corners(widget):
        """Two points well inside the plot, on different rows and columns."""
        from PySide6.QtCore import QPoint

        plot = widget._plot_rect()  # noqa: SLF001 - the drag needs plot coordinates
        return (
            QPoint(plot.left() + plot.width() // 4, plot.top() + plot.height() // 4),
            QPoint(plot.left() + plot.width() // 2, plot.top() + plot.height() // 2),
        )

    def test_a_drag_reports_a_range_in_document_frames_and_a_band_in_hertz(
        self, panel
    ) -> None:
        reported: list[tuple] = []
        panel.selectionChanged.connect(lambda *args: reported.append(args))
        first, second = self.corners(panel.spectrogram)

        self.drag(panel.spectrogram, first, second)

        assert len(reported) == 1
        rng, low_hz, high_hz = reported[0]
        assert isinstance(rng, TimeRange)
        # The analysis covered a selection, so its offset has to come back.
        start, end = rng.to_seconds(SR)
        assert self.offset_s < start < end < self.offset_s + 1.0
        assert 0.0 < low_hz < high_hz <= SR / 2
        assert panel.selection.time == rng

    def test_the_band_maps_to_where_the_pointer_was(self, panel) -> None:
        """A box dragged across the middle of a log axis lands mid-spectrum."""
        first, second = self.corners(panel.spectrogram)

        self.drag(panel.spectrogram, first, second)
        region = panel.spectrogram.region

        assert region is not None
        widget = panel.spectrogram
        for point, frequency in ((first, region.high_hz), (second, region.low_hz)):
            _, under_cursor, _ = widget.value_at(point)
            assert under_cursor == pytest.approx(frequency, rel=0.02)

    def test_the_action_buttons_wake_up_with_a_selection(self, panel) -> None:
        assert not panel.attenuate_button.isEnabled()
        assert not panel.delete_button.isEnabled()

        self.drag(panel.spectrogram, *self.corners(panel.spectrogram))

        assert panel.attenuate_button.isEnabled()
        assert panel.delete_button.isEnabled()
        assert "Hz" in panel.selection_label.text()

    def test_a_click_seeks_instead_of_selecting(self, panel) -> None:
        from PySide6.QtCore import QPoint

        seeks: list[float] = []
        panel.seekRequested.connect(seeks.append)
        first, _ = self.corners(panel.spectrogram)

        self.drag(panel.spectrogram, first, QPoint(first.x() + 1, first.y() + 1))

        assert panel.selection is None
        assert seeks and seeks[0] > self.offset_s

    def test_re_analysing_drops_a_selection_that_no_longer_addresses_anything(
        self, panel
    ) -> None:
        self.drag(panel.spectrogram, *self.corners(panel.spectrogram))
        assert panel.selection is not None

        mono = two_tone()
        panel.analyze(np.stack([mono, mono], axis=1), SR, offset_s=0.0)

        assert panel.selection is None
        assert panel.spectrogram.region is None

    def test_the_selection_survives_a_repaint(self, panel) -> None:
        from PySide6.QtGui import QPixmap

        self.drag(panel.spectrogram, *self.corners(panel.spectrogram))

        target = QPixmap(panel.spectrogram.size())
        panel.spectrogram.render(target)

        assert not target.isNull()
        assert panel.selection is not None
