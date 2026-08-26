"""GC preparation and restoration around real-time playback."""

from __future__ import annotations

import numpy as np
import pytest

from audio_studio.core import rt_discipline
from audio_studio.core.engine import AudioEngine
from audio_studio.core.output import DEFAULT_BLOCK_SIZE, NullOutput
from audio_studio.core.sample_source import MemorySampleSource
from audio_studio.core.types import AudioBuffer


def test_default_block_is_about_five_milliseconds_at_48khz() -> None:
    assert DEFAULT_BLOCK_SIZE == 256
    assert DEFAULT_BLOCK_SIZE / 48_000 == pytest.approx(0.005333, abs=1e-6)


def test_enter_collects_before_freezing(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    monkeypatch.delenv(rt_discipline.RT_GC_ENV_VAR, raising=False)
    monkeypatch.setattr(rt_discipline.gc, "collect", lambda: calls.append("collect"))
    monkeypatch.setattr(rt_discipline.gc, "freeze", lambda: calls.append("freeze"))

    rt_discipline.enter_realtime_mode()

    assert calls == ["collect", "freeze"]


def test_leave_unfreezes_the_permanent_generation(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    monkeypatch.delenv(rt_discipline.RT_GC_ENV_VAR, raising=False)
    monkeypatch.setattr(rt_discipline.gc, "unfreeze", lambda: calls.append("unfreeze"))

    rt_discipline.leave_realtime_mode()

    assert calls == ["unfreeze"]


def test_gc_discipline_can_be_disabled_by_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    monkeypatch.setenv(rt_discipline.RT_GC_ENV_VAR, "0")
    monkeypatch.setattr(rt_discipline.gc, "collect", lambda: calls.append("collect"))
    monkeypatch.setattr(rt_discipline.gc, "freeze", lambda: calls.append("freeze"))
    monkeypatch.setattr(rt_discipline.gc, "unfreeze", lambda: calls.append("unfreeze"))

    rt_discipline.enter_realtime_mode()
    rt_discipline.leave_realtime_mode()

    assert calls == []


def test_engine_enters_once_and_leaves_once_on_shutdown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(rt_discipline, "enter_realtime_mode", lambda: calls.append("enter"))
    monkeypatch.setattr(rt_discipline, "leave_realtime_mode", lambda: calls.append("leave"))
    source = MemorySampleSource(
        AudioBuffer(np.ones((4096, 1), dtype=np.float32), sample_rate=48_000)
    )
    engine = AudioEngine(NullOutput(realtime=False), ring_blocks=4)
    engine.set_source(source)

    engine.play()
    engine.stop()
    engine.play()
    engine.shutdown()
    engine.shutdown()

    assert calls == ["enter", "leave"]


def test_shutdown_before_playback_does_not_unfreeze(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(rt_discipline, "leave_realtime_mode", lambda: calls.append("leave"))

    AudioEngine(NullOutput(realtime=False)).shutdown()

    assert calls == []
