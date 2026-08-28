#!/usr/bin/env bash
# End-to-end closure test for OpenFEMLab 0.3.3 desktop workflow.
set -euo pipefail

ROOT="$(mktemp -d)"
echo "workspace: $ROOT"

openfemlab project init "$ROOT" --name e2e-demo
cd "$ROOT"

openfemlab modal models/cantilever.yaml -n 6 \
  --output reports/modes.json --format json

openfemlab correlate models/cantilever.yaml measurements/test.yaml \
  -o reports/corr.json --format json

python - <<'PY'
import json
from pathlib import Path

corr = json.loads(Path("reports/corr.json").read_text(encoding="utf-8"))
summary = corr.get("summary") or {}
assert summary.get("n_paired", summary.get("num_pairs", 0)) >= 1
print("correlate OK:", summary)
PY

PORT=18888
python - <<'PY' &
import threading
from pathlib import Path
from openfemlab.dashboard.server import serve_dashboard

serve_dashboard(host="127.0.0.1", port=18888, root=Path("."))
PY
SERVER_PID=$!
sleep 1

python - <<'PY'
import json
import urllib.request

base = "http://127.0.0.1:18888"
project = json.load(urllib.request.urlopen(f"{base}/api/project"))
assert project["has_project_file"]

job = json.loads(
    urllib.request.urlopen(
        urllib.request.Request(
            f"{base}/api/run",
            data=json.dumps({"workflow": "quickstart"}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
    ).read()
)
job_id = job["id"]
for _ in range(120):
    status = json.load(urllib.request.urlopen(f"{base}/api/job?id={job_id}"))
    if status["status"] != "running":
        break
    __import__("time").sleep(0.1)
else:
    raise SystemExit("quickstart job timeout")
assert status["status"] == "success", status
print("desktop API OK")
PY

kill "$SERVER_PID" 2>/dev/null || true
echo "E2E closure passed."
