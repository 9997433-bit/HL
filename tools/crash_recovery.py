"""Crash auto-recovery evidence (SOTA checklist E4).

The claim under test is that work survives a crash the application cannot
intercept. So nothing here is simulated: a real child process opens a session,
edits it, and autosaves through
:class:`audio_studio.core.autosave.AutosaveJournal`; the parent sends it
``SIGKILL``; and a *third* process — a fresh interpreter, standing in for the
next launch — discovers the abandoned journal and restores the session. An
in-process test could not make this claim, because ``SIGKILL`` is precisely the
signal that gives a process no chance to tidy up.

Two properties are checked on what comes back, because "a file was there" is
not recovery:

*Integrity.* The bundle's content digest must match what the journal recorded
before the crash. A snapshot torn by a kill mid-write fails this.

*Identity.* The editing loop scales one distinct region of the document per
edit, in order, so the audio itself says how many edits it contains: regions
``0..k-1`` attenuated and ``k..n`` untouched. Recovery must land on exactly
such a prefix — the state after some real edit ``k``, never a blend of two
snapshots — and ``k`` must be within one autosave interval of the last edit the
worker logged, which is the bound on what a crash may cost.

Kills are timed to land at varied points relative to the autosave interval, so
that some of them land *during* a bundle write rather than between writes.

Scope, honestly: ``SIGKILL`` is POSIX, so the harness runs on Linux and macOS
and is skipped on Windows. It is a process-kill test on one host, not a power
cut — durability against media loss rests on the ``fsync`` calls in the journal
rather than on anything measured here — and it drives the session objects
directly rather than through the Qt window.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import signal
import subprocess
import sys
import time
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
for _import_root in (REPOSITORY_ROOT, REPOSITORY_ROOT / "audio-studio"):
    if str(_import_root) not in sys.path:
        sys.path.insert(0, str(_import_root))

from audio_studio.core.autosave import AutosaveJournal, discover
from audio_studio.core.edit_session import EditSession
from audio_studio.core.loader import load_audio, save_audio
from audio_studio.core.sample_source import MemorySampleSource
from audio_studio.core.session import MultitrackSession, Track
from audio_studio.core.types import AudioBuffer, TimeRange
from audio_studio.project.store import load_waveform_document

__all__ = [
    "DEFAULT_OUTPUT",
    "EDIT_GAIN_DB",
    "REGION_COUNT",
    "build_report",
    "recover",
    "run_trial",
    "run_trials",
]

DEFAULT_OUTPUT = Path(".agent_workspace/round3/crash-recovery-report.json")

SAMPLE_RATE = 48_000
DOCUMENT_SECONDS = 3.0
#: Editable regions the document is divided into. Each edit takes the next one,
#: so the number of regions is the number of edits the worker can make.
REGION_COUNT = 120
#: Attenuation one edit applies, in dB. Far enough from unity that a region's
#: state is unambiguous after PCM-24 export and dither.
EDIT_GAIN_DB = -12.0
EDIT_GAIN_RATIO = 10.0 ** (EDIT_GAIN_DB / 20.0)
#: How fast the worker edits. Slow enough that "edits lost to the crash" is a
#: small readable number rather than an artefact of a tight loop.
EDITS_PER_SECOND = 20.0

#: Autosave interval used by the harness. The product default is 30 s; a crash
#: test that waited that long between snapshots would measure patience.
TRIAL_INTERVAL_S = 0.15
TRIAL_COUNT = 5
#: Kill delays, in seconds after the second autosave lands. Spread across the
#: interval so that some kills interrupt a bundle write.
KILL_DELAYS_S = (0.0, 0.05, 0.11, 0.19, 0.31)

PROGRESS_NAME = "progress.log"
SOURCE_NAME = "source.wav"
REGION_FRAMES = int(SAMPLE_RATE * DOCUMENT_SECONDS) // REGION_COUNT


def _base_audio() -> np.ndarray:
    """The document every trial starts from: deterministic, never silent.

    Region identification divides by this signal, so no region may be quiet
    enough to make that ratio meaningless.
    """
    rng = np.random.default_rng(90_210)
    frames = REGION_FRAMES * REGION_COUNT
    noise = 0.25 * (2.0 * rng.random((frames, 2)) - 1.0)
    return (noise + np.sign(noise) * 0.2).astype(np.float32)


def _workspace(root: Path) -> tuple[Path, Path]:
    return root / SOURCE_NAME, root / PROGRESS_NAME


# -- worker: the process that gets killed ------------------------------------


def _build_session(source_path: Path) -> tuple[EditSession, Any, MultitrackSession]:
    clip = load_audio(source_path)
    session = EditSession.from_buffer(clip.buffer)
    multitrack = MultitrackSession(sample_rate=SAMPLE_RATE, n_channels=2)
    for index in range(2):
        samples = clip.buffer.data[: SAMPLE_RATE // 2]
        source = MemorySampleSource(AudioBuffer(np.ascontiguousarray(samples), SAMPLE_RATE))
        track = multitrack.add_track(Track(name=f"Take {index + 1}", gain_db=-3.0 * index))
        multitrack.add_clip(track, source, start=index * 4_000, duration=source.n_frames)
    return session, clip, multitrack


def run_worker(
    root: Path, *, interval_s: float, editor_id: str, max_edits: int = REGION_COUNT
) -> int:
    """Edit and autosave, either until killed or until ``max_edits`` are done.

    Reaching the end is how the clean-exit control runs: the journal is
    released, and a launch that finds nothing to recover is the proof that
    recovery keys on an abandoned session rather than on any session at all.
    """
    source_path, progress_path = _workspace(root)
    session, clip, multitrack = _build_session(source_path)

    journal = AutosaveJournal(
        root=root / "autosave",
        interval_s=interval_s,
        session_id=editor_id,
        label="crash-recovery-harness",
        project_path=source_path,
    )

    def snapshot() -> dict[str, Any]:
        return {
            "edit_session": session,
            "editor_clip": clip,
            "multitrack": multitrack,
            "workspace": "waveform",
            "view_mode": "split",
            "playhead": 0,
            "selection": None,
        }

    journal.start(snapshot)

    progress = progress_path.open("a", encoding="utf-8")
    step = 1.0 / EDITS_PER_SECOND
    for region in range(min(max_edits, REGION_COUNT)):
        start = region * REGION_FRAMES
        session.apply_gain(TimeRange(start, start + REGION_FRAMES), EDIT_GAIN_DB)
        # Logged with fsync *after* the edit lands, so the log can only ever
        # claim edits the session really has. Recovery finding fewer than the
        # log records is data loss; finding more would mean the log lied.
        progress.write(json.dumps({"seq": region + 1, "region": region}) + "\n")
        progress.flush()
        os.fsync(progress.fileno())
        time.sleep(step)

    journal.release()
    progress.close()
    return 0


# -- recovery: the process that stands in for the next launch ----------------


def _region_states(restored: np.ndarray, base: np.ndarray) -> list[bool]:
    """Which regions of ``restored`` carry the edit, judged against ``base``."""
    states = []
    for region in range(REGION_COUNT):
        window = slice(region * REGION_FRAMES, (region + 1) * REGION_FRAMES)
        reference = float(np.mean(np.abs(base[window])))
        measured = float(np.mean(np.abs(restored[window])))
        ratio = measured / reference if reference else 1.0
        # PCM-24 export plus TPDF dither moves a sample by ~1e-7; the two
        # states being told apart are 1.0 and 0.25.
        states.append(bool(abs(ratio - EDIT_GAIN_RATIO) < abs(ratio - 1.0)))
    return states


def recover(root: Path) -> dict[str, Any]:
    """Restore the abandoned session under ``root``, the way a launch would."""
    source_path, progress_path = _workspace(root)
    sessions = discover(root / "autosave")
    verdict: dict[str, Any] = {
        "recoverable_sessions": len(sessions),
        "session_restored": False,
    }
    if not sessions:
        verdict["failure"] = "no abandoned autosave journal was found"
        return verdict

    session = sessions[0]
    entry = session.entry
    verdict.update(
        {
            "autosave_sequence": entry.sequence,
            "autosave_slot": entry.slot,
            "crashed_pid": entry.pid,
            "crashed_pid_alive": session.owner_alive,
            "bundle_intact": session.verify(),
            "saved_at_utc": entry.saved_at_utc,
        }
    )
    if not verdict["bundle_intact"]:
        verdict["failure"] = "the autosaved bundle did not match its recorded digest"
        return verdict

    snapshot = session.load()
    clip, restored_session, _playhead, _selection = load_waveform_document(snapshot)
    restored = restored_session.read(0, restored_session.n_frames)
    base = load_audio(source_path).buffer.data

    verdict["restored_frames"] = int(restored.shape[0])
    verdict["frames_match_source"] = restored.shape == base.shape
    if not verdict["frames_match_source"]:
        verdict["failure"] = "the restored document is not the shape of the one being edited"
        return verdict

    states = _region_states(restored, base)
    edits_restored = states.index(False) if False in states else len(states)
    # A snapshot is the state after some whole number of edits, so the edited
    # regions must be a prefix. Anything else is a bundle stitched together
    # from two different moments, which is the failure this design exists to
    # rule out.
    verdict["edited_region_prefix"] = not any(states[edits_restored:])
    verdict["edits_restored"] = edits_restored

    logged = [
        json.loads(line)
        for line in progress_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    verdict["edits_logged_before_crash"] = logged[-1]["seq"] if logged else 0
    verdict["edits_lost"] = verdict["edits_logged_before_crash"] - edits_restored

    multitrack = snapshot.multitrack
    verdict["tracks_restored"] = len(multitrack.get("tracks", []))
    verdict["track_names"] = [track.get("name") for track in multitrack.get("tracks", [])]
    verdict["clip_source"] = clip.name

    verdict["session_restored"] = bool(
        verdict["bundle_intact"]
        and verdict["edited_region_prefix"]
        and edits_restored >= 1
        and verdict["edits_lost"] >= 0
        and verdict["tracks_restored"] == 2
    )
    return verdict


# -- parent: the process that does the killing -------------------------------


def _prepare_root(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    source_path, progress_path = _workspace(root)
    save_audio(source_path, AudioBuffer(_base_audio(), SAMPLE_RATE), subtype="FLOAT")
    progress_path.write_text("", encoding="utf-8")


def _wait_for_autosave(root: Path, *, minimum: int, timeout_s: float) -> int:
    """Block until ``minimum`` autosaves have landed; return the sequence.

    Waiting for the second one matters: the first save populates slot A, and
    only from the second onwards is the process overwriting one slot while the
    pointer names the other — the situation the crash has to survive.
    """
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        sessions = discover(root / "autosave", include_live=True)
        if sessions and sessions[0].entry.sequence >= minimum:
            return sessions[0].entry.sequence
        time.sleep(0.02)
    raise TimeoutError(f"no autosave reached sequence {minimum} within {timeout_s}s")


def run_trial(
    trial_id: int,
    root: Path,
    *,
    interval_s: float = TRIAL_INTERVAL_S,
    kill_delay_s: float = 0.0,
) -> dict[str, Any]:
    """Start a worker, kill -9 it, and recover in a fresh interpreter."""
    _prepare_root(root)
    editor_id = f"trial{trial_id:02d}{random.randbytes(3).hex()}"
    worker = subprocess.Popen(
        [
            sys.executable,
            str(Path(__file__).resolve()),
            "worker",
            "--root",
            str(root),
            "--interval",
            str(interval_s),
            "--editor-id",
            editor_id,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    row: dict[str, Any] = {
        "trial": trial_id,
        "pid": worker.pid,
        "autosave_interval_s": interval_s,
        "kill_delay_after_second_autosave_s": kill_delay_s,
        "termination": "kill -9",
    }
    try:
        row["autosave_sequence_at_kill"] = _wait_for_autosave(root, minimum=2, timeout_s=30.0)
        time.sleep(kill_delay_s)
        killed_at = time.monotonic()
        os.kill(worker.pid, signal.SIGKILL)
        worker.wait(timeout=30.0)
    except (TimeoutError, subprocess.TimeoutExpired) as error:
        worker.kill()
        _stdout, stderr = worker.communicate()
        row.update(
            {
                "status": "fail",
                "failure": f"{type(error).__name__}: {error}",
                "worker_stderr": stderr.decode("utf-8", "replace")[-2_000:],
            }
        )
        return row

    _stdout, stderr = worker.communicate()
    row["kill_to_exit_ms"] = (time.monotonic() - killed_at) * 1000.0
    row["worker_returncode"] = worker.returncode
    # A worker that exited any other way did not model a crash: -9 is the
    # kernel reporting that the process was killed outright.
    row["killed_by_sigkill"] = worker.returncode == -signal.SIGKILL
    if stderr.strip():
        row["worker_stderr"] = stderr.decode("utf-8", "replace")[-2_000:]

    verdict = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "recover", "--root", str(root)],
        capture_output=True,
        check=False,
    )
    if verdict.returncode not in (0, 1) or not verdict.stdout.strip():
        row.update(
            {
                "status": "fail",
                "failure": "the recovery process did not produce a verdict",
                "recovery_stderr": verdict.stderr.decode("utf-8", "replace")[-2_000:],
            }
        )
        return row

    row["recovery"] = json.loads(verdict.stdout.decode("utf-8"))
    row["session_restored"] = bool(row["recovery"].get("session_restored"))
    row["edits_lost"] = row["recovery"].get("edits_lost")
    # Losing more than an interval's worth of edits would mean the autosave
    # ran but its snapshot was older than the interval promises.
    budget = int(interval_s * EDITS_PER_SECOND) + 2
    row["edits_lost_within_one_interval"] = (
        isinstance(row["edits_lost"], int) and 0 <= row["edits_lost"] <= budget
    )
    row["edit_loss_budget"] = budget
    row["status"] = (
        "pass"
        if row["killed_by_sigkill"]
        and row["session_restored"]
        and row["edits_lost_within_one_interval"]
        else "fail"
    )
    return row


def run_clean_exit_control(
    root: Path, *, interval_s: float = TRIAL_INTERVAL_S
) -> dict[str, Any]:
    """A worker that exits normally must leave nothing to recover.

    Without this, "a session was restored" would be consistent with a recovery
    prompt that fires after every launch, which is its own kind of broken.
    """
    _prepare_root(root)
    worker = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).resolve()),
            "worker",
            "--root",
            str(root),
            "--interval",
            str(interval_s),
            "--editor-id",
            "cleanexit",
            "--max-edits",
            "6",
        ],
        capture_output=True,
        check=False,
        timeout=120.0,
    )
    verdict = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "recover", "--root", str(root)],
        capture_output=True,
        check=False,
        timeout=120.0,
    )
    recovered = json.loads(verdict.stdout.decode("utf-8")) if verdict.stdout.strip() else {}
    row = {
        "control": "clean-exit",
        "termination": "normal exit",
        "worker_returncode": worker.returncode,
        "recoverable_sessions": recovered.get("recoverable_sessions"),
        "session_restored": bool(recovered.get("session_restored")),
    }
    row["status"] = (
        "pass"
        if worker.returncode == 0
        and row["recoverable_sessions"] == 0
        and not row["session_restored"]
        else "fail"
    )
    if row["status"] == "fail" and worker.stderr.strip():
        row["worker_stderr"] = worker.stderr.decode("utf-8", "replace")[-2_000:]
    return row


def run_trials(
    workspace: Path,
    *,
    count: int = TRIAL_COUNT,
    interval_s: float = TRIAL_INTERVAL_S,
) -> list[dict[str, Any]]:
    rows = []
    for index in range(count):
        root = workspace / f"trial-{index + 1:02d}"
        rows.append(
            run_trial(
                index + 1,
                root,
                interval_s=interval_s,
                kill_delay_s=KILL_DELAYS_S[index % len(KILL_DELAYS_S)],
            )
        )
    return rows


def build_report(
    trials: Sequence[dict[str, Any]],
    *,
    interval_s: float,
    clean_exit_control: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Wrap the trials in the E4 evidence document."""
    if not trials:
        raise ValueError("a crash-recovery report needs at least one trial")
    passed = [row for row in trials if row.get("status") == "pass"]
    control_passed = clean_exit_control is None or clean_exit_control.get("status") == "pass"
    losses = [row["edits_lost"] for row in trials if isinstance(row.get("edits_lost"), int)]
    return {
        "schema_version": 1,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "item": "E4 crash auto-recovery",
        "component": "audio_studio.core.autosave.AutosaveJournal",
        "harness": "tools/crash_recovery.py",
        "termination": "kill -9",
        "platform": sys.platform,
        "autosave_interval_s": interval_s,
        "edits_per_second": EDITS_PER_SECOND,
        "trials": list(trials),
        "trials_run": len(trials),
        "trials_passed": len(passed),
        "clean_exit_control": clean_exit_control,
        "every_worker_died_by_sigkill": all(row.get("killed_by_sigkill") for row in trials),
        "every_session_restored": all(row.get("session_restored") for row in trials),
        "worst_case_edits_lost": max(losses) if losses else None,
        "edit_loss_budget": max((row.get("edit_loss_budget", 0) for row in trials), default=0),
        "session_restored": bool(trials) and all(row.get("session_restored") for row in trials),
        "evidence": "process-kill",
        "notes": [
            (
                "Each trial kills a real editing process with SIGKILL and recovers in a "
                "separate interpreter, so nothing in the application's own shutdown path "
                "can contribute to the result."
            ),
            (
                "Recovery is accepted only when the bundle digest matches the journal and "
                "the restored audio is the state after a whole number of edits; the count "
                "of edits lost is reported per trial against a one-interval budget."
            ),
            (
                "SIGKILL is POSIX, so this runs on Linux and macOS and is skipped on "
                "Windows. It models a process kill on one host, not a power cut: "
                "durability across media loss rests on the journal's fsync calls."
            ),
            (
                "The harness drives the session and journal objects directly rather than "
                "through the Qt window, which is what lets it run headlessly in CI."
            ),
            (
                "A clean-exit control runs alongside the kills: a worker that shuts down "
                "normally must leave nothing to recover, so a launch is not offering to "
                "restore a session that never crashed."
            ),
        ],
        "status": "pass" if len(passed) == len(trials) and control_passed else "fail",
    }


