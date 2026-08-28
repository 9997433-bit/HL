"""Background CLI job runner for the desktop dashboard."""

from __future__ import annotations

import shutil
import subprocess
import sys
import threading
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

__all__ = [
    "ALLOWED_COMMANDS",
    "JobManager",
    "JobRecord",
    "build_workflow_argv",
]

ALLOWED_COMMANDS = frozenset(
    {
        "modal",
        "correlate",
        "update",
        "static",
        "topopt",
        "reduce",
        "mpe",
        "pipeline",
        "report",
        "quickstart",
        "correlate-frf",
    }
)


@dataclass(slots=True)
class JobRecord:
    """One dashboard-triggered CLI invocation."""

    id: str
    argv: list[str]
    status: str = "running"
    exit_code: int | None = None
    log: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "argv": self.argv,
            "status": self.status,
            "exit_code": self.exit_code,
            "log": list(self.log),
            "outputs": list(self.outputs),
            "error": self.error,
        }


class JobManager:
    """Run whitelisted ``openfemlab`` subcommands in the project root."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self._jobs: dict[str, JobRecord] = {}
        self._lock = threading.Lock()

    def get(self, job_id: str) -> JobRecord | None:
        with self._lock:
            return self._jobs.get(job_id)

    def start(self, argv: list[str], *, outputs: list[str] | None = None) -> JobRecord:
        if not argv:
            raise ValueError("job argv must be non-empty")
        command = str(argv[0])
        if command not in ALLOWED_COMMANDS:
            raise ValueError(f"unsupported dashboard command {command!r}")
        job = JobRecord(
            id=uuid.uuid4().hex[:12],
            argv=[str(item) for item in argv],
            outputs=[str(item) for item in outputs or []],
        )
        with self._lock:
            self._jobs[job.id] = job
        thread = threading.Thread(
            target=self._run,
            args=(job.id,),
            name=f"openfemlab-job-{job.id}",
            daemon=True,
        )
        thread.start()
        return job

    def _run(self, job_id: str) -> None:
        job = self.get(job_id)
        if job is None:
            return
        command = _cli_command() + job.argv
        try:
            process = subprocess.Popen(
                command,
                cwd=self.root,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
        except OSError as exc:
            job.status = "failed"
            job.error = str(exc)
            job.exit_code = 1
            return
        assert process.stdout is not None
        for line in process.stdout:
            job.log.append(line.rstrip("\n"))
        process.wait()
        job.exit_code = int(process.returncode)
        job.status = "success" if process.returncode == 0 else "failed"

    def list_jobs(self, *, limit: int = 20) -> list[dict[str, Any]]:
        with self._lock:
            records = list(self._jobs.values())
        records.sort(key=lambda item: item.id, reverse=True)
        return [record.to_dict() for record in records[: max(1, limit)]]


def _cli_command() -> list[str]:
    executable = shutil.which("openfemlab")
    if executable:
        return [executable, "--no-color"]
    return [sys.executable, "-m", "openfemlab.cli", "--no-color"]


def build_workflow_argv(workflow: str, payload: dict[str, Any]) -> tuple[list[str], list[str]]:
    """Map a dashboard workflow preset to CLI argv and expected output paths."""
    model = str(payload.get("model") or "models/cantilever.yaml")
    measurement = str(payload.get("measurement") or "measurements/test.yaml")
    outputs: list[str] = []

    if workflow == "modal":
        output = str(payload.get("output") or "reports/modes.json")
        outputs = [output]
        num_modes = int(payload.get("num_modes") or 8)
        return (
            ["modal", model, "-n", str(num_modes), "--output", output, "--format", "json"],
            outputs,
        )
    if workflow == "correlate":
        output = str(payload.get("output") or "reports/corr.json")
        outputs = [output]
        return (
            [
                "correlate",
                model,
                measurement,
                "-o",
                output,
                "--format",
                "json",
            ],
            outputs,
        )
    if workflow == "update":
        output = str(payload.get("output") or "models/cantilever.updated.yaml")
        outputs = [output]
        spec = str(payload.get("spec") or "models/updating.yaml")
        return (["update", spec, "-o", output], outputs)
    if workflow == "static":
        output = str(payload.get("output") or "reports/static.json")
        outputs = [output]
        return (["static", model, "--output", output, "--format", "json"], outputs)
    if workflow == "topopt":
        output = str(payload.get("output") or "reports/topology.json")
        outputs = [output]
        argv = [
            "topopt",
            model,
            "--format",
            "json",
            "-o",
            output,
        ]
        if payload.get("optimizer"):
            argv.extend(["--optimizer", str(payload["optimizer"])])
        return (argv, outputs)
    if workflow == "pipeline":
        output = str(payload.get("output") or "reports/correction.json")
        outputs = [output]
        return (
            [
                "pipeline",
                "run",
                model,
                measurement,
                "--strict",
                "-o",
                output,
                "--format",
                "json",
            ],
            outputs,
        )
    if workflow == "quickstart":
        return (["quickstart"], outputs)
    if workflow == "report":
        input_path = str(payload.get("input") or "reports/corr.json")
        output = str(payload.get("output") or "reports/corr.html")
        outputs = [output]
        return (["report", input_path, "-o", output], outputs)
    raise ValueError(f"unknown workflow {workflow!r}")
