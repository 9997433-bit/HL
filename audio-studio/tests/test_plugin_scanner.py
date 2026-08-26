"""VST3 discovery: the directory walk, bundle metadata, the cache, isolation.

No plugin binaries and no pedalboard: a ``.vst3`` bundle is a directory with a
``Contents/moduleinfo.json`` inside it, which is exactly what the scanner reads,
so every fixture here is built with :func:`make_bundle` from plain files.
"""

from __future__ import annotations

import ast
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

from audio_studio.plugins import scanner
from audio_studio.plugins.scanner import (
    DEFAULT_MAX_DEPTH,
    PluginDescriptor,
    PluginScanError,
    ScanCache,
    default_plugin_paths,
    descriptor_id,
    discover_plugins,
    find_plugin_bundles,
    probe_plugin,
    probe_plugin_isolated,
    read_bundle_metadata,
)


def make_bundle(
    root: Path,
    name: str,
    *,
    class_name: str | None = None,
    vendor: str | None = None,
    moduleinfo: bool = True,
    extra_classes: list[dict[str, str]] | None = None,
) -> Path:
    """A ``.vst3`` bundle on disk, optionally with the SDK's ``moduleinfo.json``."""
    bundle = root / f"{name}.vst3"
    contents = bundle / "Contents" / "x86_64-linux"
    contents.mkdir(parents=True, exist_ok=True)
    (contents / f"{name}.so").write_bytes(b"\x7fELF not really")
    if not moduleinfo:
        return bundle
    classes: list[dict[str, str]] = list(extra_classes or [])
    classes.append(
        {
            "CID": f"{name}-cid",
            "Category": "Audio Module Class",
            "Name": class_name if class_name is not None else name,
        }
    )
    payload = {
        "Name": name,
        "Version": "1.0.0",
        "Factory Info": {"Vendor": vendor if vendor is not None else "Acme Audio"},
        "Classes": classes,
    }
    (bundle / "Contents" / "moduleinfo.json").write_text(json.dumps(payload), encoding="utf-8")
    return bundle


@pytest.fixture()
def plugin_dir(tmp_path: Path) -> Path:
    """Two bundles at the top level and one nested a vendor folder deep."""
    root = tmp_path / "vst3"
    root.mkdir()
    make_bundle(root, "GreatVerb", class_name="Great Verb", vendor="Acme Audio")
    make_bundle(root, "TinyComp", class_name="Tiny Comp", vendor="Bolt Audio")
    make_bundle(root / "Vendor" / "Suite", "DeepEQ", class_name="Deep EQ")
    return root


# -- the walk ----------------------------------------------------------------