def write_report(report: dict[str, Any], output: Path) -> Path:
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command")

    run = subparsers.add_parser("run", help="run the trials and write the report (default)")
    run.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    run.add_argument("--workspace", type=Path, default=None)
    run.add_argument("--trials", type=int, default=TRIAL_COUNT)
    run.add_argument("--interval", type=float, default=TRIAL_INTERVAL_S)

    worker = subparsers.add_parser("worker", help="internal: the process that gets killed")
    worker.add_argument("--root", type=Path, required=True)
    worker.add_argument("--interval", type=float, default=TRIAL_INTERVAL_S)
    worker.add_argument("--editor-id", default="worker")
    worker.add_argument("--max-edits", type=int, default=REGION_COUNT)

    recover_parser = subparsers.add_parser("recover", help="internal: restore after a crash")
    recover_parser.add_argument("--root", type=Path, required=True)

    args = parser.parse_args(argv)
    if args.command is None:
        return parser.parse_args(["run", *(argv or [])])
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)

    if args.command == "worker":
        return run_worker(
            args.root,
            interval_s=args.interval,
            editor_id=args.editor_id,
            max_edits=args.max_edits,
        )

    if args.command == "recover":
        verdict = recover(args.root)
        print(json.dumps(verdict, indent=2, sort_keys=True))
        return 0 if verdict.get("session_restored") else 1

    if sys.platform == "win32":
        print("crash recovery harness needs POSIX SIGKILL; skipped on Windows")
        return 0

    import tempfile

    with tempfile.TemporaryDirectory(prefix="crash-recovery-") as scratch:
        workspace = Path(args.workspace) if args.workspace else Path(scratch)
        trials = run_trials(workspace, count=args.trials, interval_s=args.interval)
        control = run_clean_exit_control(workspace / "control", interval_s=args.interval)
        report = build_report(trials, interval_s=args.interval, clean_exit_control=control)
        write_report(report, args.output)

    print(
        json.dumps(
            {
                key: report[key]
                for key in (
                    "termination",
                    "trials_run",
                    "trials_passed",
                    "worst_case_edits_lost",
                    "session_restored",
                    "status",
                )
            },
            indent=2,
        )
    )
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
