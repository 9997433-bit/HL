# HL

Multi-agent build of **Audio Studio** — a professional audio editing and
analysis workstation, benchmarked against Adobe Audition.

| Where | What |
|---|---|
| [`audio-studio/`](audio-studio/) | The product: PySide6 waveform editor, streaming playback engine, undoable COW editing, EQ/gain/normalize/fade effects, spectral analysis and a BS.1770-4 loudness meter |
| [`tests/`](tests/), [`benchmarks/`](benchmarks/), [`tools/`](tools/) | EBU 3341/3342 compliance vectors and oracle, bit-exact null tests, SLO suite, a 30-minute headless playback soak proxy (`benchmarks/soak_playback.py`), performance-regression and realtime escape-hatch gates |
| [`.agent_workspace/`](.agent_workspace/) | Multi-agent coordination: architecture contract, SOTA audits, convergence reviews, release sign-off and roadmap |

**Status:** working toward `v0.1.0-alpha` — a single-track waveform editor and
analyzer (not yet a multitrack DAW). Release scope, known limitations and the
post-MVP roadmap (v0.2 multitrack → v0.3 VST3/repair → v1.0 SOTA alignment)
are defined in
[`.agent_workspace/round3/fable-release-signoff.md`](.agent_workspace/round3/fable-release-signoff.md).
Release history lives in [`CHANGELOG.md`](CHANGELOG.md); the project is MIT
with third-party obligations tracked in
[`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md).

Quick start:

```bash
cd audio-studio
pip install -e ".[dev]"
python -m audio_studio            # see audio-studio/README.md for details
```
