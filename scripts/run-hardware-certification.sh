#!/usr/bin/env bash
# Run the C4 hardware certification end to end on a physical USB interface.
#
# This is the one-command form of docs/HARDWARE_CERTIFICATION.md: the device
# probe first, gated with --require-physical so a host without a converter
# stops here with an honest negative report instead of measuring a sound
# server and calling it hardware; then sink and device discovery; then the
# round-trip probe, gated the same way, through the discovered (or supplied)
# endpoints.
#
# Both reports are written alongside the existing loopback evidence, never in
# place of it — the default report paths describe the CI host and stay as
# they are.
#
# Exit codes:
#   0  both probes passed on physical hardware; reports published
#   1  no physical audio device (the usb probe's gate fired, or no hardware
#      sink / full-duplex physical device could be found)
#   2  hardware present but the round-trip run refused or failed
set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

REPORT_DIR="${HARDWARE_REPORT_DIR:-${ROOT_DIR}/.agent_workspace/v1.0/hardware}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
DEVICE="${CERT_DEVICE:-}"
SINK="${CERT_SINK:-}"

USB_PROBE="benchmarks/usb_audio_probe.py"
ROUNDTRIP_PROBE="benchmarks/roundtrip_latency_probe.py"

usage() {
  cat <<'EOF'
Usage: scripts/run-hardware-certification.sh [options]

Runs the C4 hardware certification described in docs/HARDWARE_CERTIFICATION.md:

  1. benchmarks/usb_audio_probe.py --require-physical
       proves a converter exists (kernel card + USB audio class interface +
       PortAudio device addressing the card) or exits 1 honestly.
  2. benchmarks/roundtrip_latency_probe.py --require-physical
       measures the round trip through the interface and the loopback cable,
       against the 15 ms / 128-frame budget.

Both reports are published under .agent_workspace/v1.0/hardware/, alongside
the loopback evidence at the probes' default paths — never in place of it.

Options:
  --device NAME       PortAudio device for the round trip (e.g.
                      "hw:CARD=USB,DEV=0"). Default: the first full-duplex
                      physical device in the usb probe's report.
  --sink NAME         PulseAudio hardware sink to verify the loop against.
                      Default: the first module-alsa-card sink pactl lists.
  --report-dir PATH   Where the two reports go
                      (default: .agent_workspace/v1.0/hardware).
  -h, --help          Show this help.

Environment:
  HARDWARE_REPORT_DIR, CERT_DEVICE, CERT_SINK   the same settings as above.
  PYTHON_BIN                                    interpreter (default python3).

This script measures nothing on a host without hardware: the usb probe's
--require-physical gate fires first, its honest not-certified report is still
written, and the script exits 1.
EOF
}

log() {
  printf '[hardware-certification] %s\n' "$*" >&2
}

fail() {
  local code="$1"
  shift
  log "$*"
  exit "$code"
}

while (($#)); do
  case "$1" in
    --device)
      [[ $# -ge 2 ]] || fail 2 "--device needs a value"
      DEVICE="$2"
      shift 2
      ;;
    --sink)
      [[ $# -ge 2 ]] || fail 2 "--sink needs a value"
      SINK="$2"
      shift 2
      ;;
    --report-dir)
      [[ $# -ge 2 ]] || fail 2 "--report-dir needs a value"
      REPORT_DIR="$2"
      shift 2
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      usage >&2
      fail 2 "unknown argument: $1"
      ;;
  esac
done

command -v "${PYTHON_BIN}" >/dev/null 2>&1 || fail 2 "${PYTHON_BIN} is not on PATH"

mkdir -p "${REPORT_DIR}"
USB_REPORT="${REPORT_DIR}/usb-audio-probe-report.json"
ROUNDTRIP_REPORT="${REPORT_DIR}/roundtrip-latency-report.json"

# ---------------------------------------------------- step 1: prove a converter

log "step 1/2: device inventory (${USB_PROBE} --require-physical)"
probe_status=0
"${PYTHON_BIN}" "${ROOT_DIR}/${USB_PROBE}" \
  --require-physical \
  --output "${USB_REPORT}" >/dev/null || probe_status=$?

if ((probe_status != 0)); then
  log "no physical audio device on this host; the honest negative inventory"
  log "is at ${USB_REPORT} and nothing was measured."
  log "To certify: attach a class-compliant USB interface and follow"
  log "docs/HARDWARE_CERTIFICATION.md."
  exit 1
fi
log "physical hardware proven; inventory at ${USB_REPORT}"

# --------------------------------------------- step 2a: find the hardware sink

if [[ -z "${SINK}" ]]; then
  command -v pactl >/dev/null 2>&1 \
    || fail 1 "pactl is not installed, so no hardware sink can be found; pass --sink"
  SINK="$(pactl list short sinks 2>/dev/null \
    | awk -F'\t' '$3 ~ /alsa/ && $3 !~ /null-sink/ {print $2; exit}')" || true
  [[ -n "${SINK}" ]] || fail 1 \
    "no sink backed by an ALSA card in 'pactl list short sinks'; pass --sink"
  log "hardware sink: ${SINK} (auto-discovered)"
else
  log "hardware sink: ${SINK} (supplied)"
fi

# ------------------------------------- step 2b: find the full-duplex device

if [[ -z "${DEVICE}" ]]; then
  DEVICE="$("${PYTHON_BIN}" - "${USB_REPORT}" <<'PYEOF'
import json
import sys

report = json.load(open(sys.argv[1], encoding="utf-8"))
for device in report["portaudio"]["devices"]:
    if (
        device["physical"]
        and device["max_input_channels"] > 0
        and device["max_output_channels"] > 0
    ):
        print(device["name"])
        break
PYEOF
)"
  [[ -n "${DEVICE}" ]] || fail 1 \
    "the inventory lists no full-duplex physical device; pass --device (see portaudio.devices in ${USB_REPORT})"
  log "round-trip device: ${DEVICE} (auto-discovered from the inventory)"
else
  log "round-trip device: ${DEVICE} (supplied)"
fi

# --------------------------------------------- step 2c: measure the round trip

log "step 2/2: round trip (${ROUNDTRIP_PROBE} --require-physical)"
roundtrip_status=0
"${PYTHON_BIN}" "${ROOT_DIR}/${ROUNDTRIP_PROBE}" \
  --require-physical \
  --device "${DEVICE}" \
  --sink "${SINK}" \
  --output "${ROUNDTRIP_REPORT}" >/dev/null || roundtrip_status=$?

if ((roundtrip_status != 0)); then
  fail 2 "the round-trip run refused or failed (exit ${roundtrip_status}); see the probe output above and docs/HARDWARE_CERTIFICATION.md troubleshooting"
fi

log "round-trip report at ${ROUNDTRIP_REPORT}"
log "hardware certification complete: commit both reports under ${REPORT_DIR}"
log "alongside the loopback evidence, never in place of it."
exit 0
