## Suggested title

`Audio Studio v0.1.0-alpha: three-round MVP, validation, and release policy`

## Summary

This PR turns the greenfield audio-analysis branch into a testable Audio Studio
alpha. It combines a Qt desktop shell, Qt-free playback/editing core, waveform
and spectral analysis, foundational DSP/loudness, streaming sources, SPSC
transport, compliance/performance harnesses, and release/license documentation.

This is intentionally an **alpha**, not an Adobe Audition parity claim. The
remaining product, hardware, platform, and compliance gaps are explicit in
`.agent_workspace/FINAL_SUMMARY.md`.

Final merged HEAD: `<!-- fill commit SHA -->`  
Final fable verdict: `<!-- pass / conditional / fail + report link -->`

## What changed

### Round 1 — MVP foundation

- Audio loading/export and ffmpeg subprocess fallback
- Ring-buffered transport with Null and optional PyAudio output
- Cached waveform, selection, zoom, timeline, meter, shortcuts and dark UI
- STFT/iSTFT, window library, spectrogram/waterfall and color maps
- Gain/normalize/fade/EQ effects and integration tests
- Fixtures, boundary probes, benchmark baseline and architecture/SOTA specs

### Round 2 — architecture convergence

- PyQt6 → PySide6-Essentials migration
- Lock-free SPSC queue and caller-owned `read_into` render path
- Memory/disk-streaming `SampleSource` implementations
- Copy-on-write `EditSession`, reversible commands and deep undo/redo
- Dockable spectrum/effects panels and live wet/dry/bypass preview
- Product BS.1770 loudness/LRA and optimized true-peak evaluation
- Spectrogram render caches
- Independent EBU/null/SLO validation, CI matrix and performance gates

### Round 3 — final integrated scope

> Orchestrator: update this subsection from the actual merged Round 3 diffs.
> Do not mark dispatched work as delivered.

- [ ] Multitrack Session MVP: `<!-- merged SHA or "not merged" -->`
- [ ] Product BS.1770/repair additions: `<!-- merged SHA or "not merged" -->`
- [x] CI repair and acceptance automation: `b20e34d`, `772dec1`
- [x] Third-party license inventory and distribution policy
- [x] Changelog, global summary and PR handoff template
- [x] Final same-host Round 1 performance delta
- [ ] Final fable SOTA/architecture reports: `<!-- paths -->`

## Key files

- `audio-studio/audio_studio/core/` — engine, sample sources, edits, SPSC queue
- `audio-studio/audio_studio/dsp/` — effects, spectra and loudness
- `audio-studio/audio_studio/ui/` — waveform, docks, transport and meters
- `tests/`, `benchmarks/`, `tools/` — correctness, compliance and performance
- `THIRD_PARTY_LICENSES.md` — dependency notices and distribution rules
- `CHANGELOG.md` — `0.1.0-alpha` three-round history
- `.agent_workspace/FINAL_SUMMARY.md` — architecture, evidence, gaps and roadmap
- `.agent_workspace/round3/ci-acceptance-report.json` — 30-item acceptance state
- `.agent_workspace/round3/final-perf-delta.json` — final baseline comparison

## Verification

### Required commands

```bash
python -m pip install --requirement .github/requirements.lock
python -m pip install --no-deps --editable ./audio-studio

ruff check tools scripts tests
QT_QPA_PLATFORM=offscreen pytest -q tests audio-studio/tests
python tools/run_round3_acceptance.py \
  --output .agent_workspace/round3/ci-acceptance-report.json

python tools/benchmark_audio.py \
  --output .agent_workspace/round3/benchmark-final.json
python tools/perf-regression.py \
  .agent_workspace/round3/benchmark-final.json \
  --output .agent_workspace/round3/final-perf-delta.json \
  --fail-on-regression
```

Final local result:

- Tests: `659 passed, 23 xfailed, 1 xpassed in 6.38s` (Linux/Python 3.12,
  Qt offscreen; xfails are audited missing evidence)
- Round 3 acceptance: `7 evidenced, 23 expected gaps, sota_claimed=false`
- Ruff: pass
- GUI smoke: `python -m audio_studio --null-audio --offscreen --exit-after 5`
  exited 0
- CI: `<!-- workflow URL; all matrix jobs must be green -->`

### Performance result in this branch snapshot

The Round 3 benchmark uses the same Python `3.12.3`, host description, fixtures,
FFT workload and buffer configuration as Round 1. `comparison_valid` is true.

| Classification | Count |
|---|---:|
| Regression (>10% adverse) | 0 |
| Improvement (>10% favorable) | 0 |
| Stable | 9 |
| Incomparable | 0 |

The delta covers fixture loading, stdlib FFT throughput, Python allocation/RSS
and modeled one-buffer startup. It is not a physical-device RTT or long soak.

## License and distribution review

- [x] Default `pyproject` dependencies contain no PyQt6 or pedalboard.
- [x] PySide6/Qt/Shiboken and libsndfile LGPL use is dynamic and replaceable.
- [x] Corresponding-source/relinking instructions and upstream license pointers
  are recorded.
- [x] pedalboard is documented as absent/non-default; bundling it requires a
  GPL-3.0 combined distribution.
- [x] ASIO SDK is absent and `SD_ENABLE_ASIO` is not enabled by the project.
- [x] FFmpeg remains a discovered subprocess; no GPL/nonfree build is bundled.
- [x] Dependency manifests and the CI lock are reconciled in
  `THIRD_PARTY_LICENSES.md`.
- [ ] Final artifact SBOM/notices reviewed if this PR creates binary artifacts.

## Known limitations / non-claims

- No claim of Adobe Audition feature parity.
- No hardware-certified RTT, dropout/recording soak, or ASIO support.
- No complete multitrack/mixer, recording, project recovery, batch, or
  production plugin-host workflow unless the corresponding Round 3 commit is
  present and tested above.
- EBU/AES/SRC/dither acceptance remains partial unless the final fable report
  cites passing automated evidence.
- Streaming playback does not yet prove an end-to-end RF64/>4 GB out-of-core
  edit/analyze/export workflow.
- Accessibility/HiDPI and installer signing/SBOM gates remain open.

## Reviewer guide

1. Confirm the final diff matches the Round 3 checkbox claims.
2. Review `THIRD_PARTY_LICENSES.md` against the final manifests; any newly
   introduced dependency must be added before approval.
3. Inspect `core/ring_buffer.py`, `core/sample_source.py` and
   `core/edit_session.py` for realtime and revision-boundary invariants.
4. Compare product loudness code with the independent compliance oracle; shared
   implementation code would invalidate the oracle.
5. Open the performance delta and confirm `comparison_valid: true`,
   `regression: 0`, and no warnings.
6. Require the Linux/macOS/Windows tests, GUI smoke and performance jobs on the
   final SHA. Historical green runs do not validate the merged HEAD.

## Merge gates

- [ ] All expected Round 3 branches merged and this body updated
- [ ] Full test suites pass on the final SHA
- [ ] Linux, macOS and Windows CI matrix green
- [ ] Null-audio GUI smoke green
- [ ] Final performance delta has no >10% adverse regression
- [ ] fable final audit attached and blocking findings resolved/documented
- [ ] `THIRD_PARTY_LICENSES.md` still matches every final dependency manifest
- [ ] No secret, generated cache, proprietary SDK, or unreviewed binary added

If any required gate remains unchecked, keep the PR draft/blocked and describe
the owner plus concrete missing evidence.
