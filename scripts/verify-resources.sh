#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

command -v python3 >/dev/null 2>&1 || {
  printf 'ERROR: python3 is required to validate resource files.\n' >&2
  exit 1
}

python3 - "$ROOT_DIR" <<'PY'
from __future__ import annotations

import json
import sys
import wave
from pathlib import Path
from typing import Any


root = Path(sys.argv[1])
errors: list[str] = []


def check(condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def load_json(relative_path: str) -> Any:
    path = root / relative_path
    check(path.is_file(), f"missing JSON file: {relative_path}")
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        errors.append(f"invalid JSON in {relative_path}: {exc}")
        return {}


def require_text(item: dict[str, Any], fields: tuple[str, ...], context: str) -> None:
    for field in fields:
        check(
            isinstance(item.get(field), str) and bool(item[field].strip()),
            f"{context}: {field!r} must be a non-empty string",
        )


# Educational data
hanzi_doc = load_json("shared/data/common-hanzi.json")
characters = hanzi_doc.get("characters", [])
check(hanzi_doc.get("license") == "CC0-1.0", "common-hanzi.json must declare CC0-1.0")
check(isinstance(characters, list), "common-hanzi.json characters must be an array")
if isinstance(characters, list):
    check(len(characters) >= 50, f"expected at least 50 hanzi entries, found {len(characters)}")
    seen_characters: set[str] = set()
    for index, item in enumerate(characters):
        context = f"common-hanzi.json characters[{index}]"
        check(isinstance(item, dict), f"{context} must be an object")
        if not isinstance(item, dict):
            continue
        require_text(item, ("character", "pinyin", "meaning", "example"), context)
        character = item.get("character")
        check(isinstance(character, str) and len(character) == 1, f"{context}: character must be one code point")
        if isinstance(character, str):
            check(character not in seen_characters, f"duplicate hanzi entry: {character}")
            seen_characters.add(character)

math_doc = load_json("shared/data/math-problems.json")
problems = math_doc.get("problems", [])
check(math_doc.get("license") == "CC0-1.0", "math-problems.json must declare CC0-1.0")
check(isinstance(problems, list), "math-problems.json problems must be an array")
if isinstance(problems, list):
    check(len(problems) >= 40, f"expected at least 40 math problems, found {len(problems)}")
    seen_ids: set[str] = set()
    represented_types: set[str] = set()
    for index, item in enumerate(problems):
        context = f"math-problems.json problems[{index}]"
        check(isinstance(item, dict), f"{context} must be an object")
        if not isinstance(item, dict):
            continue
        require_text(item, ("id", "type", "prompt", "hint", "explanation"), context)
        problem_id = item.get("id")
        if isinstance(problem_id, str):
            check(problem_id not in seen_ids, f"duplicate math problem id: {problem_id}")
            seen_ids.add(problem_id)
        problem_type = item.get("type")
        if isinstance(problem_type, str):
            represented_types.add(problem_type)
        check(item.get("difficulty") in (1, 2, 3), f"{context}: difficulty must be 1, 2, or 3")
        answer = item.get("answer")
        check(
            isinstance(answer, (int, float, str)) and not isinstance(answer, bool),
            f"{context}: answer must be a number or string",
        )
    required_types = {
        "counting",
        "comparison",
        "addition",
        "subtraction",
        "multiplication",
        "division",
        "pattern",
        "geometry",
        "word-problem",
    }
    check(
        required_types <= represented_types,
        f"math problem categories missing: {sorted(required_types - represented_types)}",
    )

idiom_doc = load_json("shared/data/idioms.json")
idioms = idiom_doc.get("idioms", [])
check(idiom_doc.get("license") == "CC0-1.0", "idioms.json must declare CC0-1.0")
check(isinstance(idioms, list), "idioms.json idioms must be an array")
if isinstance(idioms, list):
    check(len(idioms) >= 20, f"expected at least 20 idioms, found {len(idioms)}")
    seen_idioms: set[str] = set()
    for index, item in enumerate(idioms):
        context = f"idioms.json idioms[{index}]"
        check(isinstance(item, dict), f"{context} must be an object")
        if not isinstance(item, dict):
            continue
        require_text(item, ("idiom", "pinyin", "meaning", "example"), context)
        phrase = item.get("idiom")
        if isinstance(phrase, str):
            check(phrase not in seen_idioms, f"duplicate idiom entry: {phrase}")
            seen_idioms.add(phrase)
        tags = item.get("tags")
        check(
            isinstance(tags, list) and bool(tags) and all(isinstance(tag, str) and tag for tag in tags),
            f"{context}: tags must be a non-empty string array",
        )

# Downloaded and generated assets
required_docs = [
    ".agent_workspace/open-source-resources.md",
    "shared/assets/README.md",
    "shared/assets/openmoji/LICENSE.txt",
    "shared/assets/hanzi-writer-data/ARPHICPL.TXT",
    "shared/assets/fonts/OFL-NotoSansSC.txt",
]
for relative_path in required_docs:
    path = root / relative_path
    check(path.is_file() and path.stat().st_size > 0, f"missing or empty required notice: {relative_path}")

license_needles = {
    "shared/assets/openmoji/LICENSE.txt": "Attribution-ShareAlike 4.0 International",
    "shared/assets/hanzi-writer-data/ARPHICPL.TXT": "ARPHIC PUBLIC LICENSE",
    "shared/assets/fonts/OFL-NotoSansSC.txt": "SIL OPEN FONT LICENSE Version 1.1",
}
for relative_path, needle in license_needles.items():
    path = root / relative_path
    if path.is_file():
        try:
            check(needle in path.read_text(encoding="utf-8"), f"{relative_path} lacks expected license heading")
        except (OSError, UnicodeError) as exc:
            errors.append(f"cannot read {relative_path}: {exc}")

icon_names = ("apple", "target", "open-book", "numbers", "abacus", "star")
for name in icon_names:
    relative_path = f"shared/assets/openmoji/{name}.svg"
    path = root / relative_path
    check(path.is_file() and path.stat().st_size > 0, f"missing or empty SVG: {relative_path}")
    if path.is_file():
        try:
            text = path.read_text(encoding="utf-8")
            check("<svg" in text and "</svg>" in text, f"malformed SVG wrapper: {relative_path}")
        except (OSError, UnicodeError) as exc:
            errors.append(f"cannot read {relative_path}: {exc}")

for character in ("人", "日", "山"):
    relative_path = f"shared/assets/hanzi-writer-data/{character}.json"
    data = load_json(relative_path)
    strokes = data.get("strokes", [])
    medians = data.get("medians", [])
    check(isinstance(strokes, list) and bool(strokes), f"{relative_path}: strokes must be non-empty")
    check(isinstance(medians, list) and len(medians) == len(strokes), f"{relative_path}: medians must match strokes")

for name in ("tap", "success", "try-again"):
    relative_path = f"shared/assets/audio/{name}.wav"
    path = root / relative_path
    check(path.is_file() and path.stat().st_size > 44, f"missing or empty WAV: {relative_path}")
    if path.is_file():
        try:
            with wave.open(str(path), "rb") as audio:
                check(audio.getnchannels() in (1, 2), f"{relative_path}: unsupported channel count")
                check(audio.getsampwidth() == 2, f"{relative_path}: expected 16-bit samples")
                check(audio.getframerate() == 44100, f"{relative_path}: expected 44.1 kHz sample rate")
                check(audio.getnframes() > 0, f"{relative_path}: contains no frames")
        except (wave.Error, OSError) as exc:
            errors.append(f"invalid WAV in {relative_path}: {exc}")

lottie = load_json("shared/assets/lottie/celebration.json")
check(isinstance(lottie.get("v"), str), "Lottie file must have a version")
check(isinstance(lottie.get("fr"), (int, float)) and lottie.get("fr", 0) > 0, "Lottie frame rate must be positive")
check(
    isinstance(lottie.get("ip"), (int, float))
    and isinstance(lottie.get("op"), (int, float))
    and lottie.get("op", 0) > lottie.get("ip", 0),
    "Lottie output frame must be after input frame",
)
check(isinstance(lottie.get("layers"), list) and bool(lottie.get("layers")), "Lottie layers must be non-empty")

if errors:
    print(f"Resource verification failed with {len(errors)} issue(s):", file=sys.stderr)
    for error in errors:
        print(f"  - {error}", file=sys.stderr)
    raise SystemExit(1)

print(
    "Resource verification passed: "
    f"{len(characters)} hanzi, {len(problems)} math problems, {len(idioms)} idioms, "
    f"{len(icon_names)} SVG icons, 3 stroke fixtures, 3 WAV effects, and 1 Lottie animation."
)
PY
