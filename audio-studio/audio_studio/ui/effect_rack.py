"""Effect rack panel: the controls for the chain inserted in the render path.

The rack drives a live :class:`~audio_studio.dsp.effects.base.EffectChain`. Every
control writes straight into the effect objects the device thread is already
reading, so a move is audible on the next block — there is no apply step and
nothing is written back to the clip. That is the point of a preview: the rack
is a monitoring insert until the user renders it.

Two controls sit above the individual effects, matching a mixer's insert slot:
**Bypass** takes the whole rack out of the path, and **Mix** crossfades the
processed signal against the untouched one.

The restoration pair (**De-Hum**, **De-Click**) sits at the top of the chain,
where repair belongs: correcting the recording before shaping it. Both start
switched off, so a new session's rack is inaudible. De-clicking needs the audio
on both sides of a click and therefore only applies on render — the panel says
so rather than leaving the user wondering why preview sounds unchanged.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..dsp.effects import EffectChain, GainEffect, ThreeBandEQ
from ..dsp.repair import DeClickEffect, DeHumEffect
from .theme import PALETTE, Palette

__all__ = ["EffectRackPanel", "default_preview_chain"]

#: Range of every gain control in the rack, in dB.
GAIN_RANGE_DB = (-24.0, 24.0)
EQ_RANGE_DB = (-18.0, 18.0)

#: Mains frequency choices offered by the de-hummer, plus auto-detection.
HUM_CHOICES: tuple[tuple[str, float | str], ...] = (
    ("Auto", "auto"),
    ("50 Hz", 50.0),
    ("60 Hz", 60.0),
)


def default_preview_chain() -> EffectChain:
    """The rack a new session starts with: repair, then a 3-band EQ into a trim.

    The EQ and trim are flat and the two repair effects are switched off, so
    the chain is inaudible until something is moved. Everything but the
    de-clicker streams, and the chain skips that one during preview.
    """
    return EffectChain(
        [
            DeHumEffect(enabled=False),
            DeClickEffect(enabled=False),
            ThreeBandEQ(),
            GainEffect(gain_db=0.0, ramp_ms=20.0),
        ]
    )


def _hum_choice_index(dehum: DeHumEffect) -> int:
    """Which entry of :data:`HUM_CHOICES` an effect's setting corresponds to."""
    if dehum.auto:
        return 0
    for index, (_label, value) in enumerate(HUM_CHOICES):
        if isinstance(value, float) and abs(value - dehum.frequency) < 0.5:
            return index
    return 0


class _DbSlider(QWidget):
    """Labelled integer-dB slider — Qt sliders only carry ints."""

    valueChanged = Signal(float)

    def __init__(
        self,
        text: str,
        minimum: float,
        maximum: float,
        value: float = 0.0,
        suffix: str = " dB",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._suffix = suffix
        self.caption = QLabel(text)
        self.caption.setObjectName("SecondaryTimecode")
        self.readout = QLabel()
        self.readout.setObjectName("SecondaryTimecode")
        self.readout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.readout.setMinimumWidth(56)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(int(round(minimum * 10)), int(round(maximum * 10)))
        self.slider.setValue(int(round(value * 10)))
        self.slider.valueChanged.connect(self._on_moved)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.addWidget(self.caption)
        header.addStretch(1)
        header.addWidget(self.readout)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)
        layout.addLayout(header)
        layout.addWidget(self.slider)
        self._update_readout()

    @property
    def value(self) -> float:
        return self.slider.value() / 10.0

    def set_value(self, value: float) -> None:
        self.slider.setValue(int(round(value * 10)))

    def _on_moved(self, _raw: int) -> None:
        self._update_readout()
        self.valueChanged.emit(self.value)

    def _update_readout(self) -> None:
        value = self.value
        sign = "+" if value > 0 and self._suffix == " dB" else ""
        self.readout.setText(f"{sign}{value:.1f}{self._suffix}")