class TestFindPluginBundles:
    def test_it_finds_bundles_at_every_depth(self, plugin_dir: Path) -> None:
        """Sorted by path, so a nested vendor folder lands after the top level."""
        found = find_plugin_bundles([plugin_dir])
        assert [path.name for path in found] == [
            "GreatVerb.vst3",
            "TinyComp.vst3",
            "DeepEQ.vst3",
        ]

    def test_the_depth_limit_stops_the_walk(self, plugin_dir: Path) -> None:
        shallow = find_plugin_bundles([plugin_dir], max_depth=1)
        assert [path.name for path in shallow] == ["GreatVerb.vst3", "TinyComp.vst3"]
        assert find_plugin_bundles([plugin_dir], max_depth=0) == []

    def test_it_does_not_descend_into_a_bundle(self, tmp_path: Path) -> None:
        """A ``.vst3`` holds binaries and resources, never another plugin."""
        outer = make_bundle(tmp_path, "Outer")
        make_bundle(outer / "Contents", "Inner")

        assert find_plugin_bundles([tmp_path]) == [outer.resolve()]

    def test_a_bundle_path_is_accepted_directly(self, plugin_dir: Path) -> None:
        bundle = plugin_dir / "GreatVerb.vst3"
        assert find_plugin_bundles([bundle]) == [bundle.resolve()]

    def test_non_plugin_files_are_ignored(self, tmp_path: Path) -> None:
        (tmp_path / "readme.txt").write_text("not a plugin", encoding="utf-8")
        (tmp_path / "Legacy.dll").write_bytes(b"MZ")
        (tmp_path / "presets").mkdir()

        assert find_plugin_bundles([tmp_path]) == []

    def test_duplicate_roots_yield_one_entry(self, plugin_dir: Path) -> None:
        found = find_plugin_bundles([plugin_dir, plugin_dir, plugin_dir / "Vendor"])
        assert len(found) == len(set(found)) == 3

    def test_a_missing_root_is_not_an_error(self, tmp_path: Path) -> None:
        assert find_plugin_bundles([tmp_path / "nowhere"]) == []

    def test_a_symlink_loop_terminates(self, tmp_path: Path) -> None:
        root = tmp_path / "vst3"
        (root / "sub").mkdir(parents=True)
        make_bundle(root / "sub", "Looped")
        try:
            (root / "sub" / "back").symlink_to(root, target_is_directory=True)
        except (OSError, NotImplementedError):  # pragma: no cover - platform-dependent
            pytest.skip("symlinks are not available here")

        assert [path.name for path in find_plugin_bundles([root])] == ["Looped.vst3"]

    def test_a_windows_style_dll_bundle_counts(self, tmp_path: Path) -> None:
        """On Windows a ``.vst3`` can be a plain file rather than a directory."""
        flat = tmp_path / "FlatPlugin.vst3"
        flat.write_bytes(b"MZ")

        assert find_plugin_bundles([tmp_path]) == [flat.resolve()]


# -- bundle metadata ---------------------------------------------------------


class TestBundleMetadata:
    def test_it_reads_the_class_name_and_vendor(self, tmp_path: Path) -> None:
        bundle = make_bundle(tmp_path, "GreatVerb", class_name="Great Verb", vendor="Acme")
        assert read_bundle_metadata(bundle) == ("Great Verb", "Acme")

    def test_only_audio_module_classes_name_the_plugin(self, tmp_path: Path) -> None:
        bundle = make_bundle(
            tmp_path,
            "GreatVerb",
            class_name="Great Verb",
            extra_classes=[{"Category": "Component Controller Class", "Name": "Controller"}],
        )
        assert read_bundle_metadata(bundle)[0] == "Great Verb"

    def test_a_bundle_without_moduleinfo_says_nothing(self, tmp_path: Path) -> None:
        bundle = make_bundle(tmp_path, "Legacy", moduleinfo=False)
        assert read_bundle_metadata(bundle) == ("", "")

    def test_malformed_moduleinfo_is_not_an_error(self, tmp_path: Path) -> None:
        bundle = make_bundle(tmp_path, "Broken")
        (bundle / "Contents" / "moduleinfo.json").write_text("{not json", encoding="utf-8")

        assert read_bundle_metadata(bundle) == ("", "")


class TestProbePlugin:
    def test_it_describes_a_bundle(self, plugin_dir: Path) -> None:
        descriptor = probe_plugin(plugin_dir / "GreatVerb.vst3")

        assert descriptor.name == "Great Verb"
        assert descriptor.vendor == "Acme Audio"
        assert descriptor.path == (plugin_dir / "GreatVerb.vst3").resolve()
        assert descriptor.id == descriptor_id(plugin_dir / "GreatVerb.vst3")
        assert str(descriptor) == "Great Verb — Acme Audio"

    def test_the_file_name_is_the_fallback(self, tmp_path: Path) -> None:
        descriptor = probe_plugin(make_bundle(tmp_path, "Legacy", moduleinfo=False))
        assert descriptor.name == "Legacy"
        assert descriptor.vendor == ""
        assert str(descriptor) == "Legacy"

    def test_a_missing_bundle_raises(self, tmp_path: Path) -> None:
        with pytest.raises(PluginScanError, match="no plugin bundle"):
            probe_plugin(tmp_path / "Ghost.vst3")

    def test_something_that_is_not_a_bundle_raises(self, tmp_path: Path) -> None:
        with pytest.raises(PluginScanError, match="not a .vst3 bundle"):
            probe_plugin(tmp_path)

    def test_ids_are_stable_per_path_and_differ_between_bundles(
        self, plugin_dir: Path
    ) -> None:
        first = descriptor_id(plugin_dir / "GreatVerb.vst3")
        assert first == descriptor_id(plugin_dir / "GreatVerb.vst3")
        assert first.startswith("GreatVerb-")
        assert first != descriptor_id(plugin_dir / "TinyComp.vst3")


