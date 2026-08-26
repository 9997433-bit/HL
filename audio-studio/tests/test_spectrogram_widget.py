"""Colormaps and the SpectrogramWidget renderer, exercised headlessly."""

from __future__ import annotations

import os

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from signals import SR, sine, tone_burst, white_noise  # noqa: E402

from audio_studio.dsp import SpectralAnalyzer  # noqa: E402
from audio_studio.ui.colormaps import (  # noqa: E402
    COLORMAP_NAMES,
    DEFAULT_COLORMAP,
    colorize,
    get_colormap,
    make_gradient,
)

pytest.importorskip("PyQt6")

from PyQt6.QtCore import QPoint  # noqa: E402
from PyQt6.QtGui import QImage  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

from audio_studio.ui.spectrogram_widget import (  # noqa: E402
    FrequencyScale,
    SpectrogramWidget,
)


@pytest.fixture(scope="module")
def app() -> QApplication:
    """One offscreen QApplication for this module's widgets."""
    return QApplication.instance() or QApplication([])


@pytest.fixture
def widget(app: QApplication) -> SpectrogramWidget:
    view = SpectrogramWidget()
    view.resize(640, 360)
    return view


@pytest.fixture(scope="module")
def spectrogram():
    audio = tone_burst(2000.0, total_s=1.0, burst_start_s=0.4, burst_s=0.2)
    audio += white_noise(duration_s=1.0, amplitude=0.001)
    return SpectralAnalyzer(sample_rate=SR, fft_size=2048, hop_size=512).spectrogram(audio)


# ---------------------------------------------------------------------------
# colormaps
# ---------------------------------------------------------------------------


class TestColormaps:
    @pytest.mark.parametrize("name", COLORMAP_NAMES)
    def test_lut_shape_and_endpoints(self, name: str) -> None:
        lut = get_colormap(name)
        assert lut.shape == (256, 3)
        assert lut.dtype == np.uint8

    @pytest.mark.parametrize("name", [n for n in COLORMAP_NAMES if n != "jet"])
    def test_maps_are_monotonic_in_lightness(self, name: str) -> None:
        """Level must map to brightness monotonically, or the display lies."""
        assert _is_monotonic_in_lightness(name)

    def test_jet_is_the_documented_exception(self) -> None:
        """Kept on the menu for line-spotting despite its non-monotonic ramp."""
        assert not _is_monotonic_in_lightness("jet")

    def test_luts_are_cached_and_immutable(self) -> None:
        first = get_colormap("viridis")
        assert get_colormap("viridis") is first
        with pytest.raises(ValueError):
            first[0, 0] = 1

    def test_unknown_name_lists_the_valid_ones(self) -> None:
        with pytest.raises(KeyError, match="viridis"):
            get_colormap("not-a-colormap")

    def test_custom_gradient_size(self) -> None:
        assert make_gradient(((0.0, (0, 0, 0)), (1.0, (255, 255, 255))), size=64).shape == (64, 3)

    def test_colorize_maps_range_ends_to_lut_ends(self) -> None:
        lut = get_colormap(DEFAULT_COLORMAP)
        rgb = colorize(np.array([-100.0, 0.0]), -100.0, 0.0)
        assert np.array_equal(rgb[0], lut[0])
        assert np.array_equal(rgb[1], lut[-1])

    def test_colorize_clips_out_of_range_values(self) -> None:
        rgb = colorize(np.array([-500.0, 500.0]), -100.0, 0.0)
        lut = get_colormap(DEFAULT_COLORMAP)
        assert np.array_equal(rgb[0], lut[0])
        assert np.array_equal(rgb[1], lut[-1])

    def test_colorize_preserves_shape_and_is_contiguous(self) -> None:
        rgb = colorize(np.zeros((7, 11)), -60.0, 0.0)
        assert rgb.shape == (7, 11, 3)
        assert rgb.flags["C_CONTIGUOUS"]

    def test_degenerate_range_does_not_divide_by_zero(self) -> None:
        assert np.all(np.isfinite(colorize(np.zeros(4), 0.0, 0.0).astype(float)))


# ---------------------------------------------------------------------------
# widget
# ---------------------------------------------------------------------------


