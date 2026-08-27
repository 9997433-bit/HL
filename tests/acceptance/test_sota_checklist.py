"""Executable coverage of the fable Round 3 SOTA checklist.

The source audit has 29 top-level bullets.  Its first bullet combines EBU
Tech 3341 loudness and true-peak vectors, so this suite splits that bullet into
two independently actionable checks and exposes 30 pytest cases.

Implemented capabilities are hard assertions.  Known product gaps are xfails:
they keep CI green without turning missing evidence into a pass, while an
unexpectedly fixed gap becomes an XPASS and is reported as newly available.
"""

from __future__ import annotations

import inspect
import json
import math
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
AUDIO_STUDIO_ROOT = REPOSITORY_ROOT / "audio-studio"
for import_root in (REPOSITORY_ROOT, AUDIO_STUDIO_ROOT):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from audio_studio.core.edit_session import AudioDocument, EditSession
from audio_studio.core.loader import load_audio, save_audio
from audio_studio.core.types import TimeRange
from audio_studio.dsp.effects.eq import EQBand, FilterType, ParametricEQ
from audio_studio.dsp.loudness import LoudnessMeter
from audio_studio.ui.colormaps import COLORMAP_NAMES
from audio_studio.ui.main_window import UI_REFRESH_MS
from audio_studio.ui.theme import PALETTE

from tools.ebu_vectors import (
    SAMPLE_RATE,
    TECH_3341_VECTORS,
    TECH_3342_VECTORS,
    synthesize_segments,
    synthesize_true_peak,
)
from tools.golden_audio import assert_bit_exact_wav

Verifier = Callable[[Path], None]


@dataclass(frozen=True)
class ChecklistCase:
    """One independently reported SOTA acceptance item."""

    case_id: str
    priority: str
    title: str
    verify: Verifier
    expected_gap: str | None = None


def _load_json(path: Path) -> dict:
    assert path.is_file(), f"missing evidence report: {path.relative_to(REPOSITORY_ROOT)}"
    return json.loads(path.read_text(encoding="utf-8"))


def _require_direct_report(relative_path: str, required_ids: set[str] | None = None) -> None:
    report = _load_json(REPOSITORY_ROOT / relative_path)
    results = report.get("results", [])
    if required_ids is not None:
        assert required_ids <= {item.get("slo_id") for item in results}
    assert results, "evidence report contains no measured results"
    assert all(item.get("status") == "pass" for item in results)
    assert all(item.get("formal_slo_verified") is True for item in results)


def _verify_ebu_3341_loudness(_tmp_path: Path) -> None:
    meter = LoudnessMeter(SAMPLE_RATE)
    for vector in TECH_3341_VECTORS:
        audio = synthesize_segments(vector.segments)
        measured = meter.integrated(audio, channels_last=True)
        assert measured == pytest.approx(vector.expected_integrated_lufs, abs=0.1), vector.case_id


def _verify_ebu_3341_true_peak_vectors(_tmp_path: Path) -> None:
    from tools import ebu_vectors

    vectors = getattr(ebu_vectors, "TECH_3341_TRUE_PEAK_VECTORS", ())
    assert vectors, "no Tech 3341 true-peak vectors are defined"
    for vector in vectors:
        meter = LoudnessMeter(vector.sample_rate)
        report = meter.analyze(synthesize_true_peak(vector), channels_last=True)
        error = report.true_peak_dbtp - vector.expected_dbtp
        assert -0.4 <= error <= 0.2, vector.case_id


def _verify_ebu_3342_lra(_tmp_path: Path) -> None:
    meter = LoudnessMeter(SAMPLE_RATE)
    for vector in TECH_3342_VECTORS:
        audio = synthesize_segments(vector.segments)
        measured = meter.loudness_range(audio, channels_last=True)
        assert measured == pytest.approx(vector.expected_lra_lu, abs=1.0), vector.case_id


def _verify_wav_null_roundtrip(tmp_path: Path) -> None:
    rng = np.random.default_rng(3341)
    samples = rng.uniform(-0.8, 0.8, size=(8_193, 2)).astype(np.float32)
    for subtype in ("PCM_16", "PCM_24", "FLOAT"):
        source = tmp_path / f"source-{subtype}.wav"
        exported = tmp_path / f"exported-{subtype}.wav"
        sf.write(source, samples, SAMPLE_RATE, subtype=subtype)
        loaded = load_audio(source)
        save_audio(exported, loaded.buffer, subtype=subtype, dither=False)
        assert_bit_exact_wav(source, exported)


