"""Find the VST3 bundles installed on this machine, without loading any of them.

A plugin rack is only usable if the user can pick a plugin from a list instead
of remembering where an installer put it, so the panel needs a directory scan.
Scanning is the step where a host traditionally crashes: a plugin's metadata
normally comes from loading its binary and asking the factory, and a single bad
bundle then takes the editor down with it.

This module avoids that trade-off by reading metadata off the *filesystem*:

* the bundle layout itself (``Something.vst3`` names the plugin), and
* ``Contents/moduleinfo.json``, which VST3 SDK 3.7.5 and later ship inside the
  bundle precisely so a host can enumerate plugins without executing them. It
  carries the factory vendor and the audio-module class names.

No plugin code runs during a scan, and nothing here imports pedalboard — the
GPL boundary described in :mod:`audio_studio.plugins.pedalboard_bridge` is not
even approached until the user loads one of the discovered plugins. What a scan
cannot learn without loading a binary (a bundle older than the ``moduleinfo``
convention has no vendor to report) is left empty rather than guessed at.

Two facilities exist for the cases where that is not enough:

*Caching.* :class:`ScanCache` remembers what a bundle described itself as, keyed
by the bundle's size and modification time, so a rescan of a system plugin
folder re-reads only what changed on disk.

*Process isolation.* :func:`probe_plugin_isolated` runs the probe in a
subprocess with a timeout, and ``discover_plugins(..., isolate=True)`` uses it
for every bundle. The in-process probe is the default because reading JSON
cannot hang or segfault; isolation is there for the day a probe backend that
does load binaries is added, and for a bundle on a filesystem that can wedge a
``stat``.

One descriptor is produced per bundle. Container bundles that expose several
audio-module classes are reported under the first one, because the loader path
(:func:`~audio_studio.plugins.adapter.create_plugin_effect`) currently opens a
bundle by path and lets the backend choose the plugin inside it; listing
sub-plugins that cannot then be selected would be a lie.

Examples
--------
>>> import json, tempfile
>>> from pathlib import Path
>>> root = Path(tempfile.mkdtemp())
>>> bundle = root / "GreatVerb.vst3" / "Contents"
>>> bundle.mkdir(parents=True)
>>> _ = (bundle / "moduleinfo.json").write_text(json.dumps(
...     {"Factory Info": {"Vendor": "Acme Audio"},
...      "Classes": [{"Category": "Audio Module Class", "Name": "Great Verb"}]}))
>>> found = discover_plugins([root])
>>> [(p.name, p.vendor) for p in found]
[('Great Verb', 'Acme Audio')]
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import subprocess
import sys
import tempfile
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

__all__ = [
    "BUNDLE_SUFFIX",
    "DEFAULT_MAX_DEPTH",
    "DEFAULT_PROBE_TIMEOUT",
    "PluginDescriptor",
    "PluginScanError",
    "ScanCache",
    "default_plugin_paths",
    "descriptor_id",
    "discover_plugins",
    "find_plugin_bundles",
    "probe_plugin",
    "probe_plugin_isolated",
    "read_bundle_metadata",
]

_log = logging.getLogger(__name__)

#: What a VST3 bundle (a directory on macOS/Linux, sometimes a plain DLL on
#: Windows) is called.
BUNDLE_SUFFIX = ".vst3"

#: How many directory levels below a scan root are searched. Level 1 is a
#: bundle sitting directly in the root. Plugin installers nest a couple of
#: levels deep (vendor folder, product folder); much beyond that a scan is
#: walking someone's home directory by accident.
DEFAULT_MAX_DEPTH = 4

#: Seconds an isolated probe may take before it is killed and skipped.
DEFAULT_PROBE_TIMEOUT = 10.0

#: Bumped when the cache file layout changes; an older file then misses whole.
CACHE_VERSION = 1

#: Where the ``moduleinfo.json`` written by VST3 SDK ≥ 3.7.5 lives, in the order
#: the SDK's own module loader looks for it.
_MODULE_INFO_PATHS = ("Contents/moduleinfo.json", "Contents/Resources/moduleinfo.json")

#: The ``Category`` a processor class carries in ``moduleinfo.json``. Bundles
#: also declare controller and helper classes, which are not plugins to list.
_AUDIO_MODULE_CATEGORY = "Audio Module Class"


class PluginScanError(RuntimeError):
    """A bundle could not be described (unreadable, timed out, or malformed)."""


@dataclass(frozen=True)
class PluginDescriptor:
    """What a scan can say about one plugin bundle.

    Attributes
    ----------
    id:
        Stable identifier derived from the bundle path — the same bundle keeps
        its id across scans and across runs, so a project or a cache can point
        at a plugin without embedding a display name that an update may change.
    name:
        Display name: the audio-module class name from ``moduleinfo.json`` when
        the bundle has one, otherwise the bundle's own file name.
    path:
        The ``.vst3`` bundle, as an absolute path.
    vendor:
        Factory vendor from ``moduleinfo.json``; empty when the bundle predates
        that convention, because a scan has no other way to learn it.
    """

    id: str
    name: str
    path: Path
    vendor: str = ""

    def to_json(self) -> dict[str, str]:
        """Serialisable form, used by the cache and the isolated probe."""
        return {
            "id": self.id,
            "name": self.name,
            "path": str(self.path),
            "vendor": self.vendor,
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> PluginDescriptor:
        """Rebuild a descriptor written by :meth:`to_json`.

        Raises
        ------
        PluginScanError
            When a required field is missing or unusable.
        """
        try:
            path = Path(str(data["path"]))
            return cls(
                id=str(data["id"]),
                name=str(data["name"]),
                path=path,
                vendor=str(data.get("vendor", "")),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise PluginScanError(f"invalid plugin descriptor: {exc}") from exc

    def __str__(self) -> str:
        return f"{self.name} — {self.vendor}" if self.vendor else self.name


def descriptor_id(path: str | Path) -> str:
    """Stable id for the bundle at ``path``.

    A short digest of the absolute path, prefixed with the bundle name so a
    human reading a project file or a log line can tell which plugin an id
    belongs to. Two bundles with the same name in different folders get
    different ids; moving a plugin changes its id, which is the honest outcome
    — the scan has nothing else to identify it by.
    """
    resolved = _absolute(Path(path))
    digest = hashlib.sha256(str(resolved).encode("utf-8")).hexdigest()[:8]
    return f"{resolved.stem}-{digest}"


def default_plugin_paths() -> tuple[Path, ...]:
    """The directories this platform installs VST3 plugins into.

    Only the ones that exist are returned, so the panel can offer a scan of
    "wherever plugins live here" without listing folders that do not.
    """
    home = Path.home()
    if sys.platform == "darwin":
        candidates = [
            home / "Library/Audio/Plug-Ins/VST3",
            Path("/Library/Audio/Plug-Ins/VST3"),
        ]
    elif os.name == "nt":
        program_files = os.environ.get("PROGRAMFILES", r"C:\Program Files")
        candidates = [
            Path(program_files) / "Common Files/VST3",
            home / "AppData/Local/Programs/Common/VST3",
        ]
    else:
        candidates = [
            home / ".vst3",
            Path("/usr/lib/vst3"),
            Path("/usr/local/lib/vst3"),
        ]
    return tuple(path for path in candidates if path.is_dir())


# ------------------------------------------------------------------ the walk


def find_plugin_bundles(
    paths: Iterable[str | Path], *, max_depth: int = DEFAULT_MAX_DEPTH
) -> list[Path]:
    """Every ``.vst3`` bundle under ``paths``, deduplicated and sorted.

    A path that is itself a bundle is returned as-is; a directory is walked to
    ``max_depth`` levels. The walk never descends *into* a bundle (a ``.vst3``
    contains binaries and resources, never another plugin), skips directories
    it may not read, and follows symlinks — plugin folders are routinely
    symlinked — while refusing to visit the same real directory twice, so a
    link pointing back at an ancestor cannot loop.
    """
    found: dict[Path, None] = {}
    visited: set[Path] = set()
    for raw in paths:
        root = Path(raw).expanduser()
        if _is_bundle(root):
            found[_absolute(root)] = None
            continue
        _walk(root, depth=1, max_depth=int(max_depth), found=found, visited=visited)
    return sorted(found)


def _walk(
    directory: Path,
    *,
    depth: int,
    max_depth: int,
    found: dict[Path, None],
    visited: set[Path],
) -> None:
    if depth > max_depth:
        return
    real = _absolute(directory)
    if real in visited:
        return
    visited.add(real)
    try:
        # Drained inside the context manager: the level's directory handle is
        # closed before recursing, so a deep tree does not hold one open per
        # level.
        with os.scandir(directory) as scan:
            entries = sorted(scan, key=lambda entry: entry.name)
    except OSError as exc:  # unreadable, vanished, or not a directory at all
        _log.debug("plugin scan skipped %s: %s", directory, exc)
        return

    for entry in entries:
        path = Path(entry.path)
        if path.name.lower().endswith(BUNDLE_SUFFIX):
            found[_absolute(path)] = None
            continue
        try:
            is_dir = entry.is_dir()
        except OSError:
            continue
        if is_dir:
            _walk(path, depth=depth + 1, max_depth=max_depth, found=found, visited=visited)


def _is_bundle(path: Path) -> bool:
    return path.name.lower().endswith(BUNDLE_SUFFIX) and path.exists()


def _absolute(path: Path) -> Path:
    try:
        return path.resolve()
    except OSError:
        return path.absolute()


# ---------------------------------------------------------------- the probe


def read_bundle_metadata(path: str | Path) -> tuple[str, str]:
    """``(name, vendor)`` read out of a bundle's ``moduleinfo.json``.

    Both are empty when the bundle has no ``moduleinfo.json``, when it cannot
    be read, or when what it holds is not the JSON object the VST3 SDK
    documents. A malformed sidecar is a bundle that describes itself badly, not
    a reason to fail a scan of a hundred others, so nothing here raises.
    """
    bundle = Path(path)
    for relative in _MODULE_INFO_PATHS:
        info_path = bundle / relative
        try:
            payload = json.loads(info_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        return _class_name(payload), _vendor(payload)
    return "", ""


def _class_name(payload: dict[str, Any]) -> str:
    classes = payload.get("Classes")
    if not isinstance(classes, list):
        return ""
    for entry in classes:
        if not isinstance(entry, dict):
            continue
        category = str(entry.get("Category", ""))
        name = str(entry.get("Name", "")).strip()
        if name and _AUDIO_MODULE_CATEGORY in category:
            return name
    return ""


def _vendor(payload: dict[str, Any]) -> str:
    factory = payload.get("Factory Info")
    if not isinstance(factory, dict):
        return ""
    return str(factory.get("Vendor", "")).strip()


def probe_plugin(path: str | Path) -> PluginDescriptor:
    """Describe one bundle, in this process.

    Reads only the filesystem, so it neither loads plugin code nor needs the
    ``plugins`` extra. It still raises rather than papering over a path that is
    not a plugin at all, because a caller asking about one specific bundle
    wants to know; :func:`discover_plugins` is the caller that shrugs.

    Raises
    ------
    PluginScanError
        When ``path`` does not name an existing ``.vst3`` bundle.
    """
    bundle = Path(path).expanduser()
    if not bundle.name.lower().endswith(BUNDLE_SUFFIX):
        raise PluginScanError(f"{str(bundle)!r} is not a {BUNDLE_SUFFIX} bundle")
    if not bundle.exists():
        raise PluginScanError(f"no plugin bundle at {str(bundle)!r}")
    name, vendor = read_bundle_metadata(bundle)
    absolute = _absolute(bundle)
    return PluginDescriptor(
        id=descriptor_id(absolute),
        name=name or absolute.stem,
        path=absolute,
        vendor=vendor,
    )


def probe_plugin_isolated(
    path: str | Path,
    *,
    timeout: float = DEFAULT_PROBE_TIMEOUT,
    executable: str | None = None,
) -> PluginDescriptor:
    """Describe one bundle in a subprocess that is killed if it overruns.

    The child runs this module's ``--probe`` entry point, so a probe that
    crashes or hangs costs one skipped plugin instead of the editor. It is the
    slower path by roughly an interpreter start-up per bundle, which is why
    :func:`discover_plugins` only takes it when asked.

    Raises
    ------
    PluginScanError
        When the child times out, exits non-zero, or does not print a
        descriptor.
    """
    command = [
        executable or sys.executable,
        "-m",
        "audio_studio.plugins.scanner",
        "--probe",
        str(path),
    ]
    try:
        completed = subprocess.run(  # noqa: S603 - fixed argv, no shell
            command,
            capture_output=True,
            text=True,
            timeout=float(timeout),
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise PluginScanError(
            f"probing {str(path)!r} timed out after {float(timeout):g}s"
        ) from exc
    except OSError as exc:
        raise PluginScanError(f"could not start a probe for {str(path)!r}: {exc}") from exc

    if completed.returncode != 0:
        detail = (completed.stderr or "").strip().splitlines()
        reason = detail[-1] if detail else f"exit code {completed.returncode}"
        raise PluginScanError(f"probing {str(path)!r} failed: {reason}")
    try:
        return PluginDescriptor.from_json(json.loads(completed.stdout))
    except (json.JSONDecodeError, TypeError) as exc:
        raise PluginScanError(f"probe of {str(path)!r} printed no descriptor: {exc}") from exc


# ---------------------------------------------------------------- the cache


@dataclass(frozen=True)
class _Fingerprint:
    """What makes a cached description stale: the bundle changed on disk."""

    mtime_ns: int
    size: int

    @classmethod
    def of(cls, path: Path) -> _Fingerprint:
        stat = path.stat()
        return cls(mtime_ns=int(stat.st_mtime_ns), size=int(stat.st_size))


class ScanCache:
    """Remembers descriptions of bundles that have not changed on disk.

    A system plugin folder holds hundreds of bundles and changes a handful of
    times a year, so rescanning it should cost a ``stat`` per bundle rather
    than a re-read of every ``moduleinfo.json``. Entries are keyed by absolute
    bundle path and validated against the bundle's modification time and size:
    an updated, replaced or removed plugin misses.

    The fingerprint is the bundle's own ``stat``, which on macOS and Linux is
    the ``.vst3`` *directory*. A plugin update replaces or rewrites the bundle
    and moves that timestamp; an edit buried inside an existing bundle that
    leaves the top-level directory untouched does not, so
    ``discover_plugins(..., force=True)`` exists for the user who knows better
    than the cache.

    The cache is strictly an optimisation. Every failure — unreadable file,
    corrupt JSON, read-only directory — degrades to a full scan rather than
    surfacing an error.

    Examples
    --------
    >>> cache = ScanCache()
    >>> cache.entry_count
    0
    """

    def __init__(
        self,
        entries: dict[str, dict[str, Any]] | None = None,
        *,
        path: Path | None = None,
    ) -> None:
        self.path = path
        self._entries: dict[str, dict[str, Any]] = dict(entries or {})
        self._dirty = False

    # -- construction ------------------------------------------------------

    @classmethod
    def load(cls, path: str | Path) -> ScanCache:
        """Read a cache file, or return an empty cache when it is unusable."""
        target = Path(path)
        try:
            payload = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            _log.debug("plugin scan cache %s unusable: %s", target, exc)
            return cls(path=target)
        if not isinstance(payload, dict) or payload.get("version") != CACHE_VERSION:
            return cls(path=target)
        entries = payload.get("entries")
        if not isinstance(entries, dict):
            return cls(path=target)
        return cls(
            {str(key): value for key, value in entries.items() if isinstance(value, dict)},
            path=target,
        )

    # -- lookups -----------------------------------------------------------

    @property
    def entry_count(self) -> int:
        """How many bundles are remembered, valid or not."""
        return len(self._entries)

    @property
    def is_dirty(self) -> bool:
        """Whether :meth:`save` would write something new."""
        return self._dirty

    def lookup(self, path: str | Path) -> PluginDescriptor | None:
        """The cached description of ``path``, or ``None`` on a miss.

        A stale entry is dropped on the way out, so re-probing a changed bundle
        also refreshes what the cache holds for it.
        """
        key = str(_absolute(Path(path)))
        entry = self._entries.get(key)
        if entry is None:
            return None
        try:
            current = _Fingerprint.of(Path(key))
        except OSError:
            self._drop(key)
            return None
        if (
            int(entry.get("mtime_ns", -1)) != current.mtime_ns
            or int(entry.get("size", -1)) != current.size
        ):
            self._drop(key)
            return None
        try:
            return PluginDescriptor.from_json(entry)
        except PluginScanError:
            self._drop(key)
            return None

    def store(self, descriptor: PluginDescriptor) -> None:
        """Remember ``descriptor`` against the bundle's current fingerprint."""
        key = str(_absolute(descriptor.path))
        try:
            fingerprint = _Fingerprint.of(Path(key))
        except OSError:  # it vanished between the probe and here
            return
        self._entries[key] = {
            **descriptor.to_json(),
            "mtime_ns": fingerprint.mtime_ns,
            "size": fingerprint.size,
        }
        self._dirty = True

    def prune(self) -> int:
        """Forget bundles that are no longer on disk; returns how many went.

        An uninstalled plugin is never visited by a later scan, so nothing
        would otherwise notice it is gone and the cache would grow forever.
        This costs one ``stat`` per remembered bundle.
        """
        gone = [key for key in self._entries if not Path(key).exists()]
        for key in gone:
            self._drop(key)
        return len(gone)

    def _drop(self, key: str) -> None:
        if self._entries.pop(key, None) is not None:
            self._dirty = True

    # -- persistence -------------------------------------------------------

    def save(self, path: str | Path | None = None) -> Path | None:
        """Write the cache atomically; ``None`` when that was not possible.

        A cache that cannot be written is not worth reporting: the caller
        already has the scan results it asked for.
        """
        target = Path(path) if path is not None else self.path
        if target is None:
            return None
        payload = json.dumps(
            {"version": CACHE_VERSION, "entries": self._entries},
            indent=2,
            sort_keys=True,
        )
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            handle, name = tempfile.mkstemp(
                dir=str(target.parent), prefix=f".{target.name}.", suffix=".tmp"
            )
            with os.fdopen(handle, "w", encoding="utf-8") as stream:
                stream.write(payload + "\n")
            os.replace(name, target)
        except OSError as exc:
            _log.debug("plugin scan cache write failed for %s: %s", target, exc)
            return None
        self.path = target
        self._dirty = False
        return target


