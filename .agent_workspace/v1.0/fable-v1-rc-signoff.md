# v1.0.0-rc Release Signoff — Round D (fable)

- **Date:** 2026-08-27
- **Branch:** `cursor/v1.0-round-d-b3cf` → merge to `cursor/audio-studio-v0.1.0-alpha-b3cf`
- **Version:** `1.0.0-rc` (`pyproject.toml` / `audio_studio.__version__`)

## Verdicts

| Claim | Verdict |
|---|---|
| **v1.0.0-rc professional workstation** | **Conditional Go** |
| **Audition-class / full SOTA (P0 20/20)** | **No-Go** |

### Conditional Go

The release candidate closes the post-beta roadmap items that can be evidenced headlessly:

- soxr VHQ SRC path (A5)
- True-peak limiter ISP vectors (A6)
- TPDF dither report (A7)
- Plugin host + PDC mock evidence (B6)
- Batch −16 LUFS (B7)
- Spectral repair suite (B5)
- Dock layout + keyboard workflow (D2/D3)
- UI scaling 100–200% (D5)
- Callback timing + 30-minute soak proxy (C1/C3)
- `.hlprojz` + installer scaffold (Round B)

**1661** application tests pass; SOTA checklist **19/30 items hard-pass**, **11 expected gaps** remain.

### No-Go (Audition-class)

Round 1 rule requires **P0 20/20**. Remaining P0 gaps need **real hardware** or formal artifacts we will not forge:

- B2 one-hour file performance (formal)
- B3 RF64 4 GB RSS (`formal_slo_verified` on dedicated hardware)
- C2 60-minute recording soak
- C4 hardware loopback RTT
- D1 60 fps frame-time report
- E2 three-platform golden comparison
- E4 crash recovery demo
- B1 M1–M13 manifest partials (M1/M5/M7/M12)
- A8 AES17 report

## Test evidence

| Suite | Result |
|---|---|
| Application | 1661 passed, 13 skipped |
| SOTA checklist | 20 passed, 11 xfailed, 0 xpass |
| Full tree | ~1780 passed (app + compliance + acceptance) |

## Tag instruction

Tag **`v1.0.0-rc`** on the merge commit after CI green. Do **not** claim SOTA acceptance or Audition parity in release notes.