def _reference_peaking_response(
    frequencies: np.ndarray,
    *,
    sample_rate: float,
    center_hz: float,
    gain_db: float,
    q: float,
) -> np.ndarray:
    """Independent RBJ peaking-EQ transfer-function evaluation."""
    w0 = 2.0 * math.pi * center_hz / sample_rate
    alpha = math.sin(w0) / (2.0 * q)
    amplitude = 10.0 ** (gain_db / 40.0)
    b = np.array(
        (1.0 + alpha * amplitude, -2.0 * math.cos(w0), 1.0 - alpha * amplitude)
    )
    a = np.array(
        (1.0 + alpha / amplitude, -2.0 * math.cos(w0), 1.0 - alpha / amplitude)
    )
    b /= a[0]
    a /= a[0]
    z_inverse = np.exp(-2j * np.pi * frequencies / sample_rate)
    response = (b[0] + b[1] * z_inverse + b[2] * z_inverse**2) / (
        1.0 + a[1] * z_inverse + a[2] * z_inverse**2
    )
    return 20.0 * np.log10(np.maximum(np.abs(response), 1e-15))


def _verify_parametric_eq_response(_tmp_path: Path) -> None:
    sample_rate = 48_000.0
    frequencies = np.geomspace(20.0, 20_000.0, 2_048)
    settings = {"center_hz": 2_137.0, "gain_db": 9.25, "q": 1.37}
    eq = ParametricEQ(
        [
            EQBand(
                frequency=settings["center_hz"],
                gain_db=settings["gain_db"],
                q=settings["q"],
                type=FilterType.PEAKING,
            )
        ]
    )
    actual = eq.magnitude_response_db(frequencies, sample_rate)
    expected = _reference_peaking_response(frequencies, sample_rate=sample_rate, **settings)
    assert float(np.max(np.abs(actual - expected))) < 0.05


def _verify_vhq_src_evidence(_tmp_path: Path) -> None:
    from audio_studio.core import loader

    signature = inspect.signature(loader.resample)
    assert "quality" in signature.parameters, "SRC has no selectable offline/VHQ quality"
    report = _load_json(REPOSITORY_ROOT / ".agent_workspace/round3/src-quality-report.json")
    assert report["stopband_mirror_dbfs"] < -120.0
    assert report["thd_plus_n_dbfs"] < -130.0


def _verify_true_peak_limiter(_tmp_path: Path) -> None:
    from audio_studio.dsp import effects

    assert hasattr(effects, "TruePeakLimiter")


def _verify_tpdf_dither(_tmp_path: Path) -> None:
    from audio_studio.core import loader

    assert hasattr(loader, "quantize_with_tpdf")
    report = _load_json(REPOSITORY_ROOT / ".agent_workspace/round3/tpdf-spectrum-report.json")
    assert report["status"] == "pass"


def _verify_aes17_report(_tmp_path: Path) -> None:
    assert (REPOSITORY_ROOT / "tools/aes17.py").is_file()
    report = _load_json(REPOSITORY_ROOT / ".agent_workspace/round3/aes17-report.json")
    assert report["status"] == "pass"


def _verify_m1_m13_manifest(_tmp_path: Path) -> None:
    report = _load_json(REPOSITORY_ROOT / ".agent_workspace/round3/must-have-evidence.json")
    requirements = report.get("requirements", [])
    assert {item.get("id") for item in requirements} == {f"M{index}" for index in range(1, 14)}
    assert all(item.get("status") == "pass" for item in requirements)
    assert all(item.get("evidence") for item in requirements)


def _verify_formal_file_performance(_tmp_path: Path) -> None:
    _require_direct_report(
        ".agent_workspace/round3/file-performance-report.json",
        {"waveform-open", "spectrogram-first-frame", "offline-eq-normalize"},
    )


def _verify_rf64_streaming(_tmp_path: Path) -> None:
    from audio_studio.core import loader

    source = inspect.getsource(loader)
    assert "RF64" in source
    report = _load_json(REPOSITORY_ROOT / ".agent_workspace/round3/rf64-streaming-report.json")
    assert report["file_size_bytes"] > 4 * 1024**3
    assert report["peak_rss_bytes"] < 1024**3
    assert report["status"] == "pass"