# -- the scan ----------------------------------------------------------------


class TestDiscoverPlugins:
    def test_it_returns_descriptors_sorted_by_name(self, plugin_dir: Path) -> None:
        found = discover_plugins([plugin_dir])
        assert [item.name for item in found] == ["Deep EQ", "Great Verb", "Tiny Comp"]

    def test_a_crashy_plugin_is_skipped_not_fatal(self, plugin_dir: Path) -> None:
        """A probe that blows up costs one plugin, never the whole list."""
        failures: list[tuple[Path, Exception]] = []

        def probe(bundle: Path) -> PluginDescriptor:
            if bundle.name == "TinyComp.vst3":
                raise RuntimeError("segfault in the plugin factory")
            return probe_plugin(bundle)

        found = discover_plugins(
            [plugin_dir], probe=probe, on_error=lambda path, exc: failures.append((path, exc))
        )

        assert [item.name for item in found] == ["Deep EQ", "Great Verb"]
        assert [path.name for path, _exc in failures] == ["TinyComp.vst3"]

    def test_failures_are_silent_without_an_error_hook(self, plugin_dir: Path) -> None:
        def probe(bundle: Path) -> PluginDescriptor:
            raise OSError("bundle is on a dead network mount")

        assert discover_plugins([plugin_dir], probe=probe) == []

    def test_the_depth_limit_is_passed_through(self, plugin_dir: Path) -> None:
        found = discover_plugins([plugin_dir], max_depth=1)
        assert [item.name for item in found] == ["Great Verb", "Tiny Comp"]

    def test_defaults_to_the_platform_paths(self, monkeypatch: pytest.MonkeyPatch) -> None:
        seen: list[list[str | Path]] = []
        monkeypatch.setattr(scanner, "default_plugin_paths", lambda: (Path("/opt/vst3"),))
        monkeypatch.setattr(
            scanner,
            "find_plugin_bundles",
            lambda paths, **_kwargs: seen.append(list(paths)) or [],
        )

        assert discover_plugins() == []
        assert seen == [[Path("/opt/vst3")]]

    def test_default_plugin_paths_only_lists_directories_that_exist(self) -> None:
        assert all(path.is_dir() for path in default_plugin_paths())


# -- the cache ---------------------------------------------------------------


