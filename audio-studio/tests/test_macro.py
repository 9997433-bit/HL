"""EditSession JSON macro serialization and batch CLI replay."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from audio_studio.batch import cli
from audio_studio.batch.macro import EditMacro, MacroError, load_macro, save_macro
from audio_studio.core.edit_session import EditSession
from audio_studio.core.loader import load_audio, save_audio
from audio_studio.core.types import AudioBuffer, TimeRange

SAMPLE_RATE = 48_000


def ramp(n_frames: int = 32) -> np.ndarray:
    mono = np.linspace(-0.8, 0.8, n_frames, dtype=np.float32)
    return mono[:, np.newaxis]


def test_session_macro_round_trip_reproduces_the_edited_document(tmp_path: Path) -> None:
    original = ramp()
    session = EditSession.from_array(original, SAMPLE_RATE)
    session.apply_gain(TimeRange(2, 18), -6.0)
    session.fade_out(TimeRange(4, 12), shape="cosine")
    session.reverse(TimeRange(0, 20))
    session.insert_silence(3, 2)
    session.delete(TimeRange(22, 24))
    expected = session.to_buffer().data

    path = save_macro(session, tmp_path / "edit.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    assert payload["sample_rate"] == SAMPLE_RATE
    assert [item["type"] for item in payload["commands"]] == [
        "gain",
        "fade",
        "reverse",
        "insert_silence",
        "delete",
    ]

    rendered = load_macro(path).apply(AudioBuffer(original, SAMPLE_RATE))
    np.testing.assert_array_equal(rendered.data, expected)


def test_macro_serializes_only_the_current_applied_history_branch() -> None:
    session = EditSession.from_array(ramp(), SAMPLE_RATE)
    session.silence(TimeRange(0, 2))
    session.reverse(TimeRange(2, 5))
    assert session.undo()

    macro = EditMacro.from_session(session)

    assert [command["type"] for command in macro.commands] == ["silence"]


def test_cut_and_paste_replay_uses_each_input_files_own_audio() -> None:
    original = ramp(12)
    session = EditSession.from_array(original, SAMPLE_RATE)
    session.cut(TimeRange(2, 5))
    session.paste(8)
    expected = session.to_buffer().data

    macro = EditMacro.from_session(session)
    assert [command["type"] for command in macro.commands] == ["cut", "paste"]
    rendered = macro.apply(AudioBuffer(original, SAMPLE_RATE))

    np.testing.assert_array_equal(rendered.data, expected)


def test_paste_of_copied_audio_is_rejected_instead_of_embedding_pcm() -> None:
    session = EditSession.from_array(ramp(), SAMPLE_RATE)
    session.copy(TimeRange(0, 4))
    session.paste(8)

    with pytest.raises(MacroError, match="copied or external audio"):
        EditMacro.from_session(session)


def test_invalid_or_wrong_rate_macro_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text('{"schema_version": 99, "commands": []}', encoding="utf-8")
    with pytest.raises(MacroError, match="schema_version"):
        EditMacro.load(path)

    macro = EditMacro(SAMPLE_RATE, ({"type": "reverse", "start": 0, "end": 2},))
    with pytest.raises(MacroError, match="sample rate"):
        macro.apply(AudioBuffer(ramp(), 44_100))


def test_batch_cli_replays_macro_before_export(tmp_path: Path) -> None:
    source = tmp_path / "in"
    source.mkdir()
    original = ramp(16)
    save_audio(source / "take.wav", AudioBuffer(original, SAMPLE_RATE), subtype="FLOAT")

    session = EditSession.from_array(original, SAMPLE_RATE)
    session.reverse(TimeRange(2, 10))
    macro_path = save_macro(session, tmp_path / "reverse.json")

    code = cli.main(
        [
            "--input",
            str(source / "*.wav"),
            "--output",
            str(tmp_path / "out"),
            "--macro",
            str(macro_path),
            "--subtype",
            "FLOAT",
        ]
    )

    assert code == 0
    rendered = load_audio(tmp_path / "out" / "take.wav").buffer.data
    np.testing.assert_array_equal(rendered, session.to_buffer().data)


def test_batch_cli_reports_an_unreadable_macro(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = cli.main(
        [
            "--input",
            str(tmp_path / "*.wav"),
            "--output",
            str(tmp_path / "out"),
            "--macro",
            str(tmp_path / "missing.json"),
        ]
    )
    assert code == 2
    assert "cannot read macro" in capsys.readouterr().err