def _verify_undo_redo_100_steps(_tmp_path: Path) -> None:
    rng = np.random.default_rng(100)
    original = rng.normal(0.0, 0.1, size=(512, 2)).astype(np.float32)
    session = EditSession(
        AudioDocument.from_array(original, SAMPLE_RATE, chunk_frames=64),
        undo_limit=150,
    )
    for index in range(120):
        start = index % 256
        session.apply_gain(TimeRange(start, start + 8), 0.125)
    final = session.read(0, session.n_frames)
    assert session.undo_stack.depth == 120
    assert all(session.undo() for _ in range(120))
    assert np.array_equal(session.read(0, session.n_frames), original)
    assert all(session.redo() for _ in range(120))
    assert np.array_equal(session.read(0, session.n_frames), final)


def _verify_spectral_repairs(_tmp_path: Path) -> None:
    from audio_studio.dsp import repair, spectral

    assert {"declick", "dehum"} <= set(dir(repair)), "DeClick/DeHum repairs are missing"
    required = {"attenuate_selection", "delete_selection"}
    assert required <= set(dir(spectral)), "spectral selection editing is missing"


def _verify_plugin_host(_tmp_path: Path) -> None:
    plugin_host = AUDIO_STUDIO_ROOT / "audio_studio/plugins"
    assert plugin_host.is_dir()
    report = _load_json(REPOSITORY_ROOT / ".agent_workspace/round3/plugin-host-report.json")
    assert report["vst3_plugins_passed"] >= 3
    assert report["state_restore"] == "pass"
    assert report["pdc_null_test"] == "pass"


def _verify_batch_loudness(_tmp_path: Path) -> None:
    batch_module = AUDIO_STUDIO_ROOT / "audio_studio/core/batch.py"
    assert batch_module.is_file()
    report = _load_json(REPOSITORY_ROOT / ".agent_workspace/round3/batch-loudness-report.json")
    assert report["input_files"] == 10
    assert report["output_format"].lower() == "flac"
    assert all(abs(value + 16.0) <= 0.1 for value in report["integrated_lufs"])


def _verify_multitrack_32(_tmp_path: Path) -> None:
    from audio_studio.core import session

    assert hasattr(session, "MultitrackSession"), "multitrack session model is missing"
    _require_direct_report(".agent_workspace/round3/multitrack-report.json", {"32-track"})


def _verify_playback_stability(_tmp_path: Path) -> None:
    _require_direct_report(".agent_workspace/round3/playback-stability-report.json", {"playback-30m"})


def _verify_recording_stability(_tmp_path: Path) -> None:
    _require_direct_report(".agent_workspace/round3/recording-stability-report.json", {"recording-60m"})


def _verify_callback_discipline(_tmp_path: Path) -> None:
    from audio_studio.core.engine import AudioEngine

    source = inspect.getsource(AudioEngine.render_into)
    assert "_update_levels" not in source, "callback meter path still allocates NumPy arrays/tuples"
    _require_direct_report(".agent_workspace/round3/callback-timing-report.json", {"callback-p99"})


def _verify_roundtrip_latency(_tmp_path: Path) -> None:
    report = _load_json(REPOSITORY_ROOT / ".agent_workspace/round3/roundtrip-latency-report.json")
    assert report["buffer_frames"] == 128
    assert report["roundtrip_latency_ms"] < 15.0
    assert report["evidence"] == "hardware-loopback"


def _verify_ui_60fps(_tmp_path: Path) -> None:
    assert UI_REFRESH_MS <= 16
    report = _load_json(REPOSITORY_ROOT / ".agent_workspace/round3/ui-frame-time-report.json")
    assert report["p99_frame_ms"] < 16.0
    assert report["hidpi_2x"] == "pass"
    assert report["dark_theme_default"] is True


def _verify_workspace_persistence(_tmp_path: Path) -> None:
    source = (AUDIO_STUDIO_ROOT / "audio_studio/ui/main_window.py").read_text(encoding="utf-8")
    assert '"waveform"' in source and '"multitrack"' in source, "workspace switching is missing"
    assert "saveState(" in source and "restoreState(" in source, (
        "dock-layout persistence is missing"
    )


def _verify_keyboard_workflow(_tmp_path: Path) -> None:
    report = _load_json(REPOSITORY_ROOT / ".agent_workspace/round3/keyboard-workflow-report.json")
    assert report["steps"] == ["open", "select", "apply-effect", "export"]
    assert report["mouse_events"] == 0
    assert report["status"] == "pass"


def _relative_luminance(hex_color: str) -> float:
    channels = [int(hex_color[index : index + 2], 16) / 255.0 for index in (1, 3, 5)]
    linear = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4 for value in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast_ratio(foreground: str, background: str) -> float:
    lighter, darker = sorted(
        (_relative_luminance(foreground), _relative_luminance(background)), reverse=True
    )
    return (lighter + 0.05) / (darker + 0.05)


