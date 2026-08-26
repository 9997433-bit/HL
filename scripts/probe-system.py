#!/usr/bin/env python3
"""Probe the host for Python and native audio-development capabilities."""

from __future__ import annotations

import argparse
import ctypes.util
import importlib
import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
RUNTIME_LIBRARIES = {
    "numpy": "numpy",
    "scipy": "scipy",
    "sounddevice": "sounddevice",
    "soundfile": "soundfile",
    "librosa": "librosa",
    "platformdirs": "platformdirs",
}
DEVELOPMENT_LIBRARIES = {
    "pytest": "pytest",
    "pytest-cov": "pytest_cov",
    "mypy": "mypy",
    "ruff": "ruff",
    "build": "build",
}


def command_output(command: list[str], timeout: float = 5.0) -> str | None:
    """Return the first output line from a successful command."""
    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    output = result.stdout.strip() or result.stderr.strip()
    return output.splitlines()[0] if output else None


def pkg_config_version(package: str) -> str | None:
    if shutil.which("pkg-config") is None:
        return None
    return command_output(["pkg-config", "--modversion", package])


def linux_distribution() -> dict[str, str] | None:
    os_release = Path("/etc/os-release")
    if platform.system() != "Linux" or not os_release.is_file():
        return None

    values: dict[str, str] = {}
    try:
        for line in os_release.read_text(encoding="utf-8").splitlines():
            if "=" not in line or line.startswith("#"):
                continue
            key, value = line.split("=", 1)
            values[key] = value.strip().strip("\"'")
    except OSError:
        return None
    return {
        "id": values.get("ID", "unknown"),
        "name": values.get("PRETTY_NAME", values.get("NAME", "unknown")),
        "version": values.get("VERSION_ID", "unknown"),
    }


def is_container() -> bool:
    if Path("/.dockerenv").exists() or os.environ.get("container"):
        return True
    try:
        cgroup = Path("/proc/1/cgroup").read_text(encoding="utf-8").lower()
    except OSError:
        return False
    return any(marker in cgroup for marker in ("docker", "containerd", "kubepods"))


def probe_os() -> dict[str, Any]:
    release = platform.release()
    return {
        "system": platform.system(),
        "release": release,
        "version": platform.version(),
        "machine": platform.machine(),
        "platform": platform.platform(),
        "distribution": linux_distribution(),
        "is_wsl": platform.system() == "Linux"
        and ("microsoft" in release.lower() or bool(os.environ.get("WSL_DISTRO_NAME"))),
        "is_container": is_container(),
    }


def probe_python() -> dict[str, Any]:
    return {
        "version": platform.python_version(),
        "implementation": platform.python_implementation(),
        "executable": sys.executable,
        "prefix": sys.prefix,
        "base_prefix": sys.base_prefix,
        "in_virtual_environment": sys.prefix != sys.base_prefix,
        "supported": sys.version_info >= (3, 11) and sys.version_info < (3, 14),
    }


def probe_library(
    distribution: str,
    module: str,
    *,
    category: str,
    required: bool,
) -> dict[str, Any]:
    try:
        version = importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        version = None

    error: str | None = None
    try:
        importlib.import_module(module)
        importable = True
    except Exception as exc:  # A failed native extension is a probe result.
        importable = False
        error = f"{type(exc).__name__}: {exc}"

    return {
        "distribution": distribution,
        "module": module,
        "category": category,
        "required": required,
        "installed": version is not None,
        "importable": importable,
        "version": version,
        "error": error,
    }


def probe_libraries() -> dict[str, dict[str, Any]]:
    libraries = {
        name: probe_library(
            name,
            module,
            category="runtime",
            required=True,
        )
        for name, module in RUNTIME_LIBRARIES.items()
    }
    libraries.update(
        {
            name: probe_library(
                name,
                module,
                category="development",
                required=False,
            )
            for name, module in DEVELOPMENT_LIBRARIES.items()
        }
    )
    return libraries


