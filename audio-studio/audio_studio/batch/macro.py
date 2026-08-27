"""Portable JSON macros made from an :class:`~audio_studio.core.EditSession`.

A macro stores the currently applied command branch, not PCM or undo snapshots.
Frame positions are deliberately exact and the source sample rate is part of the
schema; replay refuses a different rate instead of silently moving edit points.
Cut/paste sequences are supported while their paste still refers to the cut
clipboard. A paste of copied or external audio is rejected because embedding
source samples in a small, reusable JSON macro would not be portable.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..core.edit_session import (
    FADE_SHAPES,
    CutCommand,
    DeleteCommand,
    EditCommand,
    EditError,
    EditSession,
    FadeCommand,
    GainCommand,
    InsertSilenceCommand,
    PasteCommand,
    ReverseCommand,
    SilenceCommand,
    SpectralEditCommand,
    TrimCommand,
)
from ..core.types import AudioBuffer, TimeRange

SCHEMA_VERSION = 1

__all__ = [
    "SCHEMA_VERSION",
    "EditMacro",
    "MacroError",
    "deserialize_macro",
    "load_macro",
    "save_macro",
    "serialize_session",
]


class MacroError(ValueError):
    """A macro cannot be serialized, parsed, or replayed."""


def _range_json(rng: TimeRange) -> dict[str, int]:
    return {"start": rng.start, "end": rng.end}


def _command_json(
    command: EditCommand, clipboard: object | None
) -> tuple[dict[str, Any], object | None]:
    if isinstance(command, CutCommand):
        return {"type": "cut", **_range_json(command.range)}, command.removed
    if isinstance(command, DeleteCommand):
        return {"type": "delete", **_range_json(command.range)}, clipboard
    if isinstance(command, PasteCommand):
        if clipboard is None or command.payload is not clipboard:
            raise MacroError(
                "cannot serialize a paste of copied or external audio; "
                "only paste from an earlier cut in the macro is portable"
            )
        data: dict[str, Any] = {"type": "paste", "at": command.at}
        if command.replacing is not None:
            data["replacing"] = _range_json(command.replacing)
        return data, clipboard
    if isinstance(command, InsertSilenceCommand):
        return {
            "type": "insert_silence",
            "at": command.at,
            "n_frames": command.n_frames,
        }, clipboard
    if isinstance(command, SilenceCommand):
        return {"type": "silence", **_range_json(command.range)}, clipboard
    if isinstance(command, GainCommand):
        if not math.isfinite(command.gain_db):
            raise MacroError("gain command has a non-finite gain_db")
        return {
            "type": "gain",
            **_range_json(command.range),
            "gain_db": command.gain_db,
        }, clipboard
    if isinstance(command, FadeCommand):
        return {
            "type": "fade",
            **_range_json(command.range),
            "direction": command.direction,
            "shape": command.shape,
        }, clipboard
    if isinstance(command, ReverseCommand):
        return {"type": "reverse", **_range_json(command.range)}, clipboard
    if isinstance(command, SpectralEditCommand):
        data = {
            "type": "spectral_edit",
            **_range_json(command.range),
            "low_hz": command.band.low_hz,
            "high_hz": command.band.high_hz,
            "fft_size": command.fft_size,
        }
        if command.removes:
            data["remove"] = True
        elif math.isfinite(command.gain_db):
            data["gain_db"] = command.gain_db
        else:
            raise MacroError("spectral edit has a non-finite gain_db")
        return data, clipboard
    if isinstance(command, TrimCommand):
        return {"type": "trim", **_range_json(command.range)}, clipboard
    raise MacroError(f"unsupported edit command {type(command).__name__}")


def _integer(value: Any, field: str, *, positive: bool = False) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise MacroError(f"{field} must be an integer")
    if value < (1 if positive else 0):
        qualifier = "positive" if positive else "non-negative"
        raise MacroError(f"{field} must be {qualifier}")
    return value


def _number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise MacroError(f"{field} must be a number")
    result = float(value)
    if not math.isfinite(result):
        raise MacroError(f"{field} must be finite")
    return result


def _range_from_json(data: Mapping[str, Any], prefix: str = "") -> TimeRange:
    start = _integer(data.get("start"), f"{prefix}start")
    end = _integer(data.get("end"), f"{prefix}end")
    try:
        return TimeRange(start, end)
    except ValueError as exc:
        raise MacroError(str(exc)) from exc


def _normalise_command(raw: Any, index: int) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise MacroError(f"commands[{index}] must be an object")
    kind = raw.get("type")
    if not isinstance(kind, str):
        raise MacroError(f"commands[{index}].type must be a string")

    data: dict[str, Any] = {"type": kind}
    if kind in {"cut", "delete", "silence", "gain", "fade", "reverse", "spectral_edit", "trim"}:
        data.update(_range_json(_range_from_json(raw, f"commands[{index}].")))

    if kind == "paste":
        data["at"] = _integer(raw.get("at"), f"commands[{index}].at")
        replacing = raw.get("replacing")
        if replacing is not None:
            if not isinstance(replacing, Mapping):
                raise MacroError(f"commands[{index}].replacing must be an object")
            data["replacing"] = _range_json(
                _range_from_json(replacing, f"commands[{index}].replacing.")
            )
    elif kind == "insert_silence":
        data["at"] = _integer(raw.get("at"), f"commands[{index}].at")
        data["n_frames"] = _integer(
            raw.get("n_frames"), f"commands[{index}].n_frames", positive=True
        )
    elif kind == "gain":
        data["gain_db"] = _number(raw.get("gain_db"), f"commands[{index}].gain_db")
    elif kind == "fade":
        direction = raw.get("direction")
        shape = raw.get("shape")
        if direction not in {"in", "out"}:
            raise MacroError(f"commands[{index}].direction must be 'in' or 'out'")
        if shape not in FADE_SHAPES:
            raise MacroError(f"commands[{index}].shape must be one of {FADE_SHAPES}")
        data.update(direction=direction, shape=shape)
    elif kind == "spectral_edit":
        data["low_hz"] = _number(raw.get("low_hz"), f"commands[{index}].low_hz")
        data["high_hz"] = _number(raw.get("high_hz"), f"commands[{index}].high_hz")
        data["fft_size"] = _integer(
            raw.get("fft_size"), f"commands[{index}].fft_size", positive=True
        )
        remove = raw.get("remove", False)
        if not isinstance(remove, bool):
            raise MacroError(f"commands[{index}].remove must be a boolean")
        if remove:
            data["remove"] = True
        else:
            data["gain_db"] = _number(
                raw.get("gain_db"), f"commands[{index}].gain_db"
            )
    elif kind not in {"cut", "delete", "paste", "silence", "reverse", "trim"}:
        raise MacroError(f"commands[{index}] has unknown type {kind!r}")
    return data


@dataclass(frozen=True, slots=True)
class EditMacro:
    """A validated, replayable edit-command sequence."""

    sample_rate: int
    commands: tuple[dict[str, Any], ...]

    def __post_init__(self) -> None:
        rate = _integer(self.sample_rate, "sample_rate", positive=True)
        commands = tuple(
            _normalise_command(command, index) for index, command in enumerate(self.commands)
        )
        object.__setattr__(self, "sample_rate", rate)
        object.__setattr__(self, "commands", commands)

    @classmethod
    def from_session(cls, session: EditSession) -> EditMacro:
        """Capture the applied branch of ``session``'s undo history."""
        serialized: list[dict[str, Any]] = []
        clipboard: object | None = None
        for command in session.undo_stack.applied_commands:
            data, clipboard = _command_json(command, clipboard)
            serialized.append(data)
        return cls(session.sample_rate, tuple(serialized))

    @classmethod
    def from_json(cls, data: Mapping[str, Any]) -> EditMacro:
        """Validate and construct a macro from decoded JSON data."""
        if not isinstance(data, Mapping):
            raise MacroError("macro root must be an object")
        if data.get("schema_version") != SCHEMA_VERSION:
            raise MacroError(
                f"unsupported schema_version {data.get('schema_version')!r}; "
                f"expected {SCHEMA_VERSION}"
            )
        commands = data.get("commands")
        if not isinstance(commands, list):
            raise MacroError("commands must be an array")
        return cls(
            _integer(data.get("sample_rate"), "sample_rate", positive=True),
            tuple(commands),
        )

    def to_json(self) -> dict[str, Any]:
        """Return only JSON-native values in the stable schema-v1 shape."""
        return {
            "schema_version": SCHEMA_VERSION,
            "sample_rate": self.sample_rate,
            "commands": [dict(command) for command in self.commands],
        }

    @classmethod
    def load(cls, path: str | Path) -> EditMacro:
        source = Path(path)
        try:
            data = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise MacroError(f"cannot read macro {source}: {exc}") from exc
        if not isinstance(data, Mapping):
            raise MacroError(f"macro {source} root must be an object")
        return cls.from_json(data)

    def save(self, path: str | Path) -> Path:
        destination = Path(path)
        try:
            destination.write_text(
                json.dumps(self.to_json(), indent=2, allow_nan=False) + "\n",
                encoding="utf-8",
            )
        except OSError as exc:
            raise MacroError(f"cannot write macro {destination}: {exc}") from exc
        return destination

    def apply_to_session(self, session: EditSession) -> EditSession:
        """Replay the macro in order and return the mutated session."""
        if session.sample_rate != self.sample_rate:
            raise MacroError(
                f"macro sample rate is {self.sample_rate} Hz, "
                f"input is {session.sample_rate} Hz"
            )
        for index, command in enumerate(self.commands):
            try:
                _apply_command(session, command)
            except (EditError, ValueError) as exc:
                raise MacroError(f"command {index + 1} ({command['type']}) failed: {exc}") from exc
        return session

    def apply(self, buffer: AudioBuffer) -> AudioBuffer:
        """Apply this macro as a batch-pipeline operation."""
        session = EditSession.from_buffer(buffer)
        self.apply_to_session(session)
        return session.to_buffer()

    def describe(self) -> str:
        noun = "command" if len(self.commands) == 1 else "commands"
        return f"replay edit macro ({len(self.commands)} {noun})"


