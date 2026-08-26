"""VST3 plugin slot: load one external plugin into the live preview rack.

The panel is the UI half of :mod:`audio_studio.plugins`. It loads a ``.vst3``
bundle, wraps it in a :class:`~audio_studio.plugins.adapter.PluginEffectAdapter`
and inserts that adapter into the same
:class:`~audio_studio.dsp.effects.base.EffectChain` the effect rack drives, so a
plugin is auditioned exactly like a built-in effect: it changes what is heard
and never touches the audio in memory.

There is **one** plugin slot. Loading a second plugin replaces the first rather
than growing a chain — plugin delay compensation, per-slot state persistence and
reordering all have to land before a real plugin rack is honest, and a slot that
silently accumulated unmanaged latency would be worse than no rack at all.

Two constraints shape the rest of this module:

*The GPL boundary.* pedalboard is GPL-3.0 and optional. Nothing here imports it,
directly or transitively: :mod:`audio_studio.plugins` is pedalboard-free to
import, the panel probes for the extra with :func:`importlib.util.find_spec`
(which locates a module without executing it), and pedalboard is only reached
inside :func:`~audio_studio.plugins.adapter.create_plugin_effect` once the user
actually picks a file. Without the extra the panel says so, in place, with the
install command — a dialog the user cannot copy out of would be worse.

*Parameter scales are the plugin's business.* A host reports parameters as a
``{name: value}`` snapshot where the value is normally the 0–1 normalised host
value, but may be anything a plugin chooses to expose. Values in ``[0, 1]``
get a slider; everything else is shown read-only rather than guessed at, because
writing a wrongly-scaled value into a live plugin is audible.
"""

from __future__ import annotations

import importlib.util
from collections.abc import Callable
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from ..dsp.effects import EffectChain, LimiterEffect
from ..plugins import PluginEffectAdapter, PluginLoadError, create_plugin_effect

__all__ = ["PluginPanel", "plugins_extra_installed"]

#: Filter for the load dialog. A ``.vst3`` is a directory bundle on macOS and
#: Linux, so the dialog also has to accept one that the platform presents as a
#: folder; the "All files" entry is the escape hatch for that.
PLUGIN_DIALOG_FILTER = "VST3 plugins (*.vst3);;All files (*)"

#: Sliders resolve a normalised parameter to this many steps.
SLIDER_STEPS = 1000

#: Plugins with hundreds of parameters exist. Past this many rows the panel is
#: unusable as a scroll list anyway, so the remainder is summarised instead.
MAX_PARAMETER_ROWS = 24

_NO_PLUGIN = "No plugin loaded."

_EXTRA_MISSING_HINT = (
    "VST3 hosting needs the optional 'plugins' extra, which is not installed:\n"
    '    pip install "audio-studio[plugins]"\n'
    "It pulls in pedalboard (GPL-3.0) — fine for private use, but an artifact "
    "that bundles it must be distributed under GPL-3.0 as a whole."
)


def plugins_extra_installed() -> bool:
    """Whether pedalboard can be imported, without importing it.

    :func:`importlib.util.find_spec` locates the module without executing it,
    which keeps the GPL boundary intact: probing for the extra must not be the
    thing that loads it.
    """
    try:
        return importlib.util.find_spec("pedalboard") is not None
    except (ImportError, ValueError):
        return False


