"""Dockable list of the timeline markers and regions.

The panel is a view, not an owner: it never edits the
:class:`~audio_studio.core.markers.MarkerList` it is shown. Every button and
double-click leaves as a signal for
:class:`~audio_studio.ui.main_window.MainWindow` to act on, so the marker list,
the waveform flags and the project file all change through one code path.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..core.markers import Marker, MarkerItem, MarkerList, Region
from ..core.types import format_timecode
from .theme import PALETTE, Palette

__all__ = ["MarkerPanel"]

#: Role holding the id of the marker or region a row stands for.
ID_ROLE = Qt.ItemDataRole.UserRole

#: Shown in the length column for markers, which have no duration.
NO_LENGTH = "—"


class MarkerPanel(QWidget):
    """Table of markers and regions with add/rename/remove controls."""

    #: Emitted with a frame when a row is activated.
    goToRequested = Signal(int)

    #: Emitted with the :class:`~audio_studio.core.markers.Region` behind an
    #: activated region row, so the owner can restore the range as a selection.
    regionActivated = Signal(object)

    #: Emitted with the highlighted row's id, or ``None`` when nothing is selected.
    selectionChanged = Signal(object)

    addMarkerRequested = Signal()
    addRegionRequested = Signal()
    renameRequested = Signal(str)
    removeRequested = Signal(str)

    def __init__(self, parent: QWidget | None = None, palette: Palette = PALETTE) -> None:
        super().__init__(parent)
        self._palette = palette
        self._sample_rate = 44_100
        self._markers = MarkerList()

        self.tree = QTreeWidget()
        self.tree.setColumnCount(3)
        self.tree.setHeaderLabels(["Name", "Start", "Length"])
        self.tree.setRootIsDecorated(False)
        self.tree.setUniformRowHeights(True)
        self.tree.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
        self.tree.setColumnWidth(0, 118)
        self.tree.setColumnWidth(1, 78)

        self.add_marker_button = QPushButton("Marker")
        self.add_marker_button.setToolTip("Add a marker at the playhead (M)")
        self.add_region_button = QPushButton("Region")
        self.add_region_button.setToolTip("Add a region spanning the selection (Shift+M)")
        self.rename_button = QPushButton("Rename")
        self.remove_button = QPushButton("Remove")

        buttons = QHBoxLayout()
        buttons.setContentsMargins(6, 6, 6, 6)
        buttons.setSpacing(4)
        for button in (
            self.add_marker_button,
            self.add_region_button,
            self.rename_button,
            self.remove_button,
        ):
            buttons.addWidget(button)
        buttons.addStretch(1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.tree, 1)
        layout.addLayout(buttons)

        self.add_marker_button.clicked.connect(self.addMarkerRequested)
        self.add_region_button.clicked.connect(self.addRegionRequested)
        self.rename_button.clicked.connect(self._on_rename)
        self.remove_button.clicked.connect(self._on_remove)
        self.tree.itemActivated.connect(self._on_activated)
        self.tree.itemDoubleClicked.connect(self._on_activated)
        self.tree.itemSelectionChanged.connect(self._update_buttons)

        self._update_buttons()

    # --------------------------------------------------------------- contents

    @property
    def markers(self) -> MarkerList:
        """The snapshot the table is currently showing."""
        return self._markers

    def set_markers(self, markers: MarkerList, sample_rate: int | None = None) -> None:
        """Rebuild the table, keeping the selected row where it still exists."""
        if sample_rate:
            self._sample_rate = max(int(sample_rate), 1)
        self._markers = markers
        keep = self.selected_id
        self.tree.clear()
        for item in markers:
            self.tree.addTopLevelItem(self._row_for(item))
        if keep is not None:
            self.select(keep)
        self._update_buttons()

    @property
    def row_count(self) -> int:
        return self.tree.topLevelItemCount()

    def _row_for(self, item: MarkerItem) -> QTreeWidgetItem:
        rate = self._sample_rate
        if isinstance(item, Marker):
            row = QTreeWidgetItem([item.name, format_timecode(item.frame / rate), NO_LENGTH])
            row.setToolTip(0, f"Marker at frame {item.frame:,}")
        else:
            row = QTreeWidgetItem(
                [
                    item.name,
                    format_timecode(item.start / rate),
                    format_timecode(item.length / rate),
                ]
            )
            row.setToolTip(0, f"Region {item.start:,}–{item.end:,} frames")
        row.setData(0, ID_ROLE, item.id)
        row.setBackground(0, self._swatch(item))
        return row

    def _swatch(self, item: MarkerItem) -> QColor:
        """Tint the name cell so a row's colour matches its flag on the waveform."""
        fallback = "marker" if isinstance(item, Marker) else "region"
        colour = QColor(item.color) if item.color else QColor()
        if not colour.isValid():
            colour = self._palette.color(fallback)
        colour.setAlpha(40)
        return colour

    # -------------------------------------------------------------- selection

    @property
    def selected_id(self) -> str | None:
        items = self.tree.selectedItems()
        if not items:
            return None
        value = items[0].data(0, ID_ROLE)
        return None if value is None else str(value)

    def select(self, item_id: str) -> bool:
        for index in range(self.tree.topLevelItemCount()):
            row = self.tree.topLevelItem(index)
            if row is not None and row.data(0, ID_ROLE) == item_id:
                self.tree.setCurrentItem(row)
                return True
        return False

    def _update_buttons(self) -> None:
        selected = self.selected_id
        self.rename_button.setEnabled(selected is not None)
        self.remove_button.setEnabled(selected is not None)
        self.selectionChanged.emit(selected)

    # ------------------------------------------------------------------ slots

    def _on_rename(self) -> None:
        item_id = self.selected_id
        if item_id is not None:
            self.renameRequested.emit(item_id)

    def _on_remove(self) -> None:
        item_id = self.selected_id
        if item_id is not None:
            self.removeRequested.emit(item_id)

    def _on_activated(self, row: QTreeWidgetItem, _column: int = 0) -> None:
        item = self._markers.get(str(row.data(0, ID_ROLE)))
        if item is None:
            return
        self.goToRequested.emit(item.position)
        if isinstance(item, Region):
            self.regionActivated.emit(item)