# ------------------------------------------------------------------ the scan


def discover_plugins(
    paths: Iterable[str | Path] | None = None,
    *,
    max_depth: int = DEFAULT_MAX_DEPTH,
    cache: ScanCache | None = None,
    force: bool = False,
    isolate: bool = False,
    timeout: float = DEFAULT_PROBE_TIMEOUT,
    probe: Callable[[Path], PluginDescriptor] | None = None,
    on_error: Callable[[Path, Exception], None] | None = None,
) -> list[PluginDescriptor]:
    """Describe every VST3 bundle under ``paths``, skipping the ones that fail.

    Parameters
    ----------
    paths:
        Directories (or bundles) to search. Defaults to
        :func:`default_plugin_paths`.
    max_depth:
        Directory levels below each root to search; see
        :func:`find_plugin_bundles`.
    cache:
        A :class:`ScanCache` to read descriptions from and write them back to;
        bundles that have since left the disk are pruned from it. The caller
        owns saving it, so a UI can scan repeatedly and persist once.
    force:
        Re-probe every bundle even when the cache considers it unchanged.
    isolate:
        Probe each bundle in a subprocess with a ``timeout``, so a probe that
        crashes or hangs costs one plugin rather than the process.
    probe:
        Override the probe entirely — the seam tests use to stand in for a
        plugin binary.
    on_error:
        Called with ``(bundle, exception)`` for each bundle that could not be
        described. Without it, failures are logged and dropped: one broken
        plugin must not empty the list of the working ones.

    Returns
    -------
    list[PluginDescriptor]
        Sorted by display name (case-insensitively) and then by path, so the
        combo box a user reads does not reshuffle between scans.
    """
    roots = list(paths) if paths is not None else list(default_plugin_paths())
    if probe is None:
        probe = (
            (lambda bundle: probe_plugin_isolated(bundle, timeout=timeout))
            if isolate
            else probe_plugin
        )

    descriptors: list[PluginDescriptor] = []
    for bundle in find_plugin_bundles(roots, max_depth=max_depth):
        if cache is not None and not force:
            hit = cache.lookup(bundle)
            if hit is not None:
                descriptors.append(hit)
                continue
        try:
            descriptor = probe(bundle)
        except Exception as exc:  # noqa: BLE001 - a bad plugin is data, not a bug
            _log.debug("plugin scan skipped %s: %s", bundle, exc)
            if on_error is not None:
                on_error(bundle, exc)
            continue
        if cache is not None:
            cache.store(descriptor)
        descriptors.append(descriptor)
    if cache is not None:
        cache.prune()
    descriptors.sort(key=lambda item: (item.name.casefold(), str(item.path)))
    return descriptors


