# v1.0.0 Formal Release Signoff — Round E (fable)

- **Date:** 2026-08-27
- **Branch:** `cursor/v1.0-round-e-b3cf` → merge to `cursor/audio-studio-v0.1.0-alpha-b3cf`
- **Version:** `1.0.0` (`pyproject.toml` / `audio_studio.__version__`)

## Verdicts

| Claim | Verdict |
|---|---|
| **v1.0.0 professional workstation** | **Go** |
| **Audition-class / full SOTA (P0 20/20)** | **No-Go** |

### Go (professional workstation)

Round E closes every headless-evidence gap that can be demonstrated without
forging hardware runs:

- A8 AES17 THD+N report
- B1 M1–M13 manifest (13/13 with honest hardware caveats cross-referenced)
- B2 one-hour file performance (`formal_slo_verified: true` headless run)
- B8 32-track playback and automation
- D1 60 fps frame-time report (6.2 ms worst p99 vs 16 ms budget)
- E2 three-platform DSP golden matrix (real CI artifacts)
- E4 crash auto-recovery (SIGKILL trials + clean-exit control)
- D4 screen-reader **readiness** proxy (accessible names/roles; live NVDA/VO/Orca still open)

**1713** application tests pass; SOTA checklist **27/30 hard-pass**, **4 expected gaps**.

### No-Go (Audition-class)

Four items require real hardware or live assistive-technology sessions:

| ID | Gap |
|---|---|
| B3 | Dedicated RF64 4 GB RSS run (`formal_slo_verified: true`) |
| C2 | 60-minute recording stability soak |
| C4 | Hardware loopback round-trip latency |
| D4 | Live NVDA / VoiceOver / Orca walkthrough |

Round 1 P0 20/20 rule is not satisfied until those four are closed on target hardware.

## Test evidence

| Suite | Result |
|---|---|
| Application | 1713 passed, 13 skipped |
| SOTA checklist | 27 passed, 4 xfailed, 0 xpass |
| Full tree | ~1850 passed |

## Tag instruction

Tag **`v1.0.0`** on the merge commit after CI green. Release notes must not claim Audition parity or full SOTA acceptance.