class EffectRackPanel(QWidget):
    """Controls for a live :class:`EffectChain`.

    Examples
    --------
    Needs a running ``QApplication``, so this is illustration rather than a
    doctest::

        rack = EffectRackPanel(chain)
        rack.chainChanged.connect(window.refresh_preview_status)
    """

    #: Emitted after any control changes the chain.
    chainChanged = Signal()

    def __init__(
        self,
        chain: EffectChain | None = None,
        parent: QWidget | None = None,
        palette: Palette = PALETTE,
    ) -> None:
        super().__init__(parent)
        self.chain = chain if chain is not None else default_preview_chain()
        self._palette = palette

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        layout.addWidget(self._build_master())
        layout.addWidget(self._build_dehum())
        layout.addWidget(self._build_declick())
        layout.addWidget(self._build_eq())
        layout.addWidget(self._build_trim())
        layout.addWidget(self._build_footer())
        layout.addStretch(1)
        self.setMinimumWidth(240)
        self.refresh()

    # -- construction ------------------------------------------------------

    def _build_master(self) -> QWidget:
        box = QGroupBox("Insert")
        self.bypass_button = QPushButton("Bypass")
        self.bypass_button.setCheckable(True)
        self.bypass_button.setToolTip("Take the whole rack out of the playback path")
        self.bypass_button.toggled.connect(self._on_bypass)

        self.mix_slider = _DbSlider("Mix (dry/wet)", 0.0, 100.0, 100.0, suffix=" %")
        self.mix_slider.valueChanged.connect(self._on_mix)

        layout = QVBoxLayout(box)
        layout.setContentsMargins(8, 4, 8, 8)
        layout.setSpacing(6)
        layout.addWidget(self.bypass_button)
        layout.addWidget(self.mix_slider)
        return box

    def _build_dehum(self) -> QWidget:
        box = QGroupBox("De-Hum")
        self.dehum_enabled = QCheckBox("Enabled")
        self.dehum_enabled.toggled.connect(lambda on: self._set_enabled(self.dehum, on))

        self.hum_frequency = QComboBox()
        for label, _value in HUM_CHOICES:
            self.hum_frequency.addItem(label)
        self.hum_frequency.setToolTip(
            "Mains frequency. Auto measures the harmonic stack of the first buffer"
        )
        self.hum_frequency.currentIndexChanged.connect(self._on_hum_frequency)

        self.hum_harmonics = QSpinBox()
        self.hum_harmonics.setRange(1, 12)
        self.hum_harmonics.setToolTip("Notched harmonics, counting the fundamental")
        self.hum_harmonics.valueChanged.connect(self._on_hum_harmonics)

        self.hum_q = _DbSlider("Notch Q (narrowness)", 5.0, 60.0, 30.0, suffix="")
        self.hum_q.valueChanged.connect(self._on_hum_q)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.addWidget(self.hum_frequency)
        header.addWidget(self.hum_harmonics)

        layout = QVBoxLayout(box)
        layout.setContentsMargins(8, 4, 8, 8)
        layout.setSpacing(4)
        layout.addWidget(self.dehum_enabled)
        layout.addLayout(header)
        layout.addWidget(self.hum_q)
        return box

    def _build_declick(self) -> QWidget:
        box = QGroupBox("De-Click")
        self.declick_enabled = QCheckBox("Enabled (applies on render)")
        self.declick_enabled.setToolTip(
            "Interpolates across impulsive damage. Needs the audio either side of "
            "a click, so it is skipped during live preview"
        )
        self.declick_enabled.toggled.connect(lambda on: self._set_enabled(self.declick, on))

        self.declick_sensitivity = _DbSlider("Sensitivity", 0.0, 100.0, 60.0, suffix=" %")
        self.declick_sensitivity.valueChanged.connect(self._on_declick_sensitivity)

        layout = QVBoxLayout(box)
        layout.setContentsMargins(8, 4, 8, 8)
        layout.setSpacing(4)
        layout.addWidget(self.declick_enabled)
        layout.addWidget(self.declick_sensitivity)
        return box

    def _build_eq(self) -> QWidget:
        box = QGroupBox("3-Band EQ")
        self.eq_enabled = QCheckBox("Enabled")
        self.eq_enabled.setChecked(True)
        self.eq_enabled.toggled.connect(lambda on: self._set_enabled(self.eq, on))

        self.eq_low = _DbSlider("Low shelf 100 Hz", *EQ_RANGE_DB)
        self.eq_mid = _DbSlider("Mid bell 1 kHz", *EQ_RANGE_DB)
        self.eq_high = _DbSlider("High shelf 8 kHz", *EQ_RANGE_DB)
        self.eq_low.valueChanged.connect(lambda db: self._set_band("low", db))
        self.eq_mid.valueChanged.connect(lambda db: self._set_band("mid", db))
        self.eq_high.valueChanged.connect(lambda db: self._set_band("high", db))

        layout = QVBoxLayout(box)
        layout.setContentsMargins(8, 4, 8, 8)
        layout.setSpacing(4)
        layout.addWidget(self.eq_enabled)
        for slider in (self.eq_low, self.eq_mid, self.eq_high):
            layout.addWidget(slider)
        return box

    def _build_trim(self) -> QWidget:
        box = QGroupBox("Trim")
        self.trim_enabled = QCheckBox("Enabled")
        self.trim_enabled.setChecked(True)
        self.trim_enabled.toggled.connect(lambda on: self._set_enabled(self.trim, on))

        self.trim_gain = _DbSlider("Gain", *GAIN_RANGE_DB)
        self.trim_gain.valueChanged.connect(self._on_trim_gain)
        self.polarity = QCheckBox("Invert polarity")
        self.polarity.toggled.connect(self._on_polarity)

        layout = QVBoxLayout(box)
        layout.setContentsMargins(8, 4, 8, 8)
        layout.setSpacing(4)
        layout.addWidget(self.trim_enabled)
        layout.addWidget(self.trim_gain)
        layout.addWidget(self.polarity)
        return box

    def _build_footer(self) -> QWidget:
        footer = QWidget()
        self.status = QLabel()
        self.status.setObjectName("SecondaryTimecode")
        self.status.setWordWrap(True)

        self.reset_button = QPushButton("Reset rack")
        self.reset_button.setToolTip("Return every control to flat")
        self.reset_button.clicked.connect(self.reset)

        grid = QGridLayout(footer)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.addWidget(self.status, 0, 0)
        grid.addWidget(self.reset_button, 1, 0)
        return footer

    # -- chain access ------------------------------------------------------

    @property
    def eq(self) -> ThreeBandEQ | None:
        return next((e for e in self.chain if isinstance(e, ThreeBandEQ)), None)

    @property
    def trim(self) -> GainEffect | None:
        return next((e for e in self.chain if isinstance(e, GainEffect)), None)

    @property
    def dehum(self) -> DeHumEffect | None:
        return next((e for e in self.chain if isinstance(e, DeHumEffect)), None)

    @property
    def declick(self) -> DeClickEffect | None:
        return next((e for e in self.chain if isinstance(e, DeClickEffect)), None)

    def set_chain(self, chain: EffectChain) -> None:
        """Point the panel at a different chain and re-read its state."""
        self.chain = chain
        self.refresh()

    def refresh(self) -> None:
        """Pull control positions back from the chain (after a preset load)."""
        blocked = [
            (widget, widget.blockSignals(True))
            for widget in (
                self.bypass_button, self.mix_slider.slider, self.eq_enabled,
                self.eq_low.slider, self.eq_mid.slider, self.eq_high.slider,
                self.trim_enabled, self.trim_gain.slider, self.polarity,
                self.dehum_enabled, self.hum_frequency, self.hum_harmonics,
                self.hum_q.slider, self.declick_enabled, self.declick_sensitivity.slider,
            )
        ]
        try:
            self.bypass_button.setChecked(self.chain.bypass)
            self.mix_slider.set_value(self.chain.mix * 100.0)
            dehum, declick = self.dehum, self.declick
            if dehum is not None:
                self.dehum_enabled.setChecked(dehum.enabled)
                self.hum_frequency.setCurrentIndex(_hum_choice_index(dehum))
                self.hum_harmonics.setValue(dehum.harmonics)
                self.hum_q.set_value(dehum.q)
            if declick is not None:
                self.declick_enabled.setChecked(declick.enabled)
                self.declick_sensitivity.set_value(declick.sensitivity * 100.0)
            eq, trim = self.eq, self.trim
            if eq is not None:
                self.eq_enabled.setChecked(eq.enabled)
                self.eq_low.set_value(eq.low.gain_db)
                self.eq_mid.set_value(eq.mid.gain_db)
                self.eq_high.set_value(eq.high.gain_db)
            if trim is not None:
                self.trim_enabled.setChecked(trim.enabled)
                self.trim_gain.set_value(trim.gain_db)
                self.polarity.setChecked(trim.invert_polarity)
        finally:
            for widget, previous in blocked:
                widget.blockSignals(previous)
        for slider in (
            self.mix_slider, self.eq_low, self.eq_mid, self.eq_high, self.trim_gain,
            self.hum_q, self.declick_sensitivity,
        ):
            slider._update_readout()  # noqa: SLF001 - sibling widget, signals were blocked
        self._update_status()

    def reset(self) -> None:
        """Flatten every control without replacing the chain object.

        Repair is switched off rather than reset to a default strength: a rack
        that quietly kept rewriting samples after a reset would be the worst
        kind of surprise.
        """
        self.chain.bypass = False
        self.chain.mix = 1.0
        dehum, declick = self.dehum, self.declick
        if dehum is not None:
            dehum.enabled = False
        if declick is not None:
            declick.enabled = False
        eq, trim = self.eq, self.trim
        if eq is not None:
            eq.enabled = True
            for band in eq.bands:
                band.gain_db = 0.0
        if trim is not None:
            trim.enabled = True
            trim.gain_db = 0.0
            trim.invert_polarity = False
        self.refresh()
        self.chainChanged.emit()

    def summary(self) -> str:
        """One-line description of what the rack is doing, for a status bar."""
        if self.chain.bypass:
            return "FX bypassed"
        active = [effect.name for effect in self.chain.active]
        if not active:
            return "FX empty"
        mix = "" if self.chain.mix >= 1.0 else f" @ {self.chain.mix * 100:.0f}% wet"
        return f"FX: {' → '.join(active)}{mix}"

    # -- slots -------------------------------------------------------------

    def _on_bypass(self, bypassed: bool) -> None:
        self.chain.bypass = bypassed
        self._changed()

    def _on_mix(self, percent: float) -> None:
        self.chain.mix = percent / 100.0
        self._changed()

    def _set_enabled(self, effect, enabled: bool) -> None:
        if effect is not None:
            effect.enabled = bool(enabled)
        self._changed()

    def _on_hum_frequency(self, index: int) -> None:
        dehum = self.dehum
        if dehum is not None and 0 <= index < len(HUM_CHOICES):
            dehum.frequency = HUM_CHOICES[index][1]
            dehum.reset()
        self._changed()

    def _on_hum_harmonics(self, count: int) -> None:
        dehum = self.dehum
        if dehum is not None:
            dehum.harmonics = int(count)
        self._changed()

    def _on_hum_q(self, q: float) -> None:
        dehum = self.dehum
        if dehum is not None:
            dehum.q = float(q)
        self._changed()

    def _on_declick_sensitivity(self, percent: float) -> None:
        declick = self.declick
        if declick is not None:
            declick.sensitivity = percent / 100.0
        self._changed()

    def _set_band(self, band: str, gain_db: float) -> None:
        eq = self.eq
        if eq is not None:
            getattr(eq, band).gain_db = float(gain_db)
        self._changed()

    def _on_trim_gain(self, gain_db: float) -> None:
        trim = self.trim
        if trim is not None:
            trim.gain_db = float(gain_db)
        self._changed()

    def _on_polarity(self, inverted: bool) -> None:
        trim = self.trim
        if trim is not None:
            trim.invert_polarity = bool(inverted)
        self._changed()

    def _changed(self) -> None:
        self._update_status()
        self.chainChanged.emit()

    def _update_status(self) -> None:
        self.status.setText(self.summary())