# ------------------------------------------------------------- command line


def _main(argv: Sequence[str] | None = None) -> int:
    """``python -m audio_studio.plugins.scanner`` — probe one bundle, or scan.

    ``--probe BUNDLE`` prints one descriptor as JSON and is what
    :func:`probe_plugin_isolated` runs in its subprocess; without it, the given
    directories (or the platform defaults) are scanned and listed one per line.
    """
    import argparse

    parser = argparse.ArgumentParser(
        prog="python -m audio_studio.plugins.scanner",
        description="List the VST3 plugin bundles installed on this machine.",
    )
    parser.add_argument("paths", nargs="*", help="directories to scan")
    parser.add_argument(
        "--probe", metavar="BUNDLE", help="describe one bundle as JSON and exit"
    )
    parser.add_argument(
        "--max-depth", type=int, default=DEFAULT_MAX_DEPTH, help="directory levels to search"
    )
    parser.add_argument(
        "--isolate", action="store_true", help="probe each bundle in a subprocess"
    )
    args = parser.parse_args(argv)

    if args.probe:
        try:
            descriptor = probe_plugin(args.probe)
        except PluginScanError as exc:
            print(exc, file=sys.stderr)
            return 1
        print(json.dumps(descriptor.to_json(), sort_keys=True))
        return 0

    found = discover_plugins(
        args.paths or None, max_depth=args.max_depth, isolate=args.isolate
    )
    for descriptor in found:
        print(f"{descriptor}\t{descriptor.path}")
    return 0 if found else 1


if __name__ == "__main__":  # pragma: no cover - exercised through a subprocess
    raise SystemExit(_main())