def _apply_command(session: EditSession, command: Mapping[str, Any]) -> None:
    kind = str(command["type"])
    rng = (
        _range_from_json(command)
        if kind in {"cut", "delete", "silence", "gain", "fade", "reverse", "spectral_edit", "trim"}
        else None
    )
    if kind == "cut":
        assert rng is not None
        session.cut(rng)
    elif kind == "delete":
        assert rng is not None
        session.delete(rng)
    elif kind == "paste":
        replacing = command.get("replacing")
        replace_range = (
            _range_from_json(replacing) if isinstance(replacing, Mapping) else None
        )
        session.paste(int(command["at"]), replacing=replace_range)
    elif kind == "insert_silence":
        session.insert_silence(int(command["at"]), int(command["n_frames"]))
    elif kind == "silence":
        assert rng is not None
        session.silence(rng)
    elif kind == "gain":
        assert rng is not None
        session.apply_gain(rng, float(command["gain_db"]))
    elif kind == "fade":
        assert rng is not None
        fade = session.fade_in if command["direction"] == "in" else session.fade_out
        fade(rng, shape=str(command["shape"]))
    elif kind == "reverse":
        assert rng is not None
        session.reverse(rng)
    elif kind == "spectral_edit":
        assert rng is not None
        gain_db = -math.inf if command.get("remove") else float(command["gain_db"])
        session.spectral_edit(
            rng,
            float(command["low_hz"]),
            float(command["high_hz"]),
            gain_db,
            fft_size=int(command["fft_size"]),
        )
    elif kind == "trim":
        assert rng is not None
        session.trim(rng)
    else:  # Commands are validated at construction; keep this boundary defensive.
        raise MacroError(f"unknown command type {kind!r}")


def serialize_session(session: EditSession) -> dict[str, Any]:
    """Serialize the applied command sequence into JSON-native values."""
    return EditMacro.from_session(session).to_json()


def deserialize_macro(data: Mapping[str, Any]) -> EditMacro:
    return EditMacro.from_json(data)


def save_macro(session: EditSession, path: str | Path) -> Path:
    return EditMacro.from_session(session).save(path)


def load_macro(path: str | Path) -> EditMacro:
    return EditMacro.load(path)
