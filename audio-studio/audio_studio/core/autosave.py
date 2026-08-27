"""Interval autosave and crash recovery (SOTA checklist E4).

An editor that loses an hour of work when it is killed is not shippable, and
"we call save() in a finally block" is not a design: a process that takes
SIGKILL, a kernel panic or a power cut never reaches its own cleanup. What
survives a crash is only what already reached the filesystem, so the whole
problem is making sure that whatever is on disk at any instant is a *complete*
session rather than half of one.

The scheme here is a two-slot journal:

``<root>/<session-id>/slot-a`` and ``slot-b`` hold project bundles written by
the ordinary :class:`~audio_studio.project.store.ProjectStore`, so a recovered
session is exactly what "Save" would have produced. ``journal.json`` is a small
pointer naming which slot is complete, and it is rewritten atomically —
temporary file, ``fsync``, ``os.replace`` — only after the bundle it points at
has been fully written and flushed. Because saves alternate between the slots,
the bundle the pointer names is never the one being overwritten, so a crash at
any point leaves the pointer aimed at an intact snapshot. The worst a crash can
cost is the edits made since the last completed autosave.

Three things then have to be true before recovery offers anything back, and
:class:`RecoverableSession` checks each of them separately:

* the journal parses and its own checksum matches, so a torn pointer write is
  detected rather than followed;
* the bundle's content digest matches what the journal recorded, so a torn
  *bundle* write is detected too;
* the process that owned the journal is gone. A live instance's autosave
  directory belongs to that instance; only an abandoned one is a crash.

Liveness is a PID check plus a heartbeat, because a PID alone is not decidable
everywhere: :func:`os.kill` with signal 0 answers it on POSIX, Windows needs a
process handle, and a recycled PID can lie on either. A journal whose last save
is older than :data:`STALE_AFTER_INTERVALS` autosave intervals is therefore
treated as abandoned regardless of what the PID check says.

Nothing here imports Qt. The window drives it (:meth:`AutosaveJournal.start`
runs the timer on a daemon thread), but the harness in
``tools/crash_recovery.py`` drives the same objects headlessly, which is what
makes the evidence for E4 reproducible in CI.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import shutil
import sys
import threading
import time
import uuid
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .. import __app_name__, __version__
from ..project.store import PROJECT_JSON, ProjectSnapshot, ProjectStore, load_project

__all__ = [
    "DEFAULT_INTERVAL_S",
    "ENVIRONMENT_ROOT",
    "JOURNAL_NAME",
    "SLOTS",
    "STALE_AFTER_INTERVALS",
    "AutosaveJournal",
    "JournalEntry",
    "RecoverableSession",
    "bundle_digest",
    "default_root",
    "discover",
    "process_alive",
]

#: How often the window autosaves while a document is dirty.
DEFAULT_INTERVAL_S = 30.0

#: Heartbeat allowance. A journal untouched for this many intervals is treated
#: as abandoned even if something still answers to its PID, which is the only
#: defence against a recycled PID pinning a crashed session as "live" forever.
STALE_AFTER_INTERVALS = 6

JOURNAL_NAME = "journal.json"
SLOTS = ("a", "b")
SCHEMA_VERSION = 1

#: Overrides the autosave location, for tests, for the crash harness, and for
#: users whose state directory is not where the platform says it is.
ENVIRONMENT_ROOT = "AUDIO_STUDIO_AUTOSAVE_DIR"


def default_root() -> Path:
    """Where autosave journals live on this platform."""
    override = os.environ.get(ENVIRONMENT_ROOT, "").strip()
    if override:
        return Path(override).expanduser()
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library/Application Support"
    else:
        base = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state"))
    return base / "audio-studio" / "autosave"


def process_alive(pid: int) -> bool:
    """Whether a process with ``pid`` currently exists.

    POSIX answers this with signal 0; a permission error means the process is
    there but owned by someone else, which still counts as alive. Windows has
    no such signal, so the process is opened for synchronisation and asked
    whether it has become signalled — a handle that opens and has not been
    signalled belongs to a running process. When neither route can answer, the
    caller falls back on the heartbeat.
    """
    if pid <= 0:
        return False
    if sys.platform == "win32":  # pragma: no cover - exercised on the Windows runner
        import ctypes

        synchronize = 0x00100000
        wait_timeout = 0x00000102
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(synchronize, False, int(pid))
        if not handle:
            return False
        try:
            return kernel32.WaitForSingleObject(handle, 0) == wait_timeout
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _fsync_path(path: Path) -> None:
    """Flush ``path`` to the device, tolerating platforms that refuse.

    Directory ``fsync`` is how a rename is made durable on POSIX and is simply
    not available on Windows; a failure here costs durability across a power
    cut, never correctness, so it is never allowed to fail a save.
    """
    with contextlib.suppress(OSError, PermissionError):
        fd = os.open(path, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


def _iter_files(root: Path) -> Iterator[Path]:
    yield from sorted(path for path in root.rglob("*") if path.is_file())


def bundle_digest(bundle: Path) -> str:
    """Content digest of an autosaved bundle: every file, path and byte.

    This is what distinguishes "the snapshot is there" from "the snapshot is
    whole". A bundle half-written when the process died hashes differently
    from what the journal recorded, and recovery declines it.
    """
    digest = hashlib.sha256()
    for path in _iter_files(bundle):
        relative = path.relative_to(bundle).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(path.stat().st_size).encode("ascii"))
        digest.update(b"\0")
        with path.open("rb") as handle:
            for block in iter(lambda handle=handle: handle.read(1024 * 1024), b""):
                digest.update(block)
    return digest.hexdigest()


@dataclass(frozen=True)
class JournalEntry:
    """The pointer that says which slot holds a complete snapshot."""

    session_id: str
    pid: int
    slot: str
    sequence: int
    saved_at_utc: str
    started_at_utc: str
    payload_sha256: str
    interval_s: float
    host: str = ""
    app_version: str = __version__
    project_path: str | None = None
    label: str = ""

    def to_json(self) -> dict[str, Any]:
        body = {
            "schema_version": SCHEMA_VERSION,
            "app": __app_name__,
            "app_version": self.app_version,
            "session_id": self.session_id,
            "pid": self.pid,
            "host": self.host,
            "slot": self.slot,
            "sequence": self.sequence,
            "saved_at_utc": self.saved_at_utc,
            "started_at_utc": self.started_at_utc,
            "payload_sha256": self.payload_sha256,
            "interval_s": self.interval_s,
            "project_path": self.project_path,
            "label": self.label,
        }
        return {**body, "checksum": _checksum(body)}

    @classmethod
    def from_json(cls, payload: dict[str, Any]) -> JournalEntry:
        """Parse a journal, refusing one whose checksum does not match.

        The checksum is over the pointer's own fields, so a write torn by a
        crash mid-``replace`` (or a file truncated to nothing) is rejected here
        instead of sending recovery at a slot that was never finished.
        """
        if payload.get("schema_version") != SCHEMA_VERSION:
            raise ValueError(f"unsupported autosave schema {payload.get('schema_version')!r}")
        checksum = payload.get("checksum")
        body = {key: value for key, value in payload.items() if key != "checksum"}
        if checksum != _checksum(body):
            raise ValueError("autosave journal checksum mismatch")
        if payload.get("slot") not in SLOTS:
            raise ValueError(f"unknown autosave slot {payload.get('slot')!r}")
        return cls(
            session_id=str(payload["session_id"]),
            pid=int(payload["pid"]),
            slot=str(payload["slot"]),
            sequence=int(payload["sequence"]),
            saved_at_utc=str(payload["saved_at_utc"]),
            started_at_utc=str(payload.get("started_at_utc", "")),
            payload_sha256=str(payload["payload_sha256"]),
            interval_s=float(payload.get("interval_s", DEFAULT_INTERVAL_S)),
            host=str(payload.get("host", "")),
            app_version=str(payload.get("app_version", "")),
            project_path=payload.get("project_path"),
            label=str(payload.get("label", "")),
        )

    @property
    def saved_at(self) -> datetime | None:
        try:
            return datetime.fromisoformat(self.saved_at_utc)
        except ValueError:
            return None


def _checksum(body: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


#: What the caller hands over at each autosave: the keyword arguments
#: :meth:`ProjectStore.save` takes, gathered at the moment of the snapshot.
SnapshotSource = Callable[[], dict[str, Any]]


@dataclass
class AutosaveJournal:
    """Periodic crash-safe snapshots of one running session.

    The instance owns one directory under ``root`` for as long as it lives.
    :meth:`release` removes it, which is the difference between "this session
    exited" and "this session crashed": a directory left behind is the only
    signal recovery has.
    """

    root: Path = field(default_factory=default_root)
    interval_s: float = DEFAULT_INTERVAL_S
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    label: str = ""
    #: The project the session came from, recorded so recovery can tell the
    #: user which file the snapshot belongs to. ``None`` for unsaved work,
    #: which is exactly the work a crash would otherwise destroy outright.
    project_path: Path | None = None

    sequence: int = field(default=0, init=False)
    last_error: Exception | None = field(default=None, init=False)
    _last_save_monotonic: float | None = field(default=None, init=False)
    _thread: threading.Thread | None = field(default=None, init=False)
    _stop: threading.Event = field(default_factory=threading.Event, init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)
    _started_at: str = field(default_factory=_utc_now, init=False)

    def __post_init__(self) -> None:
        self.root = Path(self.root)
        self.interval_s = float(self.interval_s)
        if self.interval_s <= 0:
            raise ValueError("autosave interval must be positive")

    @property
    def directory(self) -> Path:
        return self.root / f"session-{self.session_id}"

    @property
    def journal_path(self) -> Path:
        return self.directory / JOURNAL_NAME

    def slot_path(self, slot: str) -> Path:
        # A snapshot is an ordinary project bundle, extension included, so
        # that a user who goes looking can open one by hand.
        return self.directory / f"slot-{slot}.hlproj"

    @property
    def next_slot(self) -> str:
        """The slot the next save writes: never the one the pointer names."""
        return SLOTS[self.sequence % len(SLOTS)]

    # -- saving ------------------------------------------------------------

    def due(self, now: float | None = None) -> bool:
        if self._last_save_monotonic is None:
            return True
        elapsed = (time.monotonic() if now is None else now) - self._last_save_monotonic
        return elapsed >= self.interval_s

    def maybe_save(self, snapshot: SnapshotSource) -> JournalEntry | None:
        """Autosave if the interval has elapsed, otherwise do nothing."""
        if not self.due():
            return None
        return self.save(snapshot)

    def save(self, snapshot: SnapshotSource) -> JournalEntry:
        """Write a snapshot to the free slot and publish the pointer.

        The order is the whole design: bundle first, flushed; pointer second,
        atomically. A crash before the pointer lands leaves the previous
        snapshot current, and a crash after it lands leaves the new one.
        """
        with self._lock:
            slot = self.next_slot
            target = self.slot_path(slot)
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                shutil.rmtree(target)

            ProjectStore(target).save(**snapshot())
            # The store keeps a dated copy of project.json every time it
            # overwrites one. Useful for a user's project directory, pure
            # accumulation for a slot rewritten every interval.
            shutil.rmtree(target / "backups", ignore_errors=True)

            for path in _iter_files(target):
                _fsync_path(path)
            _fsync_path(target)

            entry = JournalEntry(
                session_id=self.session_id,
                pid=os.getpid(),
                slot=slot,
                sequence=self.sequence + 1,
                saved_at_utc=_utc_now(),
                started_at_utc=self._started_at,
                payload_sha256=bundle_digest(target),
                interval_s=self.interval_s,
                host=os.environ.get("HOSTNAME", "") or "",
                app_version=__version__,
                project_path=str(self.project_path) if self.project_path else None,
                label=self.label,
            )
            self._write_journal(entry)
            self.sequence = entry.sequence
            self._last_save_monotonic = time.monotonic()
            return entry

    def _write_journal(self, entry: JournalEntry) -> None:
        temp = self.directory / f"{JOURNAL_NAME}.{os.getpid()}.tmp"
        payload = json.dumps(entry.to_json(), indent=2, sort_keys=True) + "\n"
        with temp.open("w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, self.journal_path)
        _fsync_path(self.directory)

    # -- background timer --------------------------------------------------

    def start(self, snapshot: SnapshotSource) -> None:
        """Autosave on a daemon thread until :meth:`stop` is called.

        An autosave that raises must not take the editor down with it, so the
        failure is recorded in :attr:`last_error` and the timer keeps its next
        appointment.
        """
        if self._thread is not None:
            raise RuntimeError("autosave is already running")
        self._stop.clear()

        def loop() -> None:
            while not self._stop.wait(self.interval_s):
                try:
                    self.save(snapshot)
                except Exception as error:  # noqa: BLE001 - never kill the editor
                    self.last_error = error

        self._thread = threading.Thread(
            target=loop, name=f"autosave-{self.session_id}", daemon=True
        )
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        self._stop.set()
        thread, self._thread = self._thread, None
        if thread is not None:
            thread.join(timeout)

    def release(self) -> None:
        """Drop the journal on a clean exit; what is left behind is a crash."""
        self.stop()
        shutil.rmtree(self.directory, ignore_errors=True)

    def __enter__(self) -> AutosaveJournal:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.release()


@dataclass(frozen=True)
class RecoverableSession:
    """An autosave directory left behind by a session that never exited."""

    directory: Path
    entry: JournalEntry

    @property
    def bundle(self) -> Path:
        return self.directory / f"slot-{self.entry.slot}.hlproj"

    @property
    def owner_alive(self) -> bool:
        return process_alive(self.entry.pid)

    def heartbeat_age_s(self, now: datetime | None = None) -> float | None:
        saved_at = self.entry.saved_at
        if saved_at is None:
            return None
        return ((now or datetime.now(UTC)) - saved_at).total_seconds()

    def is_stale(self, now: datetime | None = None) -> bool:
        """Whether this snapshot is up for recovery rather than in use."""
        if not self.owner_alive:
            return True
        age = self.heartbeat_age_s(now)
        return age is not None and age > self.entry.interval_s * STALE_AFTER_INTERVALS

    def verify(self) -> bool:
        """Whether the bundle on disk is the whole one the journal recorded."""
        if not (self.bundle / PROJECT_JSON).is_file():
            return False
        return bundle_digest(self.bundle) == self.entry.payload_sha256

    def load(self) -> ProjectSnapshot:
        """Restore the snapshot, refusing an incomplete one."""
        if not self.verify():
            raise ValueError(f"autosave bundle {self.bundle} is incomplete or altered")
        return load_project(self.bundle)

    def discard(self) -> None:
        shutil.rmtree(self.directory, ignore_errors=True)


def discover(
    root: Path | None = None,
    *,
    include_live: bool = False,
    now: datetime | None = None,
) -> list[RecoverableSession]:
    """Recoverable sessions under ``root``, newest save first.

    Journals that cannot be parsed are skipped rather than raised on: a
    corrupt pointer from some earlier crash must not stop the editor from
    starting, which is the one thing recovery may never do.
    """
    base = Path(root) if root is not None else default_root()
    if not base.is_dir():
        return []

    found: list[RecoverableSession] = []
    for directory in sorted(base.iterdir()):
        journal = directory / JOURNAL_NAME
        if not journal.is_file():
            continue
        try:
            entry = JournalEntry.from_json(json.loads(journal.read_text(encoding="utf-8")))
        except (OSError, ValueError, KeyError, json.JSONDecodeError):
            continue
        session = RecoverableSession(directory, entry)
        if include_live or session.is_stale(now):
            found.append(session)
    found.sort(key=lambda session: session.entry.saved_at_utc, reverse=True)
    return found