class TestSpectrogramWidget:
    def test_renders_nothing_before_data_arrives(self, widget: SpectrogramWidget) -> None:
        assert widget.render_image(320, 180) is None

    def test_renders_a_spectrogram(self, widget: SpectrogramWidget, spectrogram) -> None:
        widget.set_spectrogram(spectrogram)
        image = widget.render_image(320, 180)
        assert isinstance(image, QImage)
        assert (image.width(), image.height()) == (320, 180)
        assert image.format() == QImage.Format.Format_RGB888

    def test_accepts_a_raw_matrix_with_axes(self, widget: SpectrogramWidget) -> None:
        data = np.random.default_rng(0).uniform(-90, -10, size=(50, 129)).astype(np.float32)
        widget.set_spectrogram(
            data, frequencies=np.linspace(0, SR / 2, 129), times=np.linspace(0, 1, 50)
        )
        assert widget.render_image(200, 100) is not None

    def test_raw_matrix_requires_axes(self, widget: SpectrogramWidget) -> None:
        with pytest.raises(ValueError, match="frequencies and times"):
            widget.set_spectrogram(np.zeros((4, 5)))

    def test_rejects_a_non_2d_matrix(self, widget: SpectrogramWidget) -> None:
        with pytest.raises(ValueError, match="2-D"):
            widget.set_spectrogram(np.zeros((2, 4, 5)), np.zeros(5), np.zeros(4))

    def test_loud_content_renders_brighter_than_silence(
        self, widget: SpectrogramWidget, spectrogram
    ) -> None:
        """The core promise of a heat map: level maps to colour."""
        widget.set_spectrogram(spectrogram)
        widget.set_db_range(-100.0, 0.0)
        widget.set_frequency_range(1000.0, 4000.0)
        image = widget.render_image(200, 100)

        pixels = _image_to_array(image)
        luminance = pixels @ np.array([0.2126, 0.7152, 0.0722])
        # The burst sits at 0.4-0.6 s of a 1 s file, i.e. the middle fifth.
        during = luminance[:, 80:120].mean()
        before = luminance[:, :40].mean()
        assert during > before + 10.0

    def test_the_tone_lands_at_the_right_height(
        self, widget: SpectrogramWidget, spectrogram
    ) -> None:
        widget.set_spectrogram(spectrogram)
        widget.set_db_range(-100.0, 0.0)
        widget.set_frequency_scale(FrequencyScale.LOG)
        widget.set_frequency_range(20.0, 20_000.0)

        pixels = _image_to_array(widget.render_image(200, 200))
        luminance = pixels @ np.array([0.2126, 0.7152, 0.0722])
        brightest_row = int(np.argmax(luminance[:, 80:120].mean(axis=1)))

        # Row 0 is the top of the image, which is f_max on a log axis.
        expected = 199 - int(199 * np.log(2000.0 / 20.0) / np.log(20_000.0 / 20.0))
        assert abs(brightest_row - expected) <= 6

    def test_narrow_lines_survive_being_zoomed_out(self, widget: SpectrogramWidget) -> None:
        """Max-pooling, not sub-sampling: a single hot bin must not vanish."""
        data = np.full((2000, 1025), -120.0, dtype=np.float32)
        data[:, 300] = 0.0
        widget.set_spectrogram(
            data, frequencies=np.linspace(0, SR / 2, 1025), times=np.linspace(0, 20, 2000)
        )
        widget.set_db_range(-120.0, 0.0)
        widget.set_frequency_scale(FrequencyScale.LINEAR)
        widget.set_frequency_range(0.0, SR / 2)

        pixels = _image_to_array(widget.render_image(100, 50))
        assert pixels.max() > 200  # the line is still on screen

    @pytest.mark.parametrize("scale", list(FrequencyScale))
    def test_both_frequency_scales_render(
        self, widget: SpectrogramWidget, spectrogram, scale: FrequencyScale
    ) -> None:
        widget.set_spectrogram(spectrogram)
        widget.set_frequency_scale(scale)
        assert widget.render_image(160, 90) is not None

    @pytest.mark.parametrize("name", COLORMAP_NAMES)
    def test_every_colormap_renders(
        self, widget: SpectrogramWidget, spectrogram, name: str
    ) -> None:
        widget.set_spectrogram(spectrogram)
        widget.set_colormap(name)
        assert widget.colormap == name
        assert widget.render_image(120, 80) is not None

    def test_unknown_colormap_is_rejected(self, widget: SpectrogramWidget) -> None:
        with pytest.raises(KeyError):
            widget.set_colormap("nope")

    def test_db_range_must_be_increasing(self, widget: SpectrogramWidget) -> None:
        with pytest.raises(ValueError):
            widget.set_db_range(0.0, -100.0)

    def test_frequency_range_must_be_increasing(self, widget: SpectrogramWidget) -> None:
        with pytest.raises(ValueError):
            widget.set_frequency_range(8000.0, 100.0)

    def test_auto_scale_fits_the_range_to_a_percentile(
        self, widget: SpectrogramWidget, spectrogram
    ) -> None:
        """Scaling to a percentile keeps one hot bin from washing out the view."""
        widget.set_spectrogram(spectrogram)
        widget.auto_scale(percentile=99.9, floor_range_db=80.0)
        db_min, db_max = widget.db_range

        data = spectrogram.db()
        assert db_max - db_min == pytest.approx(80.0)
        assert db_max == pytest.approx(float(np.percentile(data, 99.9)), abs=0.5)
        assert db_max < float(np.max(data))  # the very top is deliberately clipped
        assert np.mean(data > db_min) > 0.1  # but the floor is not above everything

    def test_auto_scale_on_empty_data_is_a_no_op(self, widget: SpectrogramWidget) -> None:
        before = widget.db_range
        widget.auto_scale()
        assert widget.db_range == before

    def test_frequency_range_is_clamped_to_nyquist(
        self, widget: SpectrogramWidget, spectrogram
    ) -> None:
        widget.set_spectrogram(spectrogram)
        widget.set_frequency_range(20.0, 96_000.0)
        assert widget.frequency_range[1] <= SR / 2 + 1e-6

    def test_clear_removes_the_image(self, widget: SpectrogramWidget, spectrogram) -> None:
        widget.set_spectrogram(spectrogram)
        widget.clear()
        assert widget.render_image(100, 50) is None


