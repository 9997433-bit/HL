"""Timeline markers and named regions.

A :class:`Marker` names a single frame on the timeline; a :class:`Region` names
a half-open frame range. Both are frozen records, and :class:`MarkerList` keeps
them the way the rest of :mod:`audio_studio.core` keeps editable state: the
container is mutated by replacing its internal tuples rather than by handing out
mutable objects, so a reader that has already taken :attr:`MarkerList.markers`
holds a snapshot that a later edit cannot change underneath it.

Identifiers are allocated per list (``mrk_0001``, ``rgn_0001``) rather than from
a module-global counter, so a list that has been round-tripped through JSON goes
on issuing ids that do not collide with the ones it just read back.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass, replace
from typing import Any

from .types import TimeRange

#: ``type`` discriminators used in the serialized form.
MARKER_KIND = "marker"
REGION_KIND = "region"

MARKER_ID_PREFIX = "mrk_"
REGION_ID_PREFIX = "rgn_"


@dataclass(frozen=True, slots=True)
class Marker:
    """A named point on the timeline, in frames from the start of the clip."""

    id: str
    name: str
    frame: int
    color: str | None = None

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("a marker needs a non-empty id")
        if self.frame < 0:
            raise ValueError(f"marker frame must be non-negative, got {self.frame}")
        object.__setattr__(self, "frame", int(self.frame))

    #: Sort key shared with :class:`Region` so both can be ordered together.
    @property
    def position(self) -> int:
        return self.frame

    def renamed(self, name: str) -> Marker:
        return replace(self, name=name)

    def moved_to(self, frame: int) -> Marker:
        return replace(self, frame=int(frame))

    def to_json(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "type": MARKER_KIND,
            "id": self.id,
            "name": self.name,
            "frame": self.frame,
        }
        if self.color:
            data["color"] = self.color
        return data

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> Marker:
        return cls(
            id=str(data["id"]),
            name=str(data.get("name", "")),
            frame=int(data["frame"]),
            color=_optional_str(data.get("color")),
        )


@dataclass(frozen=True, slots=True)
class Region:
    """A named half-open frame range ``[start, end)`` on the timeline."""

    id: str
    name: str
    start: int
    end: int
    color: str | None = None

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("a region needs a non-empty id")
        if self.start < 0:
            raise ValueError(f"region start must be non-negative, got {self.start}")
        if self.end < self.start:
            raise ValueError(f"region end precedes start: {self.start}..{self.end}")
        object.__setattr__(self, "start", int(self.start))
        object.__setattr__(self, "end", int(self.end))

    @property
    def position(self) -> int:
        return self.start

    @property
    def length(self) -> int:
        return self.end - self.start

    @property
    def is_empty(self) -> bool:
        return self.end == self.start

    @property
    def range(self) -> TimeRange:
        return TimeRange(self.start, self.end)

    def renamed(self, name: str) -> Region:
        return replace(self, name=name)

    def with_range(self, rng: TimeRange) -> Region:
        return replace(self, start=rng.start, end=rng.end)

    def contains(self, frame: int) -> bool:
        return self.start <= frame < self.end

    def to_json(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "type": REGION_KIND,
            "id": self.id,
            "name": self.name,
            "start": self.start,
            "end": self.end,
        }
        if self.color:
            data["color"] = self.color
        return data

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> Region:
        return cls(
            id=str(data["id"]),
            name=str(data.get("name", "")),
            start=int(data["start"]),
            end=int(data["end"]),
            color=_optional_str(data.get("color")),
        )

    @classmethod
    def from_range(
        cls, region_id: str, name: str, rng: TimeRange, color: str | None = None
    ) -> Region:
        return cls(id=region_id, name=name, start=rng.start, end=rng.end, color=color)


#: Either kind of timeline annotation.
MarkerItem = Marker | Region


class MarkerList:
    """Markers and regions for one document, ordered by position.

    Mutating methods replace the stored tuples instead of editing them, so the
    sequences handed out by :attr:`markers` and :attr:`regions` stay valid as
    the snapshot they were when they were taken.
    """

    __slots__ = ("_markers", "_regions")

    def __init__(
        self,
        markers: Iterable[Marker] = (),
        regions: Iterable[Region] = (),
    ) -> None:
        self._markers: tuple[Marker, ...] = tuple(sorted(markers, key=_sort_key))
        self._regions: tuple[Region, ...] = tuple(sorted(regions, key=_sort_key))
        seen: set[str] = set()
        everything: tuple[MarkerItem, ...] = (*self._markers, *self._regions)
        for item in everything:
            if item.id in seen:
                raise ValueError(f"duplicate marker id {item.id!r}")
            seen.add(item.id)

    # ------------------------------------------------------------- inspection

    @property
    def markers(self) -> tuple[Marker, ...]:
        """Markers ordered by frame."""
        return self._markers

    @property
    def regions(self) -> tuple[Region, ...]:
        """Regions ordered by start frame."""
        return self._regions

    @property
    def is_empty(self) -> bool:
        return not self._markers and not self._regions

    def __len__(self) -> int:
        return len(self._markers) + len(self._regions)

    def __iter__(self) -> Iterator[MarkerItem]:
        """Every annotation, markers first, each group in timeline order."""
        yield from self._markers
        yield from self._regions

    def __contains__(self, item_id: object) -> bool:
        return self.get(item_id) is not None if isinstance(item_id, str) else False

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, MarkerList):
            return NotImplemented
        return self._markers == other._markers and self._regions == other._regions

    def __repr__(self) -> str:
        return f"MarkerList({len(self._markers)} markers, {len(self._regions)} regions)"

    def get(self, item_id: str) -> MarkerItem | None:
        return next((item for item in self if item.id == item_id), None)

    def copy(self) -> MarkerList:
        return MarkerList(self._markers, self._regions)

    # --------------------------------------------------------------- mutation

    def add_marker(
        self,
        frame: int,
        name: str = "",
        *,
        color: str | None = None,
        marker_id: str | None = None,
    ) -> Marker:
        """Append a marker at ``frame`` and return it."""
        marker = Marker(
            id=marker_id or self._fresh_id(MARKER_ID_PREFIX),
            name=name or f"Marker {len(self._markers) + 1}",
            frame=frame,
            color=color,
        )
        self.add(marker)
        return marker

    def add_region(
        self,
        start: int,
        end: int,
        name: str = "",
        *,
        color: str | None = None,
        region_id: str | None = None,
    ) -> Region:
        """Append a region spanning ``[start, end)`` and return it."""
        region = Region(
            id=region_id or self._fresh_id(REGION_ID_PREFIX),
            name=name or f"Region {len(self._regions) + 1}",
            start=start,
            end=end,
            color=color,
        )
        self.add(region)
        return region

    def add(self, item: MarkerItem) -> MarkerItem:
        """Insert an existing marker or region, keeping the list ordered."""
        if self.get(item.id) is not None:
            raise ValueError(f"duplicate marker id {item.id!r}")
        if isinstance(item, Marker):
            self._markers = tuple(sorted((*self._markers, item), key=_sort_key))
        else:
            self._regions = tuple(sorted((*self._regions, item), key=_sort_key))
        return item

    def remove(self, item_id: str) -> bool:
        """Drop the marker or region with ``item_id``; False when it is absent."""
        markers = tuple(item for item in self._markers if item.id != item_id)
        regions = tuple(item for item in self._regions if item.id != item_id)
        removed = len(markers) != len(self._markers) or len(regions) != len(self._regions)
        self._markers, self._regions = markers, regions
        return removed

    def rename(self, item_id: str, name: str) -> MarkerItem:
        """Give ``item_id`` a new name and return the replacement record."""
        return self._replace_item(item_id, lambda item: item.renamed(name))

    def move(self, item_id: str, frame: int) -> Marker:
        """Move a marker to ``frame``; raises for a region id."""
        item = self.get(item_id)
        if not isinstance(item, Marker):
            raise KeyError(f"no marker with id {item_id!r}")
        return self._replace_item(item_id, lambda m: m.moved_to(frame))  # type: ignore[return-value]

    def set_range(self, item_id: str, rng: TimeRange) -> Region:
        """Re-span a region; raises for a marker id."""
        item = self.get(item_id)
        if not isinstance(item, Region):
            raise KeyError(f"no region with id {item_id!r}")
        return self._replace_item(item_id, lambda r: r.with_range(rng))  # type: ignore[return-value]

    def clear(self) -> None:
        self._markers = ()
        self._regions = ()

    def _replace_item(self, item_id: str, transform: Callable[[Any], Any]) -> MarkerItem:
        """Swap the record ``item_id`` names for ``transform``'s version of it."""
        for existing in self._markers:
            if existing.id == item_id:
                marker: Marker = transform(existing)
                self._markers = tuple(
                    sorted(
                        (marker if m.id == item_id else m for m in self._markers),
                        key=_sort_key,
                    )
                )
                return marker
        for existing_region in self._regions:
            if existing_region.id == item_id:
                region: Region = transform(existing_region)
                self._regions = tuple(
                    sorted(
                        (region if r.id == item_id else r for r in self._regions),
                        key=_sort_key,
                    )
                )
                return region
        raise KeyError(f"no marker or region with id {item_id!r}")

    def _fresh_id(self, prefix: str) -> str:
        used = {item.id for item in self}
        index = 1
        while f"{prefix}{index:04d}" in used:
            index += 1
        return f"{prefix}{index:04d}"

    # ------------------------------------------------------------- navigation

    def next_marker(self, frame: int) -> Marker | None:
        """The first marker strictly after ``frame``."""
        return next((m for m in self._markers if m.frame > frame), None)

    def previous_marker(self, frame: int) -> Marker | None:
        """The last marker strictly before ``frame``."""
        return next((m for m in reversed(self._markers) if m.frame < frame), None)

    def nearest_marker(self, frame: int) -> Marker | None:
        """The marker closest to ``frame``, or None when the list has none."""
        if not self._markers:
            return None
        return min(self._markers, key=lambda m: (abs(m.frame - frame), m.frame))

    def regions_at(self, frame: int) -> tuple[Region, ...]:
        """Every region covering ``frame``; regions are allowed to overlap."""
        return tuple(region for region in self._regions if region.contains(frame))

    # ------------------------------------------------------------ persistence

    def to_json(self) -> list[dict[str, Any]]:
        """The ``markers`` array stored in ``project.json``."""
        return [item.to_json() for item in self]

    @classmethod
    def from_json(cls, data: Iterable[dict[str, Any]] | None) -> MarkerList:
        """Rebuild a list from the serialized form; ``None`` gives an empty list."""
        markers: list[Marker] = []
        regions: list[Region] = []
        for entry in data or ():
            kind = str(entry.get("type", "")) or _infer_kind(entry)
            if kind == MARKER_KIND:
                markers.append(Marker.from_json(entry))
            elif kind == REGION_KIND:
                regions.append(Region.from_json(entry))
            else:
                raise ValueError(f"unknown marker entry {entry!r}")
        return cls(markers, regions)


def _sort_key(item: MarkerItem) -> tuple[int, str]:
    return item.position, item.id


def _infer_kind(entry: dict[str, Any]) -> str:
    """Classify an entry written without a ``type`` field."""
    if "frame" in entry:
        return MARKER_KIND
    if "start" in entry and "end" in entry:
        return REGION_KIND
    return ""


def _optional_str(value: Any) -> str | None:
    return None if value is None else str(value)
