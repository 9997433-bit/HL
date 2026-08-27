"""Run the bounded modal benchmark used by the CI acceptance-gates job."""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BENCHMARK_TIME_LIMIT_SECONDS = 20.0
PROCESS_TIMEOUT_SECONDS = 30.0
COMMAND = (
    "openfemlab",
    "bench",
    "modal",
    "--sizes",
    "100,500",
    "--repeats",
    "1",
)


def _write_output(result: subprocess.CompletedProcess[str]) -> None:
    """Forward captured benchmark output into the CI log."""
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)


def main() -> int:
    """Run the benchmark and fail on command errors, hangs, or regressions."""
    started = time.perf_counter()
    try:
        result = subprocess.run(
            COMMAND,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=PROCESS_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        print(
            f"modal benchmark exceeded the {PROCESS_TIMEOUT_SECONDS:.0f} s hard timeout",
            file=sys.stderr,
        )
        if exc.stdout:
            print(exc.stdout, end="", file=sys.stderr)
        if exc.stderr:
            print(exc.stderr, end="", file=sys.stderr)
        return 1

    elapsed = time.perf_counter() - started
    _write_output(result)
    if result.returncode != 0:
        print(f"modal benchmark exited with status {result.returncode}", file=sys.stderr)
        return 1
    if elapsed > BENCHMARK_TIME_LIMIT_SECONDS:
        print(
            f"modal benchmark took {elapsed:.2f} s; "
            f"limit is {BENCHMARK_TIME_LIMIT_SECONDS:.0f} s",
            file=sys.stderr,
        )
        return 1

    print(
        f"Modal benchmark gate passed in {elapsed:.2f} s "
        f"(limit {BENCHMARK_TIME_LIMIT_SECONDS:.0f} s)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