class TestScanCache:
    def test_a_second_scan_reuses_what_did_not_change(self, plugin_dir: Path) -> None:
        cache = ScanCache()
        probed: list[Path] = []

        def probe(bundle: Path) -> PluginDescriptor:
            probed.append(bundle)
            return probe_plugin(bundle)

        first = discover_plugins([plugin_dir], cache=cache, probe=probe)
        second = discover_plugins([plugin_dir], cache=cache, probe=probe)

        assert len(probed) == 3  # the second scan probed nothing
        assert [item.name for item in second] == [item.name for item in first]
        assert cache.entry_count == 3

    def test_a_changed_bundle_is_re_probed(self, plugin_dir: Path) -> None:
        cache = ScanCache()
        discover_plugins([plugin_dir], cache=cache)

        bundle = plugin_dir / "TinyComp.vst3"
        _touch_later(bundle)
        probed: list[Path] = []

        def probe(path: Path) -> PluginDescriptor:
            probed.append(path)
            return probe_plugin(path)

        discover_plugins([plugin_dir], cache=cache, probe=probe)

        assert probed == [bundle.resolve()]

    def test_force_re_probes_everything(self, plugin_dir: Path) -> None:
        cache = ScanCache()
        discover_plugins([plugin_dir], cache=cache)
        probed: list[Path] = []

        discover_plugins(
            [plugin_dir],
            cache=cache,
            force=True,
            probe=lambda path: probed.append(path) or probe_plugin(path),
        )

        assert len(probed) == 3

    def test_an_uninstalled_plugin_leaves_the_cache(self, plugin_dir: Path) -> None:
        cache = ScanCache()
        discover_plugins([plugin_dir], cache=cache)
        shutil.rmtree(plugin_dir / "TinyComp.vst3")

        found = discover_plugins([plugin_dir], cache=cache)

        assert [item.name for item in found] == ["Deep EQ", "Great Verb"]
        assert cache.entry_count == 2

    def test_it_round_trips_through_a_file(self, plugin_dir: Path, tmp_path: Path) -> None:
        path = tmp_path / "cache" / "plugins.json"
        cache = ScanCache(path=path)
        discover_plugins([plugin_dir], cache=cache)

        assert cache.is_dirty
        assert cache.save() == path
        assert not cache.is_dirty

        reopened = ScanCache.load(path)
        probed: list[Path] = []
        found = discover_plugins(
            [plugin_dir],
            cache=reopened,
            probe=lambda bundle: probed.append(bundle) or probe_plugin(bundle),
        )

        assert probed == []
        assert [item.name for item in found] == ["Deep EQ", "Great Verb", "Tiny Comp"]

    def test_a_corrupt_cache_file_is_a_miss_not_a_crash(self, tmp_path: Path) -> None:
        path = tmp_path / "plugins.json"
        path.write_text("]not json[", encoding="utf-8")

        cache = ScanCache.load(path)

        assert cache.entry_count == 0
        assert cache.lookup(tmp_path / "Anything.vst3") is None

    def test_a_cache_from_a_future_version_is_ignored(self, tmp_path: Path) -> None:
        path = tmp_path / "plugins.json"
        path.write_text(json.dumps({"version": 99, "entries": {"x": {}}}), encoding="utf-8")

        assert ScanCache.load(path).entry_count == 0

    def test_a_cache_that_cannot_be_written_is_not_an_error(self, tmp_path: Path) -> None:
        cache = ScanCache()
        assert cache.save() is None  # nowhere to write to

        blocked = tmp_path / "file.txt"
        blocked.write_text("in the way", encoding="utf-8")
        assert cache.save(blocked / "cache.json") is None

    def test_lookup_misses_a_bundle_it_has_never_seen(self, plugin_dir: Path) -> None:
        assert ScanCache().lookup(plugin_dir / "GreatVerb.vst3") is None


def _touch_later(path: Path) -> None:
    """Move a bundle's modification time forward past the cached fingerprint."""
    stat = path.stat()
    later = stat.st_mtime + 10.0
    os.utime(path, (later, later))
    assert path.stat().st_mtime_ns != stat.st_mtime_ns


# -- descriptors -------------------------------------------------------------


class TestPluginDescriptor:
    def test_json_round_trip(self, plugin_dir: Path) -> None:
        descriptor = probe_plugin(plugin_dir / "GreatVerb.vst3")
        assert PluginDescriptor.from_json(descriptor.to_json()) == descriptor

    def test_an_entry_without_a_path_is_rejected(self) -> None:
        with pytest.raises(PluginScanError, match="invalid plugin descriptor"):
            PluginDescriptor.from_json({"id": "x", "name": "y"})


# -- process isolation -------------------------------------------------------