def _verify_accessibility(_tmp_path: Path) -> None:
    assert _contrast_ratio(PALETTE.text, PALETTE.window) >= 4.5
    assert "viridis" in COLORMAP_NAMES
    report = _load_json(REPOSITORY_ROOT / ".agent_workspace/round3/accessibility-report.json")
    assert report["wcag_2_2_aa"] == "pass"
    assert report["screen_reader_platforms_passed"] >= 1


def _verify_ui_scaling(_tmp_path: Path) -> None:
    report = _load_json(REPOSITORY_ROOT / ".agent_workspace/round3/ui-scaling-report.json")
    assert report["scales_percent"] == [100, 125, 150, 175, 200]
    assert all(result["status"] == "pass" for result in report["results"])


def _verify_three_platform_ci(_tmp_path: Path) -> None:
    workflow = (REPOSITORY_ROOT / ".github/workflows/audio-tests.yml").read_text(encoding="utf-8")
    for token in ("ubuntu-latest", "macos-latest", "windows-latest"):
        assert token in workflow
    for package in ("libegl1", "libgl1", "libxcb-cursor0", "libxkbcommon-x11-0"):
        assert package in workflow
    assert "python -m pytest -q tests audio-studio/tests" in workflow
    assert "audio-studio/tests/test_loudness.py" in workflow
    assert "! grep -rn PyQt6 audio-studio/" in workflow


def _verify_cross_platform_golden(_tmp_path: Path) -> None:
    report = _load_json(REPOSITORY_ROOT / ".agent_workspace/round3/cross-platform-golden.json")
    platforms = report.get("platforms", {})
    assert set(platforms) == {"linux", "macos", "windows"}
    assert report["maximum_absolute_error"] <= 1e-9
    assert report["status"] == "pass"


def _verify_third_party_licenses(_tmp_path: Path) -> None:
    path = REPOSITORY_ROOT / "THIRD_PARTY_LICENSES.md"
    assert path.is_file()
    text = path.read_text(encoding="utf-8").lower()
    for dependency in ("pyside6", "numpy", "scipy", "libsndfile"):
        assert dependency in text


def _verify_crash_recovery(_tmp_path: Path) -> None:
    report = _load_json(REPOSITORY_ROOT / ".agent_workspace/round3/crash-recovery-report.json")
    assert report["termination"] == "kill -9"
    assert report["session_restored"] is True
    assert report["status"] == "pass"


