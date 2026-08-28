"""Project tree and metadata helpers for the desktop dashboard."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

__all__ = ["list_directory", "project_info", "resolve_under_root"]

IGNORED_NAMES = frozenset({".git", "__pycache__", ".pytest_cache", ".venv", "node_modules"})


def resolve_under_root(root: Path, relative: str) -> Path:
    """Resolve ``relative`` under ``root`` and reject path traversal."""
    candidate = (root / relative).resolve()
    root_resolved = root.resolve()
    if not str(candidate).startswith(str(root_resolved)):
        raise ValueError("path escapes the project root")
    return candidate


def list_directory(root: Path, relative: str = ".") -> dict[str, Any]:
    """Return a shallow directory listing relative to the project root."""
    path = resolve_under_root(root, relative or ".")
    if path.is_file():
        return {
            "type": "file",
            "path": relative.replace("\\", "/"),
            "name": path.name,
        }
    if not path.is_dir():
        raise FileNotFoundError(relative)
    entries: list[dict[str, str]] = []
    for child in sorted(path.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower())):
        if child.name in IGNORED_NAMES or child.name.startswith("."):
            continue
        rel = child.relative_to(root.resolve()).as_posix()
        entries.append(
            {
                "name": child.name,
                "path": rel,
                "type": "directory" if child.is_dir() else "file",
            }
        )
    return {
        "type": "directory",
        "path": (relative or ".").replace("\\", "/"),
        "entries": entries,
    }


def project_info(root: Path) -> dict[str, Any]:
    """Load ``project.yaml`` when present and summarize the workspace."""
    info: dict[str, Any] = {
        "root": str(root.resolve()),
        "name": root.name,
        "has_project_file": False,
        "paths": {
            "models": "models",
            "measurements": "measurements",
            "reports": "reports",
        },
        "workflow": [],
    }
    project_file = root / "project.yaml"
    if not project_file.is_file():
        return info
    raw = yaml.safe_load(project_file.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return info
    info["has_project_file"] = True
    info["name"] = str(raw.get("name") or info["name"])
    info["description"] = raw.get("description")
    paths = raw.get("paths")
    if isinstance(paths, dict):
        info["paths"] = {str(key): str(value) for key, value in paths.items()}
    workflow = raw.get("workflow")
    if isinstance(workflow, list):
        info["workflow"] = workflow
    return info


def read_json_under_root(root: Path, relative: str) -> dict[str, Any]:
    path = resolve_under_root(root, relative)
    if not path.is_file():
        raise FileNotFoundError(relative)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("the document must be a JSON object")
    return payload
