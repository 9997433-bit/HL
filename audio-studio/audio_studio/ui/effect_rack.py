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

from ..dsp.effects import (
    LOUDNESS_PRESETS,
    CompressorEffect,
    DelayEffect,
    EffectChain,
    FDNReverbEffect,
    GainEffect,
    LimiterEffect,
    LoudnessNormalizeEffect,
    NoiseGateEffect,
    ThreeBandEQ,
)
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

#: Delivery targets offered by the Loudness Match slot, as (label, preset key).
LOUDNESS_CHOICES: tuple[tuple[str, str], ...] = (
    ("Broadcast -23 LUFS (EBU R 128)", "broadcast"),
    ("Streaming -16 LUFS", "streaming"),
)


def default_preview_chain() -> EffectChain:
    """The rack a new session starts with: repair, then a 3-band EQ into a trim.

    The EQ and trim are flat and the two repair effects are switched off, so
    the chain is inaudible until something is moved. Everything streams except
    the de-clicker and the loudness matcher, which need the whole signal; the
    chain skips those two during preview and they apply on render.
    """
    return EffectChain(
        [
            DeHumEffect(enabled=False),
            DeClickEffect(enabled=False),
            NoiseGateEffect(enabled=False),
            ThreeBandEQ(),
            CompressorEffect(enabled=False),
            GainEffect(gain_db=0.0, ramp_ms=20.0),
            DelayEffect(enabled=False),
            FDNReverbEffect(enabled=False),
            LimiterEffect(enabled=False),
            LoudnessNormalizeEffect(enabled=False),
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


def _loudness_choice_index(effect: LoudnessNormalizeEffect) -> int:
    """Which entry of :data:`LOUDNESS_CHOICES` an effect's target corresponds to."""
    for index, (_label, key) in enumerate(LOUDNESS_CHOICES):
        if abs(LOUDNESS_PRESETS[key].target_lufs - effect.target_lufs) < 0.5:
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
        layout.addWidget(self._build_compressor())
        layout.addWidget(self._build_trim())
        layout.addWidget(self._build_time_space())
        layout.addWidget(self._build_limiter())
        layout.addWidget(self._build_loudness())
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

    def _build_compressor(self) -> QWidget:
        box = QGroupBox("Compressor")
        self.compressor_enabled = QCheckBox("Enabled")
        self.compressor_enabled.toggled.connect(
            lambda on: self._set_enabled(self.compressor, on)
        )

        self.compressor_threshold = _DbSlider("Threshold", -60.0, 0.0, -18.0)
        self.compressor_threshold.valueChanged.connect(self._on_compressor_threshold)
        self.compressor_ratio = _DbSlider("Ratio", 1.0, 20.0, 4.0, suffix=":1")
        self.compressor_ratio.valueChanged.connect(self._on_compressor_ratio)

        layout = QVBoxLayout(box)
        layout.setContentsMargins(8, 4, 8, 8)
        layout.setSpacing(4)
        layout.addWidget(self.compressor_enabled)
        layout.addWidget(self.compressor_threshold)
        layout.addWidget(self.compressor_ratio)
        return box

    def _build_time_space(self) -> QWidget:
        box = QGroupBox("Time & Space")

        gate_label = QLabel("Noise Gate")
        gate_label.setObjectName("SecondaryTimecode")
        self.noise_gate_enabled = QCheckBox("Gate enabled")
        self.noise_gate_enabled.toggled.connect(
            lambda on: self._set_enabled(self.noise_gate, on)
        )
        self.noise_gate_threshold = _DbSlider("Threshold", -80.0, 0.0, -45.0)
        self.noise_gate_threshold.valueChanged.connect(self._on_noise_gate_threshold)
        self.noise_gate_ratio = _DbSlider("Ratio", 1.0, 20.0, 4.0, suffix=":1")
        self.noise_gate_ratio.valueChanged.connect(self._on_noise_gate_ratio)

        delay_label = QLabel("Delay")
        delay_label.setObjectName("SecondaryTimecode")
        self.delay_enabled = QCheckBox("Delay enabled")
        self.delay_enabled.toggled.connect(lambda on: self._set_enabled(self.delay, on))
        self.delay_time = _DbSlider("Time", 0.0, 1000.0, 250.0, suffix=" ms")
        self.delay_time.valueChanged.connect(self._on_delay_time)
        self.delay_feedback = _DbSlider("Feedback", 0.0, 95.0, 35.0, suffix=" %")
        self.delay_feedback.valueChanged.connect(self._on_delay_feedback)
        self.delay_mix = _DbSlider("Delay mix", 0.0, 100.0, 35.0, suffix=" %")
        self.delay_mix.valueChanged.connect(self._on_delay_mix)

        reverb_label = QLabel("FDN Reverb")
        reverb_label.setObjectName("SecondaryTimecode")
        self.reverb_enabled = QCheckBox("Reverb enabled")
        self.reverb_enabled.toggled.connect(lambda on: self._set_enabled(self.reverb, on))
        self.reverb_room_size = _DbSlider("Room size", 0.0, 100.0, 60.0, suffix=" %")
        self.reverb_room_size.valueChanged.connect(self._on_reverb_room_size)
        self.reverb_damping = _DbSlider("Damping", 0.0, 100.0, 35.0, suffix=" %")
        self.reverb_damping.valueChanged.connect(self._on_reverb_damping)
        self.reverb_mix = _DbSlider("Reverb mix", 0.0, 100.0, 25.0, suffix=" %")
        self.reverb_mix.valueChanged.connect(self._on_reverb_mix)

        layout = QVBoxLayout(box)
        layout.setContentsMargins(8, 4, 8, 8)
        layout.setSpacing(4)
        for widget in (
            gate_label,
            self.noise_gate_enabled,
            self.noise_gate_threshold,
            self.noise_gate_ratio,
            delay_label,
            self.delay_enabled,
            self.delay_time,
            self.delay_feedback,
            self.delay_mix,
            reverb_label,
            self.reverb_enabled,
            self.reverb_room_size,
            self.reverb_damping,
            self.reverb_mix,
        ):
            layout.addWidget(widget)
        return box

    def _build_limiter(self) -> QWidget:
        box = QGroupBox("True Peak Limiter")
        self.limiter_enabled = QCheckBox("Enabled")
        self.limiter_enabled.toggled.connect(lambda on: self._set_enabled(self.limiter, on))

        self.limiter_ceiling = _DbSlider("Ceiling", -12.0, 0.0, -1.0, suffix=" dBTP")
        self.limiter_ceiling.valueChanged.connect(self._on_limiter_ceiling)

        layout = QVBoxLayout(box)
        layout.setContentsMargins(8, 4, 8, 8)
        layout.setSpacing(4)
        layout.addWidget(self.limiter_enabled)
        layout.addWidget(self.limiter_ceiling)
        return box

    def _build_loudness(self) -> QWidget:
        box = QGroupBox("Loudness Match")
        self.loudness_enabled = QCheckBox("Enabled (applies on render)")
        self.loudness_enabled.setToolTip(
            "Normalise the clip's BS.1770 integrated loudness to the selected "
            "delivery target. Needs the whole signal, so it is skipped during "
            "live preview and applied on render"
        )
        self.loudness_enabled.toggled.connect(
            lambda on: self._set_enabled(self.loudness, on)
        )

        self.loudness_preset = QComboBox()
        for label, _key in LOUDNESS_CHOICES:
            self.loudness_preset.addItem(label)
        self.loudness_preset.setToolTip(
            "Delivery target: the integrated LUFS the render should measure, "
            "with the gain capped so the true peak stays under the preset's ceiling"
        )
        self.loudness_preset.currentIndexChanged.connect(self._on_loudness_preset)

        layout = QVBoxLayout(box)
        layout.setContentsMargins(8, 4, 8, 8)
        layout.setSpacing(4)
        layout.addWidget(self.loudness_enabled)
        layout.addWidget(self.loudness_preset)
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
    def compressor(self) -> CompressorEffect | None:
        return next((e for e in self.chain if isinstance(e, CompressorEffect)), None)

    @property
    def limiter(self) -> LimiterEffect | None:
        return next((e for e in self.chain if isinstance(e, LimiterEffect)), None)

    @property
    def noise_gate(self) -> NoiseGateEffect | None:
        return next((e for e in self.chain if isinstance(e, NoiseGateEffect)), None)

    @property
    def delay(self) -> DelayEffect | None:
        return next((e for e in self.chain if isinstance(e, DelayEffect)), None)

    @property
    def reverb(self) -> FDNReverbEffect | None:
        return next((e for e in self.chain if isinstance(e, FDNReverbEffect)), None)

    @property
    def loudness(self) -> LoudnessNormalizeEffect | None:
        return next(
            (e for e in self.chain if isinstance(e, LoudnessNormalizeEffect)), None
        )

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
                self.compressor_enabled, self.compressor_threshold.slider,
                self.compressor_ratio.slider, self.limiter_enabled,
                self.limiter_ceiling.slider,
                self.loudness_enabled, self.loudness_preset,
                self.noise_gate_enabled, self.noise_gate_threshold.slider,
                self.noise_gate_ratio.slider, self.delay_enabled,
                self.delay_time.slider, self.delay_feedback.slider,
                self.delay_mix.slider, self.reverb_enabled,
                self.reverb_room_size.slider, self.reverb_damping.slider,
                self.reverb_mix.slider,
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
            compressor = self.compressor
            if compressor is not None:
                self.compressor_enabled.setChecked(compressor.enabled)
                self.compressor_threshold.set_value(compressor.threshold_db)
                self.compressor_ratio.set_value(compressor.ratio)
            limiter = self.limiter
            if limiter is not None:
                self.limiter_enabled.setChecked(limiter.enabled)
                self.limiter_ceiling.set_value(limiter.ceiling_db)
            loudness = self.loudness
            if loudness is not None:
                self.loudness_enabled.setChecked(loudness.enabled)
                self.loudness_preset.setCurrentIndex(_loudness_choice_index(loudness))
            noise_gate = self.noise_gate
            if noise_gate is not None:
                self.noise_gate_enabled.setChecked(noise_gate.enabled)
                self.noise_gate_threshold.set_value(noise_gate.threshold_db)
                self.noise_gate_ratio.set_value(noise_gate.ratio)
            delay = self.delay
            if delay is not None:
                self.delay_enabled.setChecked(delay.enabled)
                self.delay_time.set_value(delay.time_ms)
                self.delay_feedback.set_value(delay.feedback * 100.0)
                self.delay_mix.set_value(delay.mix * 100.0)
            reverb = self.reverb
            if reverb is not None:
                self.reverb_enabled.setChecked(reverb.enabled)
                self.reverb_room_size.set_value(reverb.room_size * 100.0)
                self.reverb_damping.set_value(reverb.damping * 100.0)
                self.reverb_mix.set_value(reverb.mix * 100.0)
        finally:
            for widget, previous in blocked:
                widget.blockSignals(previous)
        for slider in (
            self.mix_slider, self.eq_low, self.eq_mid, self.eq_high, self.trim_gain,
            self.compressor_threshold, self.compressor_ratio, self.limiter_ceiling,
            self.noise_gate_threshold, self.noise_gate_ratio, self.delay_time,
            self.delay_feedback, self.delay_mix, self.reverb_room_size,
            self.reverb_damping, self.reverb_mix, self.hum_q,
            self.declick_sensitivity,
        ):
            slider._update_readout()  # noqa: SLF001 - sibling widget, signals were blocked
        self.update_status()

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
        compressor = self.compressor
        if compressor is not None:
            compressor.enabled = False
            compressor.threshold_db = -18.0
            compressor.ratio = 4.0
        limiter = self.limiter
        if limiter is not None:
            limiter.enabled = False
            limiter.ceiling_db = -1.0
        loudness = self.loudness
        if loudness is not None:
            loudness.enabled = False
            loudness.apply_preset(LOUDNESS_CHOICES[0][1])
        noise_gate = self.noise_gate
        if noise_gate is not None:
            noise_gate.enabled = False
            noise_gate.threshold_db = -45.0
            noise_gate.ratio = 4.0
        delay = self.delay
        if delay is not None:
            delay.enabled = False
            delay.time_ms = 250.0
            delay.feedback = 0.35
            delay.mix = 0.35
        reverb = self.reverb
        if reverb is not None:
            reverb.enabled = False
            reverb.room_size = 0.6
            reverb.damping = 0.35
            reverb.mix = 0.25
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

    def _on_compressor_threshold(self, threshold_db: float) -> None:
        compressor = self.compressor
        if compressor is not None:
            compressor.threshold_db = float(threshold_db)
        self._changed()

    def _on_compressor_ratio(self, ratio: float) -> None:
        compressor = self.compressor
        if compressor is not None:
            compressor.ratio = float(ratio)
        self._changed()

    def _on_limiter_ceiling(self, ceiling_db: float) -> None:
        limiter = self.limiter
        if limiter is not None:
            limiter.ceiling_db = float(ceiling_db)
        self._changed()

    def _on_loudness_preset(self, index: int) -> None:
        loudness = self.loudness
        if loudness is not None and 0 <= index < len(LOUDNESS_CHOICES):
            loudness.apply_preset(LOUDNESS_CHOICES[index][1])
        self._changed()

    def _on_noise_gate_threshold(self, threshold_db: float) -> None:
        noise_gate = self.noise_gate
        if noise_gate is not None:
            noise_gate.threshold_db = float(threshold_db)
        self._changed()

    def _on_noise_gate_ratio(self, ratio: float) -> None:
        noise_gate = self.noise_gate
        if noise_gate is not None:
            noise_gate.ratio = float(ratio)
        self._changed()

    def _on_delay_time(self, milliseconds: float) -> None:
        delay = self.delay
        if delay is not None:
            delay.time_ms = float(milliseconds)
        self._changed()

    def _on_delay_feedback(self, percent: float) -> None:
        delay = self.delay
        if delay is not None:
            delay.feedback = percent / 100.0
        self._changed()

    def _on_delay_mix(self, percent: float) -> None:
        delay = self.delay
        if delay is not None:
            delay.mix = percent / 100.0
        self._changed()

    def _on_reverb_room_size(self, percent: float) -> None:
        reverb = self.reverb
        if reverb is not None:
            reverb.room_size = percent / 100.0
        self._changed()

    def _on_reverb_damping(self, percent: float) -> None:
        reverb = self.reverb
        if reverb is not None:
            reverb.damping = percent / 100.0
        self._changed()

    def _on_reverb_mix(self, percent: float) -> None:
        reverb = self.reverb
        if reverb is not None:
            reverb.mix = percent / 100.0
        self._changed()

    def _on_polarity(self, inverted: bool) -> None:
        trim = self.trim
        if trim is not None:
            trim.invert_polarity = bool(inverted)
        self._changed()

    def _changed(self) -> None:
        self.update_status()
        self.chainChanged.emit()

    def update_status(self) -> None:
        """Re-read the chain into the rack's own summary line.

        Public because the chain is not the rack's alone: the plugin slot
        inserts into it too, and its changes have to show up here.
        """
        self.status.setText(self.summary())