class _ParameterSlider(QWidget):
    """One normalised (0–1) plugin parameter, as a labelled slider."""

    valueChanged = Signal(str, float)

    def __init__(self, name: str, value: float, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.parameter_name = name

        self.caption = QLabel(name)
        self.caption.setObjectName("SecondaryTimecode")
        self.caption.setToolTip(name)
        self.readout = QLabel()
        self.readout.setObjectName("SecondaryTimecode")
        self.readout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.readout.setMinimumWidth(48)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, SLIDER_STEPS)
        self.slider.setValue(self._to_steps(value))
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
        """Current position on the plugin's own 0–1 scale."""
        return self.slider.value() / SLIDER_STEPS

    def set_value(self, value: float) -> None:
        """Move the slider without telling the plugin (used when re-reading it)."""
        blocked = self.slider.blockSignals(True)
        try:
            self.slider.setValue(self._to_steps(value))
        finally:
            self.slider.blockSignals(blocked)
        self._update_readout()

    @staticmethod
    def _to_steps(value: float) -> int:
        return int(round(min(max(float(value), 0.0), 1.0) * SLIDER_STEPS))

    def _on_moved(self, _raw: int) -> None:
        self._update_readout()
        self.valueChanged.emit(self.parameter_name, self.value)

    def _update_readout(self) -> None:
        self.readout.setText(f"{self.value:.3f}")


class _ParameterReadout(QWidget):
    """A parameter the panel will not pretend to know the scale of."""

    def __init__(self, name: str, value: Any, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.parameter_name = name

        self.caption = QLabel(name)
        self.caption.setObjectName("SecondaryTimecode")
        self.caption.setToolTip(f"{name} — read-only: not a normalised 0–1 parameter")
        self.readout = QLabel(str(value))
        self.readout.setObjectName("SecondaryTimecode")
        self.readout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.caption)
        layout.addStretch(1)
        layout.addWidget(self.readout)

    def set_value(self, value: Any) -> None:
        self.readout.setText(str(value))