CHECKLIST_CASES = (
    ChecklistCase("A1-LUFS", "P0", "EBU Tech 3341 loudness ±0.1 LU", _verify_ebu_3341_loudness),
    ChecklistCase(
        "A1-TP",
        "P0",
        "EBU Tech 3341 true peak +0.2/-0.4 dB",
        _verify_ebu_3341_true_peak_vectors,
    ),
    ChecklistCase("A2", "P0", "EBU Tech 3342 LRA ±1 LU", _verify_ebu_3342_lra),
    ChecklistCase("A3", "P0", "WAV 16/24/32f null round-trip", _verify_wav_null_roundtrip),
    ChecklistCase("A4", "P0", "Parametric EQ response <0.05 dB", _verify_parametric_eq_response),
    ChecklistCase(
        "A5",
        "P0",
        "VHQ SRC stopband and THD+N",
        _verify_vhq_src_evidence,
        "resample() has no quality parameter and the SRC report misses the "
        "stopband/THD+N mastering thresholds",
    ),
    ChecklistCase(
        "A6",
        "P0",
        "True-peak limiter ISP ceiling",
        _verify_true_peak_limiter,
        "no true-peak limiter is implemented",
    ),
    ChecklistCase(
        "A7",
        "P1",
        "TPDF dither spectrum",
        _verify_tpdf_dither,
        "quantize_with_tpdf landed; the TPDF spectrum evidence report is missing",
    ),
    ChecklistCase(
        "A8",
        "P1",
        "AES17 THD+N report",
        _verify_aes17_report,
        "AES17 measurement tool and report are missing",
    ),
    ChecklistCase(
        "B1",
        "P0",
        "M1-M13 demonstrated with evidence",
        _verify_m1_m13_manifest,
        "no complete M1-M13 evidence manifest exists",
    ),
    ChecklistCase(
        "B2",
        "P0",
        "One-hour file performance",
        _verify_formal_file_performance,
        "only shortened headless performance proxies exist",
    ),
    ChecklistCase(
        "B3",
        "P0",
        "4GB RF64 streaming under 1GB RSS",
        _verify_rf64_streaming,
        "RF64/W64 decode support landed; 4GB streaming under-1GB-RSS evidence is missing",
    ),
    ChecklistCase("B4", "P0", "100-step undo/redo", _verify_undo_redo_100_steps),
    ChecklistCase(
        "B5",
        "P1",
        "Spectral edit, DeClick, and DeHum",
        _verify_spectral_repairs,
        "DeClick/DeHum landed in dsp.repair; spectral selection editing is missing",
    ),
    ChecklistCase(
        "B6",
        "P1",
        "VST3/AU host, state, and PDC",
        _verify_plugin_host,
        "plugin host package landed; VST3 compatibility/state/PDC evidence is missing",
    ),
    ChecklistCase(
        "B7",
        "P1",
        "10-file -16 LUFS FLAC batch",
        _verify_batch_loudness,
        "batch loudness workflow is missing",
    ),
    ChecklistCase(
        "B8",
        "P1",
        "32-track playback and automation",
        _verify_multitrack_32,
        "MultitrackSession landed; 32-track playback/automation evidence is missing",
    ),
    ChecklistCase(
        "C1",
        "P0",
        "48k/256 30-minute playback stability",
        _verify_playback_stability,
        "only an accelerated headless soak exists; hardware 30-minute playback "
        "evidence is missing",
    ),
    ChecklistCase(
        "C2",
        "P0",
        "60-minute recording stability",
        _verify_recording_stability,
        "hardware recording stability evidence is missing",
    ),
    ChecklistCase(
        "C3",
        "P0",
        "Callback p99 and realtime discipline",
        _verify_callback_discipline,
        # The zero-allocation callback landed (meter reductions moved to the
        # feeder thread; see tests/test_render_discipline.py), so the source
        # assertion below passes. Only the formal callback-p99 hardware timing
        # report keeps this item open.
        "zero-alloc callback fixed; formal callback-p99 timing evidence is missing",
    ),
    ChecklistCase(
        "C4",
        "P1",
        "Hardware round-trip latency under 15 ms",
        _verify_roundtrip_latency,
        "hardware loopback evidence is missing",
    ),
    ChecklistCase(
        "D1",
        "P0",
        "60fps, HiDPI, and dark default",
        _verify_ui_60fps,
        "UI timer is 30Hz and no frame-time/HiDPI report exists",
    ),
    ChecklistCase(
        "D2",
        "P0",
        "Dock presets and layout persistence",
        _verify_workspace_persistence,
        "waveform/multitrack workspaces landed; dock-layout saveState/restoreState "
        "persistence is missing",
    ),
    ChecklistCase(
        "D3",
        "P0",
        "Keyboard-only end-to-end workflow",
        _verify_keyboard_workflow,
        "no keyboard-only workflow evidence exists",
    ),
    ChecklistCase(
        "D4",
        "P1",
        "WCAG AA, color-safe map, screen reader",
        _verify_accessibility,
        "palette and colormap checks pass; screen-reader evidence is missing",
    ),
    ChecklistCase(
        "D5",
        "P1",
        "UI scaling from 100% to 200%",
        _verify_ui_scaling,
        "multi-scale UI evidence is missing",
    ),
    ChecklistCase("E1", "P0", "Three-platform CI gates", _verify_three_platform_ci),
    ChecklistCase(
        "E2",
        "P0",
        "Cross-platform DSP golden consistency",
        _verify_cross_platform_golden,
        "no three-platform golden comparison artifact exists",
    ),
    ChecklistCase("E3", "P0", "Third-party license inventory", _verify_third_party_licenses),
    ChecklistCase(
        "E4",
        "P1",
        "Crash auto-recovery",
        _verify_crash_recovery,
        "crash recovery implementation/evidence is missing",
    ),
)


def _pytest_parameter(case: ChecklistCase):
    marks = ()
    if case.expected_gap:
        marks = pytest.mark.xfail(reason=case.expected_gap, strict=False)
    return pytest.param(case, id=case.case_id, marks=marks)


def test_checklist_defines_thirty_independent_automated_items() -> None:
    assert len(CHECKLIST_CASES) == 30
    assert len({case.case_id for case in CHECKLIST_CASES}) == 30


@pytest.mark.parametrize("case", [_pytest_parameter(case) for case in CHECKLIST_CASES])
def test_sota_checklist_item(case: ChecklistCase, tmp_path: Path) -> None:
    case.verify(tmp_path)