def probe_devices() -> dict[str, Any]:
    result: dict[str, Any] = {
        "query_succeeded": False,
        "count": 0,
        "input_count": 0,
        "output_count": 0,
        "default_input": None,
        "default_output": None,
        "devices": [],
        "error": None,
    }
    try:
        sounddevice = importlib.import_module("sounddevice")
        host_apis = sounddevice.query_hostapis()
        devices = sounddevice.query_devices()
        default_input, default_output = sounddevice.default.device

        normalized = []
        for index, device in enumerate(devices):
            host_api_index = int(device["hostapi"])
            host_api_name = (
                host_apis[host_api_index]["name"]
                if 0 <= host_api_index < len(host_apis)
                else "unknown"
            )
            normalized.append(
                {
                    "index": index,
                    "name": str(device["name"]),
                    "host_api": str(host_api_name),
                    "max_input_channels": int(device["max_input_channels"]),
                    "max_output_channels": int(device["max_output_channels"]),
                    "default_samplerate": float(device["default_samplerate"]),
                }
            )

        result.update(
            {
                "query_succeeded": True,
                "count": len(normalized),
                "input_count": sum(
                    device["max_input_channels"] > 0 for device in normalized
                ),
                "output_count": sum(
                    device["max_output_channels"] > 0 for device in normalized
                ),
                "default_input": int(default_input)
                if default_input is not None and default_input >= 0
                else None,
                "default_output": int(default_output)
                if default_output is not None and default_output >= 0
                else None,
                "devices": normalized,
            }
        )
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def probe_audio() -> dict[str, Any]:
    system = platform.system()
    portaudio_library = ctypes.util.find_library("portaudio")
    alsa_library = ctypes.util.find_library("asound") if system == "Linux" else None
    proc_asound = Path("/proc/asound")

    return {
        "portaudio": {
            "library_available": portaudio_library is not None,
            "library": portaudio_library,
            "pkg_config_version": pkg_config_version("portaudio-2.0"),
        },
        "alsa": {
            "applicable": system == "Linux",
            "library_available": alsa_library is not None,
            "library": alsa_library,
            "pkg_config_version": pkg_config_version("alsa"),
            "proc_asound_available": proc_asound.is_dir(),
        },
        "devices": probe_devices(),
    }


def probe_ffmpeg() -> dict[str, Any]:
    path = shutil.which("ffmpeg")
    return {
        "available": path is not None,
        "path": path,
        "version": command_output([path, "-version"]) if path else None,
        "ffprobe_available": shutil.which("ffprobe") is not None,
    }


def assess(
    os_info: dict[str, Any],
    python: dict[str, Any],
    libraries: dict[str, dict[str, Any]],
    audio: dict[str, Any],
    ffmpeg: dict[str, Any],
) -> tuple[str, list[dict[str, str]], list[dict[str, str]]]:
    missing: list[dict[str, str]] = []
    risks: list[dict[str, str]] = []

    if not python["supported"]:
        missing.append(
            {
                "name": "python",
                "kind": "runtime",
                "detail": "Python 3.11-3.13 is required.",
            }
        )

    for name, state in libraries.items():
        if not state["importable"]:
            missing.append(
                {
                    "name": name,
                    "kind": state["category"],
                    "detail": state["error"] or "Package is not installed.",
                }
            )

    if not audio["portaudio"]["library_available"]:
        missing.append(
            {
                "name": "PortAudio",
                "kind": "native",
                "detail": "Install the PortAudio runtime and development headers.",
            }
        )
    if os_info["system"] == "Linux" and not audio["alsa"]["library_available"]:
        missing.append(
            {
                "name": "ALSA",
                "kind": "native",
                "detail": "Install libasound2 and libasound2-dev.",
            }
        )
    if not ffmpeg["available"]:
        missing.append(
            {
                "name": "ffmpeg",
                "kind": "tool",
                "detail": "Install ffmpeg and ensure it is on PATH.",
            }
        )

    if audio["devices"]["count"] == 0:
        risks.append(
            {
                "code": "no_audio_devices",
                "detail": "No audio devices are visible; live capture/playback cannot be tested.",
            }
        )
    if os_info["is_container"]:
        risks.append(
            {
                "code": "container_audio_isolation",
                "detail": "Containers do not receive host audio devices or audio-server sockets by default.",
            }
        )
    if os_info["is_wsl"]:
        risks.append(
            {
                "code": "wsl_audio_bridge",
                "detail": "WSL audio depends on WSLg/PulseAudio bridging and adds latency.",
            }
        )

    blocking = any(item["kind"] != "development" for item in missing)
    status = "not_ready" if blocking else "degraded" if missing or risks else "ready"
    return status, missing, risks


def build_report() -> dict[str, Any]:
    os_info = probe_os()
    python = probe_python()
    libraries = probe_libraries()
    audio = probe_audio()
    ffmpeg = probe_ffmpeg()
    status, missing, risks = assess(os_info, python, libraries, audio, ffmpeg)
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "development_ready": status == "ready",
        "os": os_info,
        "python": python,
        "libraries": libraries,
        "audio": audio,
        "tools": {"ffmpeg": ffmpeg},
        "missing_dependencies": missing,
        "platform_risks": risks,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        help="Write JSON to this path instead of standard output.",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Emit compact JSON.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero unless the probe status is ready.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report()
    payload = json.dumps(
        report,
        indent=None if args.compact else 2,
        sort_keys=False,
    )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(f"{payload}\n", encoding="utf-8")
    else:
        print(payload)
    return int(args.strict and report["status"] != "ready")


if __name__ == "__main__":
    raise SystemExit(main())
