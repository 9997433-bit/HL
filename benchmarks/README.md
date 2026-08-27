# SLO and compliance benchmarks

`benchmarks/slo/` turns the key fable architecture §7 limits into executable,
headless probes. The suite uses `perf_counter_ns` directly, so it runs with
plain pytest and does not require the optional `pytest-benchmark` plugin.

Run the benchmark tests:

```bash
python3 -m pytest -q benchmarks/slo
```

Run all Round 2 validation and write the required JSON report:

```bash
python3 tools/run_round2_validation.py
```

The report is written atomically to
`.agent_workspace/round2/slo-compliance-report.json`.

## Coverage

| SLO | Executable probe | Formal limit represented |
| --- | --- | --- |
| L1 | 128-frame ring-buffer simulation and underrun counter | buffer ≤128; underruns <0.1% |
| T2 | callback queue p99 timing histogram | p99 <50% of 128/48 kHz block period |
| T1 | 32 stereo tracks, each with EQ + 3 gain effects | reference CPU <60% |
| T3 | four-effect offline render | ≥10× realtime |
| U2/U3 | 10 s stereo STFT, FFT 4096 | ≥30 analysis frames/s; ≥10× realtime |
| U1 | repeatable 60 s stereo PCM WAV decode | <2 s startup proxy |

Set `SLO_ENFORCE=1` to turn proxy threshold misses into pytest failures on a
controlled reference host. The JSON always records pass/fail against each
threshold even when pytest is in observational mode.

These cloud probes do **not** certify hardware SLOs. L1 still requires a
10-minute device run, T1 needs four-core CPU telemetry, L2 needs a physical or
virtual loopback, and U1 needs the one-hour waveform-visible workflow. U2/U3
measure STFT compute throughput rather than Qt paint cadence. Those limitations
are explicit in every JSON result so a proxy pass cannot be mistaken for formal
acceptance.

## Playback soak proxy

`benchmarks/soak_playback.py` plays a full session's worth of audio (default:
30 minutes at 48 kHz / 256-frame blocks) through the real engine — feeder
thread, ring buffer and the zero-allocation `render_into` device path — on the
`NullOutput` backend, then reports underruns/xruns and callback timing as
JSON:

```bash
python3 benchmarks/soak_playback.py                        # 30-minute soak
python3 benchmarks/soak_playback.py --duration-sec 60      # quick smoke
python3 benchmarks/soak_playback.py --wall-clock           # paced in real time
python3 benchmarks/soak_playback.py --output soak.json
```

The default accelerated mode acts as the device clock itself: before every
block the feeder gets at most one block period of catch-up budget — the same
real-time budget a hardware callback cycle would give it — so a feeder that
could not keep a real device fed still shows up as underruns, without the run
taking 30 wall-clock minutes. The run fails (exit code 1) when zero-filled
frames exceed `--max-underrun-ratio` (default 0.1%).

Like the SLO probes above, this is a headless **proxy**: it soaks the software
pipeline for a full session of audio but is not hardware playback-stability
evidence. The approved v1.0 acceptance policy treats it as formal
software-pipeline evidence for C1/C3. Every run writes the standalone
`.agent_workspace/v1.0/soak-30min-report.json` and
`.agent_workspace/v1.0/callback-timing-report.json` artifacts.

## EBU and golden tests

```bash
python3 -m pytest -q tests/compliance tests/golden
```

`tools/ebu_r128.py` is an independent BS.1770/EBU R128 oracle.
`tests/compliance/test_ebu3341.py` synthesizes Tech 3341 cases 1–3 and applies
the normative ±0.1 LU tolerance. `test_ebu3342.py` implements case 1 and keeps
the remaining vector definitions as the expansion skeleton; Tech 3342's
normative LRA tolerance is ±1 LU.

The application currently has no production loudness meter. These tests prove
the vector generator and oracle, not product EBU compliance; the report states
`product_compliance_claimed: false`.

The golden framework fingerprints WAV format fields and hashes the encoded
`data` chunk. Null tests cover PCM 16-bit, PCM 24-bit, and 32-bit float
import→no-op→export and fail on any changed sample bit.

`tools/benchmark_audio.py` remains the lightweight Round 1 fixture baseline.
The SLO suite adds application STFT/effect/load paths and explicit §7 mapping.