class PluginPanel(QWidget):
    """The single external-plugin slot, wired to a live :class:`EffectChain`.

    Parameters
    ----------
    chain:
        The rack to insert the loaded plugin into. May be ``None``, in which
        case the panel still loads plugins but nothing is inserted anywhere —
        useful for testing the widget on its own.
    loader:
        Callable taking a path and returning a
        :class:`~audio_studio.plugins.adapter.PluginEffectAdapter`. Defaults to
        :func:`~audio_studio.plugins.adapter.create_plugin_effect`; tests
        substitute a fake so no plugin binary (and no pedalboard) is needed.

    Examples
    --------
    Needs a running ``QApplication``, so this is illustration rather than a
    doctest::

        panel = PluginPanel(window.effect_chain)
        panel.pluginChanged.connect(window.refresh_preview_status)
        panel.load_plugin("/plugins/GreatVerb.vst3")
    """

    #: Emitted whenever the slot changes: loaded, removed, bypassed, retuned.
    pluginChanged = Signal()

    def __init__(
        self,
        chain: EffectChain | None = None,
        parent: QWidget | None = None,
        *,
        loader: Callable[[str | Path], PluginEffectAdapter] | None = None,
    ) -> None:
        super().__init__(parent)
        self.chain = chain
        self._loader = loader
        self.adapter: PluginEffectAdapter | None = None
        self.parameter_rows: dict[str, _ParameterSlider | _ParameterReadout] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        layout.addWidget(self._build_slot())
        layout.addWidget(self._build_parameters(), 1)
        layout.addWidget(self._build_message())
        self.setMinimumWidth(240)
        self._update_controls()

    # -- construction ------------------------------------------------------

    def _build_slot(self) -> QWidget:
        box = QGroupBox("External Plugin")

        self.load_button = QPushButton("Load VST3…")
        self.load_button.setToolTip(
            "Open a .vst3 bundle and insert it into the preview rack. "
            "One slot: loading another plugin replaces this one"
        )
        self.load_button.clicked.connect(self.open_plugin_dialog)

        self.name_label = QLabel(_NO_PLUGIN)
        self.name_label.setWordWrap(True)

        self.bypass_button = QPushButton("Bypass")
        self.bypass_button.setCheckable(True)
        self.bypass_button.setToolTip("Take the plugin out of the playback path")
        self.bypass_button.toggled.connect(self._on_bypass)

        self.remove_button = QPushButton("Remove")
        self.remove_button.setToolTip("Unload the plugin and take its slot out of the rack")
        self.remove_button.clicked.connect(self.remove_plugin)

        buttons = QHBoxLayout()
        buttons.setContentsMargins(0, 0, 0, 0)
        buttons.addWidget(self.bypass_button)
        buttons.addWidget(self.remove_button)

        layout = QVBoxLayout(box)
        layout.setContentsMargins(8, 4, 8, 8)
        layout.setSpacing(6)
        layout.addWidget(self.load_button)
        layout.addWidget(self.name_label)
        layout.addLayout(buttons)
        return box

    def _build_parameters(self) -> QWidget:
        box = QGroupBox("Parameters")

        self.parameter_container = QWidget()
        self.parameter_layout = QVBoxLayout(self.parameter_container)
        self.parameter_layout.setContentsMargins(0, 0, 0, 0)
        self.parameter_layout.setSpacing(4)

        # A plugin can expose dozens of parameters; the dock is narrow and
        # already shares its side of the window with the effect rack.
        self.parameter_scroll = QScrollArea()
        self.parameter_scroll.setWidgetResizable(True)
        self.parameter_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.parameter_scroll.setWidget(self.parameter_container)

        layout = QVBoxLayout(box)
        layout.setContentsMargins(8, 4, 8, 8)
        layout.addWidget(self.parameter_scroll)
        return box

    def _build_message(self) -> QWidget:
        self.message = QLabel()
        self.message.setObjectName("SecondaryTimecode")
        self.message.setWordWrap(True)
        self.message.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        self.message.setText(_NO_PLUGIN if plugins_extra_installed() else _EXTRA_MISSING_HINT)
        return self.message

    # -- slot management ---------------------------------------------------

    @property
    def has_plugin(self) -> bool:
        return self.adapter is not None

    @property
    def plugin_name(self) -> str | None:
        """Name reported by the loaded plugin, or ``None`` when the slot is empty."""
        return None if self.adapter is None else self.adapter.plugin_name

    def set_chain(self, chain: EffectChain | None) -> None:
        """Point the panel at a different rack, carrying the loaded plugin over."""
        adapter = self.adapter
        if adapter is not None and self.chain is not None and adapter in self.chain.effects:
            self.chain.remove(adapter)
        self.chain = chain
        if adapter is not None and chain is not None:
            chain.insert(self._insert_index(chain), adapter)

    def open_plugin_dialog(self) -> bool:
        """Ask for a ``.vst3`` bundle and load it."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Load VST3 plugin", str(Path.home()), PLUGIN_DIALOG_FILTER
        )
        return self.load_plugin(path) if path else False

    def load_plugin(self, path: str | Path) -> bool:
        """Load ``path`` into the slot, replacing whatever was there.

        Returns ``False`` and reports in the panel's message line when the
        plugin (or the ``plugins`` extra) could not be loaded; the previously
        loaded plugin is left untouched in that case, because dropping a
        working plugin because a second one failed to open would be rude.
        """
        loader = self._loader if self._loader is not None else create_plugin_effect
        try:
            adapter = loader(path)
        except (PluginLoadError, ValueError, OSError) as exc:
            self.message.setText(str(exc))
            return False

        self._detach_adapter()
        self.adapter = adapter
        if self.chain is not None:
            self.chain.insert(self._insert_index(self.chain), adapter)
        self.name_label.setText(f"{adapter.plugin_name}\n{adapter.plugin_path}")
        self.message.setText(f"Loaded {adapter.plugin_name} into the preview rack.")
        self.refresh_parameters()
        self._update_controls()
        self.pluginChanged.emit()
        return True

    def remove_plugin(self) -> bool:
        """Unload the plugin and take its slot out of the rack."""
        if self.adapter is None:
            return False
        name = self.adapter.plugin_name
        self._detach_adapter()
        self.adapter = None
        self.name_label.setText(_NO_PLUGIN)
        self.message.setText(f"Removed {name}.")
        self.refresh_parameters()
        self._update_controls()
        self.pluginChanged.emit()
        return True

    def _detach_adapter(self) -> None:
        adapter = self.adapter
        if adapter is not None and self.chain is not None and adapter in self.chain.effects:
            self.chain.remove(adapter)

    @staticmethod
    def _insert_index(chain: EffectChain) -> int:
        """Where the plugin goes: ahead of the limiter, if the rack has one.

        A true-peak limiter is the rack's safety net, and an unknown plugin is
        exactly what it is there to catch. Everything else is appended.
        """
        return next(
            (i for i, effect in enumerate(chain) if isinstance(effect, LimiterEffect)),
            len(chain),
        )

    # -- parameters --------------------------------------------------------

    def refresh_parameters(self) -> None:
        """Rebuild the parameter controls from the plugin's current snapshot."""
        self._clear_parameters()
        if self.adapter is None:
            return
        try:
            snapshot = self.adapter.plugin_parameters()
        except Exception as exc:  # noqa: BLE001 - a plugin that cannot be read is not fatal
            self.message.setText(f"Could not read plugin parameters: {exc}")
            return

        for name, value in list(snapshot.items())[:MAX_PARAMETER_ROWS]:
            row = self._build_parameter_row(name, value)
            self.parameter_rows[name] = row
            self.parameter_layout.addWidget(row)
        hidden = len(snapshot) - len(self.parameter_rows)
        if hidden > 0:
            note = QLabel(f"…and {hidden} more parameters (edit them in the plugin's own UI)")
            note.setObjectName("SecondaryTimecode")
            note.setWordWrap(True)
            self.parameter_layout.addWidget(note)
        self.parameter_layout.addStretch(1)

    def read_parameters(self) -> None:
        """Pull the control positions back from the plugin, without rebuilding."""
        if self.adapter is None:
            return
        for name, value in self.adapter.plugin_parameters().items():
            row = self.parameter_rows.get(name)
            if isinstance(row, _ParameterSlider) and _is_normalised(value):
                row.set_value(float(value))
            elif isinstance(row, _ParameterReadout):
                row.set_value(value)

    def _build_parameter_row(
        self, name: str, value: Any
    ) -> _ParameterSlider | _ParameterReadout:
        if _is_normalised(value):
            slider = _ParameterSlider(name, float(value))
            slider.valueChanged.connect(self._on_parameter)
            return slider
        return _ParameterReadout(name, value)

    def _clear_parameters(self) -> None:
        self.parameter_rows.clear()
        while (item := self.parameter_layout.takeAt(0)) is not None:
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

    def _on_parameter(self, name: str, value: float) -> None:
        if self.adapter is None:
            return
        try:
            self.adapter.set_parameter(name, value)
        except (NotImplementedError, KeyError, ValueError, TypeError) as exc:
            self.message.setText(f"Could not set {name}: {exc}")
            return
        self.message.setText(f"{name} = {value:.3f}")
        self.pluginChanged.emit()

    # -- state -------------------------------------------------------------

    def summary(self) -> str:
        """One-line description of the slot, for a status bar."""
        if self.adapter is None:
            return "Plugin: none"
        state = "bypassed" if self.adapter.bypass else "active"
        return f"Plugin: {self.adapter.plugin_name} ({state})"

    def _on_bypass(self, bypassed: bool) -> None:
        if self.adapter is not None:
            self.adapter.bypass = bool(bypassed)
        self.pluginChanged.emit()

    def _update_controls(self) -> None:
        adapter = self.adapter
        self.bypass_button.setEnabled(adapter is not None)
        self.remove_button.setEnabled(adapter is not None)
        blocked = self.bypass_button.blockSignals(True)
        try:
            self.bypass_button.setChecked(adapter is not None and adapter.bypass)
        finally:
            self.bypass_button.blockSignals(blocked)


def _is_normalised(value: Any) -> bool:
    """Whether a reported parameter is a plain number on the 0–1 host scale."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return 0.0 <= float(value) <= 1.0