class TestIsolatedProbe:
    def test_it_describes_a_bundle_in_a_subprocess(self, plugin_dir: Path) -> None:
        descriptor = probe_plugin_isolated(plugin_dir / "GreatVerb.vst3", timeout=60)

        assert descriptor == probe_plugin(plugin_dir / "GreatVerb.vst3")

    def test_a_scan_can_run_every_probe_isolated(self, plugin_dir: Path) -> None:
        found = discover_plugins([plugin_dir], isolate=True, timeout=60)
        assert [item.name for item in found] == ["Deep EQ", "Great Verb", "Tiny Comp"]

    def test_a_probe_that_fails_is_reported(self, tmp_path: Path) -> None:
        with pytest.raises(PluginScanError, match="failed"):
            probe_plugin_isolated(tmp_path / "Ghost.vst3", timeout=60)

    def test_a_probe_that_hangs_is_killed(self, plugin_dir: Path) -> None:
        """The point of isolation: a wedged plugin costs a timeout, not the app."""
        sleeper = _sleeper_script(plugin_dir.parent)

        with pytest.raises(PluginScanError, match="timed out"):
            probe_plugin_isolated(
                plugin_dir / "GreatVerb.vst3", timeout=0.5, executable=str(sleeper)
            )

    def test_a_hung_probe_only_costs_that_plugin(self, plugin_dir: Path) -> None:
        def probe(bundle: Path) -> PluginDescriptor:
            if bundle.name == "GreatVerb.vst3":
                raise PluginScanError("probing timed out after 0.5s")
            return probe_plugin(bundle)

        found = discover_plugins([plugin_dir], probe=probe)

        assert [item.name for item in found] == ["Deep EQ", "Tiny Comp"]

    def test_a_probe_executable_that_does_not_exist_is_reported(
        self, plugin_dir: Path
    ) -> None:
        with pytest.raises(PluginScanError, match="could not start"):
            probe_plugin_isolated(
                plugin_dir / "GreatVerb.vst3", executable="/nonexistent/python"
            )


def _sleeper_script(directory: Path) -> Path:
    """An "interpreter" that ignores its arguments and hangs, for the timeout test."""
    script = directory / "sleeper.sh"
    script.write_text("#!/bin/sh\nsleep 30\n", encoding="utf-8")
    script.chmod(0o755)
    return script


# -- the command line --------------------------------------------------------


class TestCommandLine:
    def test_probe_prints_one_descriptor(self, plugin_dir: Path) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "audio_studio.plugins.scanner",
                "--probe",
                str(plugin_dir / "GreatVerb.vst3"),
            ],
            capture_output=True,
            text=True,
            timeout=60,
            check=True,
        )

        payload = json.loads(completed.stdout)
        assert payload["name"] == "Great Verb"
        assert payload["vendor"] == "Acme Audio"

    def test_probing_a_missing_bundle_exits_non_zero(self, tmp_path: Path) -> None:
        assert scanner._main(["--probe", str(tmp_path / "Ghost.vst3")]) == 1

    def test_listing_a_folder_prints_every_plugin(
        self, plugin_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert scanner._main([str(plugin_dir)]) == 0

        lines = capsys.readouterr().out.strip().splitlines()
        assert len(lines) == 3
        assert "Great Verb — Acme Audio" in lines[1]

    def test_an_empty_folder_exits_non_zero(self, tmp_path: Path) -> None:
        assert scanner._main([str(tmp_path)]) == 1


# -- the GPL boundary --------------------------------------------------------


def test_scanning_works_without_the_plugins_extra(
    plugin_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A scan reads the filesystem; the GPL backend is not part of it."""
    monkeypatch.setitem(sys.modules, "pedalboard", None)

    assert len(discover_plugins([plugin_dir])) == 3


def test_the_scanner_module_never_imports_pedalboard() -> None:
    """The GPL boundary, checked against the source rather than the docstrings."""
    tree = ast.parse(Path(scanner.__file__).read_text(encoding="utf-8"))
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }

    assert "pedalboard" not in imported


def test_a_scan_of_a_large_tree_is_bounded_by_the_depth_limit(tmp_path: Path) -> None:
    """The default depth keeps a mistyped root from walking a whole home folder."""
    deep = tmp_path
    for level in range(DEFAULT_MAX_DEPTH + 3):
        deep = deep / f"level{level}"
    deep.mkdir(parents=True)
    make_bundle(deep, "TooDeep")

    started = time.monotonic()
    assert discover_plugins([tmp_path]) == []
    assert time.monotonic() - started < 5.0
