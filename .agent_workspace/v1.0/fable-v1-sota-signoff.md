# v1.0.1 SOTA Signoff — Round F (fable)

- **Date:** 2026-08-27
- **Branch:** `cursor/v1.0-round-f-b3cf` → merge to alpha
- **Version:** `1.0.1`
- **Tag:** `v1.0.1-sota`

## Verdicts

| Claim | Verdict |
|---|---|
| **SOTA checklist 30/30 automated** | **Go** |
| **v1.0.1 professional workstation** | **Go** |
| **Adobe Audition parity** | **No-Go** (product scope, not checklist) |

## Round F evidence (four former gaps)

| ID | Evidence | Caveat |
|---|---|---|
| B3 | Dense 4.4 GB RF64, peak RSS 127 MiB, `formal_slo_verified: true` | Linux VM; dense chunked write, not a field recorder capture |
| C2 | 60 min PortAudio recording, 172M frames, 0 xruns | PulseAudio null-sink monitor input, not physical ADC |
| C4 | 8.17 ms worst RTT at 128 frames | PulseAudio loopback; `physical_dac_adc: false` in report |
| D4 | Live Orca 46.1 + AT-SPI, 60 utterances | Linux only; NVDA/VoiceOver not run |

## Test evidence

| Suite | Result |
|---|---|
| Application | 1721 passed, 12 skipped |
| SOTA checklist | **31 passed** (30 items + structural), **0 xfailed** |

## Honest positioning

All 30 SOTA checklist items now pass as **automated, reproducible assertions** with
committed JSON evidence. That is not the same as claiming Adobe Audition feature parity,
broadcast facility certification on every OS, or NVDA/VoiceOver sign-off on Windows/macOS.

## Tag instruction

Tag **`v1.0.1-sota`** on merge commit after CI green.
