# Audio probes and fixtures

The probe scripts use only the Python standard library. Run commands from the
repository root with Python 3.11 or newer.

## Generate deterministic fixtures

```bash
python tools/generate_fixtures.py
```

This writes 16-bit PCM WAV files to `tests/fixtures/` at both 44.1 kHz and
48 kHz:

- linear 20 Hz–20 kHz sine sweep
- seeded white noise
- digital silence
- deliberately clipped 997 Hz sine
- 110/440/1,000/7,500/15,000 Hz mixture
- stereo 1 kHz tone with a 90-degree right-channel phase offset

The default duration is one second. The output is reproducible across runs.
Useful overrides are:

```bash
python tools/generate_fixtures.py --duration 2
python tools/generate_fixtures.py --sample-rates 48000 --output-dir /tmp/wav
```

## Run the baseline benchmark

```bash
python tools/benchmark_audio.py
```

The command validates and loads every fixture, runs a standard-library radix-2
FFT workload, estimates startup latency, and records Python allocation and
process peak-memory metrics. Its JSON output is written to
`.agent_workspace/round1/benchmark-baseline.json`.

Playback latency is an estimate, not a sound-device measurement. It is the
median validated file-load time plus one configured output buffer
(`512 / sample_rate` by default). Compare benchmark runs on the same machine
and Python build; absolute timings and process RSS are host-dependent.

Common tuning options:

```bash
python tools/benchmark_audio.py \
  --load-repetitions 10 \
  --fft-size 4096 \
  --fft-iterations 100 \
  --buffer-frames 256 \
  --output /tmp/audio-benchmark.json
```

The loader rejects malformed/truncated files, non-PCM data, sample rates
outside 8–384 kHz, more than 32 channels, and declared inputs above its frame
safety limit before reading the payload.

## Run probes in tests

```bash
python -m pytest -q tests/test_boundary.py
```

The boundary suite uses small synthetic headers to exercise empty files,
corrupt headers, truncated PCM, extreme sample-rate metadata, and a simulated
oversized file without allocating a large fixture.
