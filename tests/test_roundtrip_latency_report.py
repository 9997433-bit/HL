"""Schema and honesty checks for the SOTA C4 round-trip latency evidence.

Two things are checked here, and they are different kinds of check. The first
is that the published report says what a C4 report has to say: the buffer, the
rate, the measured round trip, the controls that make it believable, and the
plain statement that no converter was in the loop. The second is that the
probe's own arithmetic is right — the detector is exercised against synthetic
audio with a delay this file chose, so a regression in the correlation would
fail here rather than quietly move the published number.
"""

from __future__ import annotations

import itertools
import json
import math
from pathlib import Path

import numpy as np
import pytest

from benchmarks import roundtrip_latency_probe as probe

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = REPOSITORY_ROOT / ".agent_workspace/round3/roundtrip-latency-report.json"
SAMPLE_RATE = 48_000


def _load_report() -> dict:
    assert REPORT_PATH.is_file(), (
        "run `python3 benchmarks/roundtrip_latency_probe.py` on a host with a "
        "PulseAudio loopback to publish the C4 report"
    )
    return json.loads(REPORT_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def report() -> dict:
    return _load_report()


# ------------------------------------------------------------------ the report


def test_report_identifies_itself(report: dict) -> None:
    assert report["schema_version"] == 1
    assert report["harness"] == "benchmarks/roundtrip_latency_probe.py"
    assert report["checklist_item"] == "C4"
    assert report["evidence"] == "hardware-loopback"
    assert {"python", "platform", "sounddevice", "portaudio", "pulseaudio_server"} <= set(
        report["environment"]
    )


def test_report_states_what_the_loopback_left_out(report: dict) -> None:
    """"hardware-loopback" must not be left to imply converters that are absent."""
    assert isinstance(report["physical_dac_adc"], bool)
    assert report["loopback_path"]
    limitation = report["limitation"]
    assert limitation.strip()
    if not report["physical_dac_adc"]:
        assert "DAC" in limitation and "ADC" in limitation
        assert report["loopback"]["sink"] and report["loopback"]["source"]


def test_measured_round_trip_clears_the_c4_budget(report: dict) -> None:
    assert report["buffer_frames"] == 128
    assert report["sample_rate"] == SAMPLE_RATE
    assert report["threshold_ms"] == 15.0
    assert report["roundtrip_latency_ms"] < report["threshold_ms"]
    assert report["margin_ms"] == pytest.approx(
        report["threshold_ms"] - report["roundtrip_latency_ms"], abs=1e-3
    )
    assert report["status"] == "pass"


def test_headline_is_the_worst_measurement_not_a_flattering_one(report: dict) -> None:
    latency = report["latency"]
    steady = [item["latency_ms"] for item in report["samples"] if not item["settling"]]
    assert steady, "the report carries no steady-state samples"
    assert report["roundtrip_latency_ms"] == pytest.approx(max(steady), abs=1e-3)
    assert report["roundtrip_latency_ms"] == pytest.approx(latency["max_ms"], abs=1e-3)
    assert latency["min_ms"] <= latency["median_ms"] <= latency["max_ms"]
    assert latency["measurements"] == report["measurements"]
    assert report["measurements"] >= 20


def test_every_measurement_is_a_real_detection(report: dict) -> None:
    """A round trip is only a round trip if the signal actually came back."""
    for sample in report["samples"]:
        assert sample["delay_frames"] > 0
        assert sample["peak_to_sidelobe"] >= probe.MIN_PEAK_TO_SIDELOBE
        # The chirp is emitted at half scale; anything much quieter coming back
        # would mean the correlation locked onto something other than it.
        assert sample["amplitude_in"] > 0.4 * probe.CHIRP_AMPLITUDE
        assert sample["latency_ms"] == pytest.approx(
            sample["delay_frames"] / SAMPLE_RATE * 1000.0, abs=1e-3
        )


def test_the_kept_sessions_glitched_nowhere(report: dict) -> None:
    assert report["xruns"] == 0
    for result in report["results"]:
        assert result["status"] == "pass"
        assert result["xruns"] == 0
        assert not result["discarded_emissions"]
        assert result["measured"]["max_ms"] < report["threshold_ms"]
        sessions = result["sessions"]
        assert sessions["completed"] == sessions["requested"]
        assert sessions["attempted"] == sessions["completed"] + sessions["discarded_for_xruns"]


def test_any_session_thrown_out_is_published_with_its_numbers(report: dict) -> None:
    """Retrying a glitched stream is only honest if the discarded one is shown."""
    discarded = report["sessions_discarded_for_xruns"]
    published = [
        entry for result in report["results"] for entry in result["glitched_sessions"]
    ]
    assert discarded == len(published)
    for entry in published:
        assert entry["xruns"] > 0
        assert entry["reason"].strip()
        # Including what it measured, so a reader can see what was left out.
        assert entry["measured"]


def test_controls_are_present_and_passing(report: dict) -> None:
    controls = report["controls"]
    assert {"silence", "injected_delay", "latency_sensitivity", "wall_clock"} <= set(controls)
    assert all(control["status"] == "pass" for control in controls.values())

    # Nothing was found in a session that emitted nothing.
    assert controls["silence"]["highest_peak_to_sidelobe"] < probe.MIN_PEAK_TO_SIDELOBE
    # A known offset came back exactly, not approximately.
    assert controls["injected_delay"]["max_error_frames"] <= 1
    assert (
        controls["injected_delay"]["expected_delay_frames"]
        == controls["injected_delay"]["baseline_delay_frames"] + probe.CONTROL_DELAY_FRAMES
    )
    # Widening the buffers lengthened the measured trip, so the number is
    # coming from the audio path rather than from somewhere else.
    assert controls["latency_sensitivity"]["growth_ms"] >= probe.MIN_SENSITIVITY_GROWTH_MS
    # And the frames never ran ahead of a clock that knows nothing about audio.
    assert controls["wall_clock"]["most_negative_difference_ms"] >= -controls["wall_clock"][
        "tolerance_ms"
    ]


def test_transient_measurements_are_reported_rather_than_dropped(report: dict) -> None:
    """The cold start and the warm-up chirps are excluded from the headline, not hidden."""
    cold_start = report["cold_start"]
    assert cold_start["measurements"] > 0
    assert cold_start["max_ms"] >= cold_start["median_ms"] > 0.0
    assert isinstance(cold_start["within_budget"], bool)

    settling = report["startup_settling"]
    assert settling["measurements"] > 0
    assert any(sample["settling"] for sample in report["samples"])
    assert settling["measurements"] == sum(
        1 for sample in report["samples"] if sample["settling"]
    )


def test_both_the_transport_and_the_engine_render_path_were_measured(report: dict) -> None:
    slo_ids = {result["slo_id"] for result in report["results"]}
    assert {"roundtrip-direct-duplex", "roundtrip-engine-render"} <= slo_ids


def test_configured_buffering_is_itself_under_the_budget(report: dict) -> None:
    """The observed trip cannot exceed what PortAudio configured, so that ceiling matters.

    With it under 15 ms too, the result does not depend on the buffers happening
    to be favourably aligned when a stream starts.
    """
    ceilings = report["portaudio_configured_roundtrip_ms"]
    assert ceilings
    assert max(ceilings) < report["threshold_ms"]


# ------------------------------------------------------------- the arithmetic


def test_detector_finds_a_chirp_at_a_delay_this_test_chose() -> None:
    """The correlation has to recover an offset the test knows, to the frame."""
    chirp = probe.chirp(SAMPLE_RATE)
    rng = np.random.default_rng(4)
    signal = rng.normal(0.0, 1e-4, size=8_000).astype(np.float32)
    offset = 1_237
    signal[offset : offset + chirp.size] += chirp

    found = probe.detect(signal, chirp)
    assert found.index == offset
    assert found.confident


def test_detector_refuses_to_find_a_chirp_that_is_not_there() -> None:
    chirp = probe.chirp(SAMPLE_RATE)
    rng = np.random.default_rng(5)
    noise = rng.normal(0.0, 1e-3, size=8_000).astype(np.float32)

    found = probe.detect(noise, chirp)
    assert not found.confident


def test_measurement_recovers_a_delay_planted_in_a_synthetic_session() -> None:
    """End-to-end arithmetic: build a session with a known delay, read it back.

    Nothing here touches an audio device. The point is that the code turning
    captured audio into a latency reports the delay that was put into it, so a
    published number can be attributed to the loopback rather than to a bug in
    this file's neighbour.
    """
    chirp = probe.chirp(SAMPLE_RATE)
    buffer_frames = 128
    delay = 259
    emissions = [3_000, 15_000, 27_000]
    span = 40_000
    played = np.zeros((span, 2), dtype=np.float32)
    for offset in emissions:
        played[offset : offset + chirp.size, :] += chirp[:, None]
    captured = np.roll(played, delay, axis=0)
    blocks = span // buffer_frames

    session = probe.Session(
        played=played,
        captured=captured,
        # One block period per callback, which is what an unglitched stream does.
        callback_time=np.arange(blocks) * (buffer_frames / SAMPLE_RATE),
        blocks=blocks,
        emission_frames=emissions,
        settling_frames=[],
        status_flags=[],
        xruns=0,
        reported_latency=(0.005, 0.008),
        reported_roundtrip_ms=None,
        scenario="synthetic",
        buffer_frames=buffer_frames,
    )
    measurements, discarded = probe.measure_session(session, chirp, SAMPLE_RATE, 0)

    assert not discarded
    assert len(measurements) == len(emissions)
    assert {item.delay_frames for item in measurements} == {delay}
    assert all(
        math.isclose(item.latency_ms, delay / SAMPLE_RATE * 1000.0, abs_tol=1e-3)
        for item in measurements
    )
    # The wall clock derived from the callback grid has to agree with the frames.
    assert all(
        item.wall_clock_ms == pytest.approx(item.latency_ms, abs=3.0) for item in measurements
    )


def test_emission_schedule_keeps_chirps_off_block_boundaries() -> None:
    settling, measured, total = probe._emission_schedule(SAMPLE_RATE, 128, 6, 2.0)

    assert settling and measured
    assert all(offset + 12_000 < 2.0 * SAMPLE_RATE for offset in settling)
    assert all(offset >= 2.0 * SAMPLE_RATE for offset in measured)
    assert total > measured[-1]
    # Every measured emission lands mid-block, so a delay that had been rounded
    # to whole buffers could not hide behind a block-aligned chirp.
    assert all(offset % 128 for offset in measured)
    # And they are far enough apart that no search window can catch its neighbour.
    gaps = [second - first for first, second in itertools.pairwise(measured)]
    assert min(gaps) > (probe.SEARCH_BEFORE_SECONDS + probe.SEARCH_AFTER_SECONDS) * SAMPLE_RATE