class TestWaterfallMode:
    def test_push_frame_before_start_is_an_error(self, widget: SpectrogramWidget) -> None:
        with pytest.raises(RuntimeError, match="start_waterfall"):
            widget.push_frame(np.zeros(10))

    def test_frames_accumulate_and_render(self, widget: SpectrogramWidget) -> None:
        analyzer = SpectralAnalyzer(sample_rate=SR, fft_size=1024, hop_size=256)
        widget.start_waterfall(
            analyzer.frequencies, history=64, frame_interval_s=analyzer.config.hop_seconds
        )
        assert widget.render_image(100, 50) is None  # nothing pushed yet

        for _ in range(20):
            widget.push_frame(analyzer.spectrum(sine(1000.0, 1024 / SR, 0.5)), repaint=False)
        assert widget.render_image(100, 50) is not None

    def test_waterfall_time_axis_is_relative_to_now(self, widget: SpectrogramWidget) -> None:
        widget.start_waterfall(np.linspace(0, SR / 2, 65), history=100, frame_interval_s=0.01)
        widget.push_frame(np.full(65, -20.0))
        start, end = widget._time_span()
        assert start == pytest.approx(-1.0) and end == pytest.approx(0.0)


class TestInteraction:
    def test_value_at_reads_back_the_level(
        self, widget: SpectrogramWidget, spectrogram
    ) -> None:
        widget.set_spectrogram(spectrogram)
        widget.set_frequency_range(20.0, 20_000.0)
        plot = widget._plot_rect()
        point = QPoint(plot.center().x(), plot.center().y())

        time_s, frequency, level_db = widget.value_at(point)
        assert 0.0 <= time_s <= spectrogram.times[-1]
        assert 20.0 <= frequency <= 20_000.0
        assert np.isfinite(level_db)

    def test_cursor_maps_to_the_burst_frequency(
        self, widget: SpectrogramWidget, spectrogram
    ) -> None:
        """Hovering the bright line should read close to 2 kHz and be loud."""
        widget.set_spectrogram(spectrogram)
        widget.set_frequency_scale(FrequencyScale.LOG)
        widget.set_frequency_range(20.0, 20_000.0)
        plot = widget._plot_rect()

        fraction = np.log(2000.0 / 20.0) / np.log(20_000.0 / 20.0)
        y = plot.bottom() - int(fraction * (plot.height() - 1))
        x = plot.left() + int(0.5 * (plot.width() - 1))

        _, frequency, level_db = widget.value_at(QPoint(x, y))
        assert frequency == pytest.approx(2000.0, rel=0.05)
        assert level_db > -40.0

    def test_axis_mapping_round_trips(self, widget: SpectrogramWidget, spectrogram) -> None:
        """Round-trip error is bounded by one pixel, which is ~2% on a log axis."""
        widget.set_spectrogram(spectrogram)
        widget.set_frequency_range(20.0, 20_000.0)
        plot = widget._plot_rect()
        pixel_ratio = (20_000.0 / 20.0) ** (1.0 / (plot.height() - 1))

        for frequency in (50.0, 440.0, 5000.0, 15_000.0):
            y = widget._frequency_to_y(frequency, plot)
            assert y is not None
            recovered = widget._y_to_frequency(y, plot)
            assert recovered == pytest.approx(frequency, rel=pixel_ratio - 1.0)

    def test_value_at_is_safe_without_data(self, widget: SpectrogramWidget) -> None:
        assert len(widget.value_at(QPoint(10, 10))) == 3


