"""VST3 plugin rack: three slots feeding the live preview chain.

The panel is the UI half of :mod:`audio_studio.plugins`. It loads ``.vst3``
bundles, wraps each in a
:class:`~audio_studio.plugins.adapter.PluginEffectAdapter` and inserts those
adapters into the same :class:`~audio_studio.dsp.effects.base.EffectChain` the
effect rack drives, so a plugin is auditioned exactly like a built-in effect: it
changes what is heard and never touches the audio in memory.

There are three slots. They run in slot order — slot 1 first — and always ahead
of the rack's true-peak limiter, which is the safety net for exactly this kind
of unknown processor. **▲**/**▼** swap neighbouring slots, so the chain order
can be changed without reloading anything.

Three constraints shape the rest of this module:

*The GPL boundary.* pedalboard is GPL-3.0 and optional. Nothing here imports it,
directly or transitively: :mod:`audio_studio.plugins` is pedalboard-free to
import, scanning reads only the filesystem, the panel probes for the extra with
:func:`importlib.util.find_spec` (which locates a module without executing it),
and pedalboard is only reached inside
:func:`~audio_studio.plugins.adapter.create_plugin_effect` once the user
actually loads a plugin. Without the extra the panel says so, in place, with the
install command — a dialog the user cannot copy out of would be worse.

*Latency is compensated on the preview, and the panel says by how much.* The
readout under the slots shows the constant the playback path is padded to —
the sum of what every loaded plugin reports, bypassed or not, because plugin
delay compensation (see :mod:`audio_studio.dsp.preview`) holds the path there
so a bypass toggle does not move the stream in time. The **PDC** toggle beside
it turns the padding off (the panel emits :attr:`PluginPanel.pdcToggled`; the
main window forwards it to the preview insert), and the readout then falls
back to reporting the uncompensated delay of the plugins actually running.

*Parameter scales are the plugin's business.* A host reports parameters as a
``{name: value}`` snapshot where the value is normally the 0–1 normalised host
value, but may be anything a plugin chooses to expose. Values in ``[0, 1]``
get a slider; everything else is shown read-only rather than guessed at, because
writing a wrongly-scaled value into a live plugin is audible. Parameters belong
to one slot at a time: the panel shows those of the *selected* slot, which is
the one last loaded or clicked.
"""

from __future__ import annotations