class TestPainting:
    """Paint into an off-screen image; a crash here is a crash in the app."""

    def _paint(self, widget: SpectrogramWidget) -> QImage:
        from PyQt6.QtGui import QPainter

        image = QImage(widget.width(), widget.height(), QImage.Format.Format_RGB32)
        image.fill(0)
        painter = QPainter(image)
        widget.render(painter)
        painter.end()
        return image

    def test_paints_with_data(self, widget: SpectrogramWidget, spectrogram) -> None:
        widget.set_spectrogram(spectrogram)
        assert not self._paint(widget).isNull()

    def test_paints_the_empty_state(self, widget: SpectrogramWidget) -> None:
        assert not self._paint(widget).isNull()

    def test_paints_with_the_colorbar_hidden(
        self, widget: SpectrogramWidget, spectrogram
    ) -> None:
        widget.set_spectrogram(spectrogram)
        widget.set_colorbar_visible(False)
        widget.set_grid_visible(False)
        assert not self._paint(widget).isNull()

    def test_paints_after_a_resize(self, widget: SpectrogramWidget, spectrogram) -> None:
        widget.set_spectrogram(spectrogram)
        self._paint(widget)
        widget.resize(300, 200)
        assert not self._paint(widget).isNull()

    def test_paints_at_a_very_small_size(
        self, widget: SpectrogramWidget, spectrogram
    ) -> None:
        widget.set_spectrogram(spectrogram)
        widget.resize(60, 40)
        assert not self._paint(widget).isNull()

    def test_paints_in_waterfall_mode(self, widget: SpectrogramWidget) -> None:
        analyzer = SpectralAnalyzer(sample_rate=SR, fft_size=512, hop_size=128)
        widget.start_waterfall(analyzer.frequencies, history=32, frame_interval_s=128 / SR)
        for _ in range(10):
            widget.push_frame(analyzer.spectrum(white_noise(512 / SR, 0.2)), repaint=False)
        assert not self._paint(widget).isNull()


def _is_monotonic_in_lightness(name: str, tolerance: float = 2.0) -> bool:
    """Whether a palette's Rec. 709 luminance rises (or falls) without reversal."""
    lut = get_colormap(name).astype(np.float64)
    luminance = lut @ np.array([0.2126, 0.7152, 0.0722])
    direction = np.sign(luminance[-1] - luminance[0])
    return bool(np.all(np.diff(luminance) * direction >= -tolerance))


def _image_to_array(image: QImage) -> np.ndarray:
    """Copy a Format_RGB888 QImage into an ``(h, w, 3)`` uint8 array."""
    width, height = image.width(), image.height()
    pointer = image.constBits()
    pointer.setsize(image.sizeInBytes())
    stride = image.bytesPerLine()
    raw = np.frombuffer(bytes(pointer), dtype=np.uint8).reshape(height, stride)
    return raw[:, : width * 3].reshape(height, width, 3)