import base64
import binascii
import importlib.util
from collections.abc import Callable, Iterable, Sequence
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (
    QComboBox,
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
from ..plugins.scanner import (
    PluginDescriptor,
    PluginScanError,
    ScanCache,
    default_plugin_paths,
    discover_plugins,
)

__all__ = ["SLOT_COUNT", "PluginPanel", "plugins_extra_installed"]

#: How many plugins can be loaded at once. Three is what fits in the dock
#: without scrolling and is enough for the usual channel-strip shape (character
#: → correction → glue); a rack that grows without plugin delay compensation
#: would mostly grow its uncompensated latency.
SLOT_COUNT = 3

#: Filter for the load dialog. A ``.vst3`` is a directory bundle on macOS and
#: Linux, so the dialog also has to accept one that the platform presents as a
#: folder; the "All files" entry is the escape hatch for that.
PLUGIN_DIALOG_FILTER = "VST3 plugins (*.vst3);;All files (*)"

#: Sliders resolve a normalised parameter to this many steps.
SLIDER_STEPS = 1000

#: Plugins with hundreds of parameters exist. Past this many rows the panel is
#: unusable as a scroll list anyway, so the remainder is summarised instead.
MAX_PARAMETER_ROWS = 24

_EMPTY_SLOT = "Empty"

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
        self.slider.setAccessibleName(name)
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


class _PluginSlotBox(QGroupBox):
    """One slot's controls; the panel owns what they mean.

    The widget holds the adapter currently in the slot but never touches the
    effect chain: insertion order is a property of the rack as a whole, so the
    panel resynchronises it whenever any slot changes.
    """

    loadRequested = Signal(int)
    removeRequested = Signal(int)
    bypassToggled = Signal(int, bool)
    moveRequested = Signal(int, int)
    selected = Signal(int)

    def __init__(self, index: int, parent: QWidget | None = None) -> None:
        super().__init__(f"Plugin Slot {index + 1}", parent)
        self.index = index
        self.adapter: PluginEffectAdapter | None = None

        self.load_button = QPushButton("Load VST3…")
        self.load_button.setToolTip(
            f"Open a .vst3 bundle into slot {index + 1}, replacing whatever is in it"
        )
        self.load_button.clicked.connect(lambda: self.loadRequested.emit(self.index))

        self.name_label = QLabel(_EMPTY_SLOT)
        self.name_label.setObjectName("SecondaryTimecode")
        self.name_label.setWordWrap(True)

        self.bypass_button = QPushButton("Bypass")
        self.bypass_button.setCheckable(True)
        self.bypass_button.setToolTip("Take this plugin out of the playback path")
        self.bypass_button.toggled.connect(
            lambda checked: self.bypassToggled.emit(self.index, bool(checked))
        )

        self.remove_button = QPushButton("Remove")
        self.remove_button.setToolTip("Unload this plugin and empty the slot")
        self.remove_button.clicked.connect(lambda: self.removeRequested.emit(self.index))

        self.up_button = QPushButton("▲")
        self.up_button.setToolTip("Run this plugin one slot earlier in the chain")
        self.up_button.setAccessibleName("Move plugin earlier")
        self.up_button.setMaximumWidth(28)
        self.up_button.clicked.connect(lambda: self.moveRequested.emit(self.index, -1))

        self.down_button = QPushButton("▼")
        self.down_button.setToolTip("Run this plugin one slot later in the chain")
        self.down_button.setAccessibleName("Move plugin later")
        self.down_button.setMaximumWidth(28)
        self.down_button.clicked.connect(lambda: self.moveRequested.emit(self.index, 1))

        buttons = QHBoxLayout()
        buttons.setContentsMargins(0, 0, 0, 0)
        buttons.setSpacing(4)
        buttons.addWidget(self.bypass_button)
        buttons.addWidget(self.remove_button)
        buttons.addWidget(self.up_button)
        buttons.addWidget(self.down_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 8)
        layout.setSpacing(4)
        layout.addWidget(self.load_button)
        layout.addWidget(self.name_label)
        layout.addLayout(buttons)

    # -- state -------------------------------------------------------------

    @property
    def has_plugin(self) -> bool:
        return self.adapter is not None

    def set_adapter(self, adapter: PluginEffectAdapter | None) -> None:
        """Put ``adapter`` (or nothing) in the slot and redraw its controls."""
        self.adapter = adapter
        if adapter is None:
            self.name_label.setText(_EMPTY_SLOT)
            self.setToolTip("")
        else:
            self.name_label.setText(adapter.plugin_name)
            self.setToolTip(str(adapter.plugin_path))
        self.update_controls(first=self.index == 0, last=self.index == SLOT_COUNT - 1)

    def update_controls(self, *, first: bool, last: bool) -> None:
        loaded = self.adapter is not None
        self.bypass_button.setEnabled(loaded)
        self.remove_button.setEnabled(loaded)
        self.up_button.setEnabled(loaded and not first)
        self.down_button.setEnabled(loaded and not last)
        blocked = self.bypass_button.blockSignals(True)
        try:
            self.bypass_button.setChecked(loaded and bool(self.adapter and self.adapter.bypass))
        finally:
            self.bypass_button.blockSignals(blocked)

    def set_selected(self, selected: bool) -> None:
        """Mark the slot whose parameters the panel is showing."""
        title = f"Plugin Slot {self.index + 1}"
        self.setTitle(f"▸ {title}" if selected else title)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt override
        self.selected.emit(self.index)
        super().mousePressEvent(event)


class PluginPanel(QWidget):
    """Three external-plugin slots, wired to a live :class:`EffectChain`.

    Parameters
    ----------
    chain:
        The rack to insert loaded plugins into. May be ``None``, in which case
        the panel still loads plugins but nothing is inserted anywhere — useful
        for testing the widget on its own.
    loader:
        Callable taking a path and returning a
        :class:`~audio_studio.plugins.adapter.PluginEffectAdapter`. Defaults to
        :func:`~audio_studio.plugins.adapter.create_plugin_effect`; tests
        substitute a fake so no plugin binary (and no pedalboard) is needed.
    scanner:
        Callable taking a directory and returning the
        :class:`~audio_studio.plugins.scanner.PluginDescriptor` list to offer in
        the combo. Defaults to a cached
        :func:`~audio_studio.plugins.scanner.discover_plugins` over that one
        directory.

    Examples
    --------
    Needs a running ``QApplication``, so this is illustration rather than a
    doctest::

        panel = PluginPanel(window.effect_chain)
        panel.pluginChanged.connect(window.refresh_preview_status)
        panel.scan_directory("/usr/lib/vst3")
        panel.load_plugin("/usr/lib/vst3/GreatVerb.vst3", slot=0)
    """

    #: Emitted whenever the rack changes: loaded, removed, moved, bypassed,
    #: retuned.
    pluginChanged = Signal()

    #: Emitted when the PDC toggle changes; carries the new enabled state.
    #: The panel only *announces* the preference — whoever owns the
    #: :class:`~audio_studio.dsp.preview.EffectPreview` applies it there.
    pdcToggled = Signal(bool)

    def __init__(
        self,
        chain: EffectChain | None = None,
        parent: QWidget | None = None,
        *,
        loader: Callable[[str | Path], PluginEffectAdapter] | None = None,
        scanner: Callable[[Path], list[PluginDescriptor]] | None = None,
    ) -> None:
        super().__init__(parent)
        self.setAccessibleName("VST3 plugins")
        self.chain = chain
        self._loader = loader
        self._scanner = scanner
        # An in-memory cache: rescanning the same folder after installing one
        # plugin re-reads that plugin's metadata and stats the rest.
        self._scan_cache = ScanCache()
        self._scan_directory: Path | None = None
        self.discovered: list[PluginDescriptor] = []
        self.parameter_rows: dict[str, _ParameterSlider | _ParameterReadout] = {}
        self._active_slot = 0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        layout.addWidget(self._build_browser())
        self.slots: list[_PluginSlotBox] = []
        for index in range(SLOT_COUNT):
            slot = self._build_slot(index)
            self.slots.append(slot)
            layout.addWidget(slot)
        layout.addWidget(self._build_latency())
        layout.addWidget(self._build_parameters(), 1)
        layout.addWidget(self._build_message())
        self.setMinimumWidth(260)
        self._update_controls()

    # -- construction ------------------------------------------------------

    def _build_browser(self) -> QWidget:
        box = QGroupBox("Installed Plugins")

        self.scan_button = QPushButton("Scan…")
        self.scan_button.setToolTip(
            "Search a folder for .vst3 bundles. Scanning reads the bundles' own "
            "metadata files and never runs plugin code"
        )
        self.scan_button.clicked.connect(self.open_scan_dialog)

        self.plugin_combo = QComboBox()
        self.plugin_combo.setToolTip("Plugins found by the last scan")
        self.plugin_combo.setEnabled(False)
        self.plugin_combo.addItem("No plugins scanned yet")

        self.scan_load_button = QPushButton("Load")
        self.scan_load_button.setToolTip("Load the selected plugin into the first free slot")
        self.scan_load_button.setEnabled(False)
        self.scan_load_button.clicked.connect(self.load_selected)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)
        row.addWidget(self.scan_button)
        row.addWidget(self.plugin_combo, 1)
        row.addWidget(self.scan_load_button)

        layout = QVBoxLayout(box)
        layout.setContentsMargins(8, 4, 8, 8)
        layout.addLayout(row)
        return box

    def _build_slot(self, index: int) -> _PluginSlotBox:
        slot = _PluginSlotBox(index)
        slot.loadRequested.connect(self.open_plugin_dialog)
        slot.removeRequested.connect(self.remove_plugin)
        slot.bypassToggled.connect(self._on_bypass)
        slot.moveRequested.connect(self.move_slot)
        slot.selected.connect(self.set_active_slot)
        return slot

    def _build_latency(self) -> QWidget:
        self.pdc_button = QPushButton("PDC")
        self.pdc_button.setCheckable(True)
        self.pdc_button.setChecked(True)
        self.pdc_button.setMaximumWidth(48)
        self.pdc_button.setToolTip(
            "Plugin delay compensation: pad the playback path to a constant "
            "latency so bypassing a plugin does not move the stream in time"
        )
        self.pdc_button.toggled.connect(self._on_pdc)

        self.latency_label = QLabel()
        self.latency_label.setObjectName("SecondaryTimecode")
        self.latency_label.setToolTip(
            "Delay the loaded plugins report. With PDC on it is the constant "
            "the whole preview path is padded to (bypassed slots included); "
            "with PDC off it is the uncompensated delay of the plugins "
            "actually running, which are then heard late"
        )

        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(self.pdc_button)
        layout.addWidget(self.latency_label, 1)
        return row

    def _build_parameters(self) -> QWidget:
        self.parameter_box = QGroupBox("Parameters")

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

        layout = QVBoxLayout(self.parameter_box)
        layout.setContentsMargins(8, 4, 8, 8)
        layout.addWidget(self.parameter_scroll)
        return self.parameter_box

    def _build_message(self) -> QWidget:
        self.message = QLabel()
        self.message.setObjectName("SecondaryTimecode")
        self.message.setWordWrap(True)
        self.message.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        self.message.setText(_NO_PLUGIN if plugins_extra_installed() else _EXTRA_MISSING_HINT)
        return self.message

    # -- the rack ----------------------------------------------------------

    @property
    def has_plugin(self) -> bool:
        """Whether any slot holds a plugin."""
        return any(slot.has_plugin for slot in self.slots)

    @property
    def adapters(self) -> list[PluginEffectAdapter]:
        """Loaded plugins in chain order, empty slots skipped."""
        return [slot.adapter for slot in self.slots if slot.adapter is not None]

    @property
    def active_slot(self) -> int:
        """Index of the slot whose parameters are on show."""
        return self._active_slot

    @property
    def adapter(self) -> PluginEffectAdapter | None:
        """Plugin in the selected slot, or ``None`` when it is empty."""
        return self.slots[self._active_slot].adapter

    @property
    def plugin_name(self) -> str | None:
        """Name of the plugin in the selected slot, if there is one."""
        adapter = self.adapter
        return None if adapter is None else adapter.plugin_name

    def slot_of(self, index: int) -> _PluginSlotBox:
        """The slot widget at ``index``."""
        return self.slots[index]

    def set_active_slot(self, index: int) -> None:
        """Show ``index``'s parameters. Out-of-range indices are ignored."""
        if not 0 <= index < SLOT_COUNT or index == self._active_slot:
            return
        self._active_slot = index
        self.refresh_parameters()
        self._update_controls()

    def set_chain(self, chain: EffectChain | None) -> None:
        """Point the panel at a different rack, carrying the plugins over."""
        if self.chain is not None:
            self._detach_all(self.chain)
        self.chain = chain
        self._sync_chain()

    # -- loading -----------------------------------------------------------

    def open_plugin_dialog(self, slot: int | None = None) -> bool:
        """Ask for a ``.vst3`` bundle and load it into ``slot``."""
        start = self._scan_directory or next(iter(default_plugin_paths()), Path.home())
        path, _ = QFileDialog.getOpenFileName(
            self, "Load VST3 plugin", str(start), PLUGIN_DIALOG_FILTER
        )
        return self.load_plugin(path, slot=slot) if path else False

    def load_plugin(self, path: str | Path, *, slot: int | None = None) -> bool:
        """Load ``path`` into ``slot``, or into the first free slot.

        Returns ``False`` and reports in the panel's message line when the
        plugin (or the ``plugins`` extra) could not be loaded; the slot keeps
        whatever it already held in that case, because dropping a working
        plugin because a second one failed to open would be rude.
        """
        target = self._target_slot(slot)
        loader = self._loader if self._loader is not None else create_plugin_effect
        try:
            adapter = loader(path)
        except (PluginLoadError, ValueError, OSError) as exc:
            self.message.setText(str(exc))
            return False

        self._detach(self.slots[target].adapter)
        self.slots[target].set_adapter(adapter)
        self._active_slot = target
        self._sync_chain()
        self.message.setText(
            f"Loaded {adapter.plugin_name} into slot {target + 1} of the preview rack."
        )
        self.refresh_parameters()
        self._update_controls()
        self.pluginChanged.emit()
        return True

    def load_selected(self) -> bool:
        """Load the plugin currently chosen in the scan combo."""
        descriptor = self.selected_descriptor()
        if descriptor is None:
            self.message.setText("Scan a folder first, then pick a plugin to load.")
            return False
        return self.load_plugin(descriptor.path)

    def remove_plugin(self, slot: int | None = None) -> bool:
        """Unload the plugin in ``slot`` (the selected one by default)."""
        index = self._active_slot if slot is None else int(slot)
        adapter = self.slots[index].adapter
        if adapter is None:
            return False
        self._detach(adapter)
        self.slots[index].set_adapter(None)
        self._sync_chain()
        self.message.setText(f"Removed {adapter.plugin_name} from slot {index + 1}.")
        self.refresh_parameters()
        self._update_controls()
        self.pluginChanged.emit()
        return True

    def move_slot(self, index: int, delta: int) -> bool:
        """Swap slot ``index`` with the neighbour ``delta`` slots away.

        Slots are the chain order, so swapping two of them is what reordering
        the plugin rack means. The selection follows the plugin that moved.
        """
        other = index + int(delta)
        if not (0 <= index < SLOT_COUNT and 0 <= other < SLOT_COUNT):
            return False
        moving = self.slots[index].adapter
        if moving is None:
            return False
        self.slots[index].set_adapter(self.slots[other].adapter)
        self.slots[other].set_adapter(moving)
        self._active_slot = other
        self._sync_chain()
        self.message.setText(f"Moved {moving.plugin_name} to slot {other + 1}.")
        self.refresh_parameters()
        self._update_controls()
        self.pluginChanged.emit()
        return True

    def _target_slot(self, slot: int | None) -> int:
        """Where a load with no explicit slot goes: the first free one."""
        if slot is not None:
            if not 0 <= int(slot) < SLOT_COUNT:
                raise IndexError(f"plugin slot {slot} is outside 0..{SLOT_COUNT - 1}")
            return int(slot)
        free = next((s.index for s in self.slots if not s.has_plugin), None)
        return self._active_slot if free is None else free

    # -- chain wiring ------------------------------------------------------

    def _sync_chain(self) -> None:
        """Rewrite the chain so the loaded plugins run in slot order.

        Cheaper schemes (insert here, move there) all have to reason about
        where the rack's own effects have moved to since the last edit. Pulling
        the panel's adapters out and putting them back as a block is O(slots)
        on a chain of a handful of effects and cannot drift out of order.
        """
        chain = self.chain
        if chain is None:
            return
        self._detach_all(chain)
        index = self._insert_index(chain)
        for adapter in self.adapters:
            chain.insert(index, adapter)
            index += 1

    def _detach_all(self, chain: EffectChain) -> None:
        for adapter in self.adapters:
            if any(effect is adapter for effect in chain.effects):
                chain.remove(adapter)

    def _detach(self, adapter: PluginEffectAdapter | None) -> None:
        if (
            adapter is not None
            and self.chain is not None
            and any(effect is adapter for effect in self.chain.effects)
        ):
            self.chain.remove(adapter)

    @staticmethod
    def _insert_index(chain: EffectChain) -> int:
        """Where the plugins go: ahead of the limiter, if the rack has one.

        A true-peak limiter is the rack's safety net, and an unknown plugin is
        exactly what it is there to catch. Everything else is appended.
        """
        return next(
            (i for i, effect in enumerate(chain) if isinstance(effect, LimiterEffect)),
            len(chain),
        )

    # -- scanning ----------------------------------------------------------

    def open_scan_dialog(self) -> list[PluginDescriptor]:
        """Ask for a folder and scan it for ``.vst3`` bundles."""
        start = self._scan_directory or next(iter(default_plugin_paths()), Path.home())
        directory = QFileDialog.getExistingDirectory(
            self, "Scan folder for VST3 plugins", str(start)
        )
        return self.scan_directory(directory) if directory else []

    def scan_directory(self, directory: str | Path) -> list[PluginDescriptor]:
        """Populate the combo with the plugins found under ``directory``.

        A scan reads bundle metadata off disk and never loads plugin code, so
        it is safe to point at a folder of unknown plugins. Anything that could
        not be described is left out and counted in the message line rather
        than raised: one broken bundle must not hide the rest.
        """
        root = Path(directory)
        failures: list[Path] = []
        scanner = self._scanner
        try:
            if scanner is not None:
                found = list(scanner(root))
            else:
                found = discover_plugins(
                    [root],
                    cache=self._scan_cache,
                    on_error=lambda bundle, _exc: failures.append(bundle),
                )
        except (OSError, PluginScanError) as exc:
            self.message.setText(f"Could not scan {root}: {exc}")
            return []

        self._scan_directory = root
        self.set_discovered(found)
        skipped = f", {len(failures)} skipped" if failures else ""
        self.message.setText(
            f"Found {len(found)} plugin{'' if len(found) == 1 else 's'} in {root}{skipped}."
            if found
            else f"No .vst3 plugins under {root}{skipped}."
        )
        return found

    def set_discovered(self, descriptors: Iterable[PluginDescriptor]) -> None:
        """Fill the combo from a plugin list, without scanning anything."""
        self.discovered = list(descriptors)
        blocked = self.plugin_combo.blockSignals(True)
        try:
            self.plugin_combo.clear()
            for descriptor in self.discovered:
                self.plugin_combo.addItem(str(descriptor), descriptor)
                self.plugin_combo.setItemData(
                    self.plugin_combo.count() - 1,
                    str(descriptor.path),
                    Qt.ItemDataRole.ToolTipRole,
                )
            if not self.discovered:
                self.plugin_combo.addItem("No plugins found")
        finally:
            self.plugin_combo.blockSignals(blocked)
        self.plugin_combo.setEnabled(bool(self.discovered))
        self.scan_load_button.setEnabled(bool(self.discovered))

    def selected_descriptor(self) -> PluginDescriptor | None:
        """The plugin chosen in the combo, or ``None`` when nothing was found."""
        data = self.plugin_combo.currentData()
        return data if isinstance(data, PluginDescriptor) else None

    # -- latency -----------------------------------------------------------

    @property
    def pdc_enabled(self) -> bool:
        """Whether the panel is asking for plugin delay compensation."""
        return self.pdc_button.isChecked()

    def set_pdc_enabled(self, enabled: bool) -> None:
        """Move the PDC toggle; emits :attr:`pdcToggled` when it changes."""
        self.pdc_button.setChecked(bool(enabled))

    def total_latency_samples(self) -> int:
        """Delay reported by the plugins that are actually in the path.

        A bypassed plugin is not processed, so it contributes nothing. A plugin
        that cannot report its latency counts as zero — the same thing
        pedalboard says for a backend that compensates internally.
        """
        total = 0
        for adapter in self.adapters:
            if adapter.bypass:
                continue
            try:
                total += int(adapter.latency_samples())
            except (AttributeError, TypeError, ValueError):
                continue
        return total

    def compensated_latency_samples(self) -> int:
        """The constant PDC pads the playback path to, in samples.

        Every loaded plugin counts, bypassed or not: compensation's whole
        point is that toggling a bypass swaps plugin delay for an equal
        padding delay, so the figure the listener experiences is this sum
        regardless of which slots are active.
        """
        total = 0
        for adapter in self.adapters:
            try:
                total += max(int(adapter.latency_samples()), 0)
            except (AttributeError, TypeError, ValueError):
                continue
        return total

    def _latency_text(self) -> str:
        if self.pdc_enabled:
            total = self.compensated_latency_samples()
            if total <= 0:
                return "Plugin latency: 0 samples"
            return f"Plugin latency: {total} samples (compensated)"
        total = self.total_latency_samples()
        if total <= 0:
            return "Plugin latency: 0 samples"
        return f"Plugin latency: {total} samples (not compensated)"

    def _on_pdc(self, enabled: bool) -> None:
        self._update_controls()
        self.pdcToggled.emit(bool(enabled))

    # -- parameters --------------------------------------------------------

    def refresh_parameters(self) -> None:
        """Rebuild the parameter controls from the selected plugin's snapshot."""
        self._clear_parameters()
        adapter = self.adapter
        self.parameter_box.setTitle(f"Parameters — Slot {self._active_slot + 1}")
        if adapter is None:
            return
        try:
            snapshot = adapter.plugin_parameters()
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
        adapter = self.adapter
        if adapter is None:
            return
        for name, value in adapter.plugin_parameters().items():
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
        adapter = self.adapter
        if adapter is None:
            return
        try:
            adapter.set_parameter(name, value)
        except (NotImplementedError, KeyError, ValueError, TypeError) as exc:
            self.message.setText(f"Could not set {name}: {exc}")
            return
        self.message.setText(f"{name} = {value:.3f}")
        self.pluginChanged.emit()

    # -- project state -----------------------------------------------------

    def project_state(self) -> list[dict[str, Any]]:
        """What the ``.hlproj`` remembers: which bundle is in which slot.

        Path, bypass flag and — when the host can produce one — an opaque
        state blob, base64-encoded for the JSON bundle. The blob is the
        backend's native state chunk when pedalboard exposes one, and the
        parameter-dict JSON fallback otherwise; either way it is best-effort,
        so a host that cannot serialise simply writes path and bypass the way
        it always did.
        """
        entries: list[dict[str, Any]] = []
        for slot in self.slots:
            adapter = slot.adapter
            if adapter is None:
                continue
            entry: dict[str, Any] = {
                "slot": slot.index,
                "path": str(adapter.plugin_path),
                "bypass": bool(adapter.bypass),
            }
            try:
                blob = adapter.state_blob()
            except Exception:  # noqa: BLE001 - a plugin that cannot save must not block the project
                blob = None
            if blob:
                entry["state"] = base64.b64encode(blob).decode("ascii")
            entries.append(entry)
        return entries

    def restore_project_state(self, entries: Sequence[dict[str, Any]]) -> int:
        """Reload the plugins a project was saved with; returns how many opened.

        Plugins are a property of the machine, not of the project: a bundle may
        have been uninstalled, or the project may be open on a machine without
        the ``plugins`` extra. Every failure is counted and reported in the
        message line, and the slots that did load still work. A saved state
        blob is applied after the plugin opens, best-effort: a blob the plugin
        no longer understands (different version, different backend) leaves the
        plugin at its own defaults rather than failing the slot.
        """
        for slot in self.slots:
            self._detach(slot.adapter)
            slot.set_adapter(None)
        self._active_slot = 0

        loaded = 0
        missing: list[str] = []
        for entry in entries:
            path = str(entry.get("path", ""))
            if not path:
                continue
            index = int(entry.get("slot", loaded))
            if not 0 <= index < SLOT_COUNT:
                index = loaded
            if self.load_plugin(path, slot=index):
                adapter = self.slots[index].adapter
                if adapter is not None:
                    adapter.bypass = bool(entry.get("bypass", False))
                    self._restore_adapter_state(adapter, entry.get("state"))
                loaded += 1
            else:
                missing.append(Path(path).name)

        self._sync_chain()
        self.refresh_parameters()
        self._update_controls()
        if missing:
            self.message.setText(
                f"{len(missing)} plugin{'' if len(missing) == 1 else 's'} from this "
                f"project could not be loaded: {', '.join(missing)}"
            )
        self.pluginChanged.emit()
        return loaded

    @staticmethod
    def _restore_adapter_state(adapter: PluginEffectAdapter, state: Any) -> bool:
        """Best-effort application of a saved base64 state blob to ``adapter``."""
        if not state:
            return False
        try:
            blob = base64.b64decode(str(state), validate=True)
        except (binascii.Error, ValueError):
            return False
        try:
            return bool(adapter.restore_state(blob))
        except Exception:  # noqa: BLE001 - stale state must not fail the slot it rode in on
            return False

    # -- status ------------------------------------------------------------

    def summary(self) -> str:
        """One-line description of the rack, for a status bar."""
        loaded = self.adapters
        if not loaded:
            return "Plugins: none"
        parts = [
            f"{adapter.plugin_name} ({'bypassed' if adapter.bypass else 'active'})"
            for adapter in loaded
        ]
        return "Plugins: " + ", ".join(parts)

    def _on_bypass(self, index: int, bypassed: bool) -> None:
        adapter = self.slots[index].adapter
        if adapter is not None:
            adapter.bypass = bool(bypassed)
        self._update_controls()
        self.pluginChanged.emit()

    def _update_controls(self) -> None:
        for slot in self.slots:
            slot.update_controls(first=slot.index == 0, last=slot.index == SLOT_COUNT - 1)
            slot.set_selected(slot.index == self._active_slot)
        self.latency_label.setText(self._latency_text())


def _is_normalised(value: Any) -> bool:
    """Whether a reported parameter is a plain number on the 0–1 host scale."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return 0.0 <= float(value) <= 1.0
