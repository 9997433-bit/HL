# Shared placeholder assets

All production code should reference assets from this directory by relative URL so both education apps can
run offline.

## Third-party assets

### OpenMoji SVGs (`openmoji/`)

Source: <https://github.com/hfg-gmuend/openmoji>

Files: `apple.svg`, `target.svg`, `open-book.svg`, `numbers.svg`, `abacus.svg`, `star.svg`.
They are unmodified copies renamed from their Unicode code-point filenames.

> All emojis designed by [OpenMoji](https://openmoji.org/) – the open-source emoji and icon project.
> License: [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).

The complete license is in `openmoji/LICENSE.txt`. Any adapted versions must retain attribution, indicate
changes, and use CC BY-SA 4.0.

### Hanzi Writer data samples (`hanzi-writer-data/`)

Source: <https://github.com/chanind/hanzi-writer-data>

`人.json`, `日.json`, and `山.json` were downloaded through the official jsDelivr npm endpoint as small
offline fixtures. They are covered by the Arphic Public License, included as
`hanzi-writer-data/ARPHICPL.TXT`. Keep that license with every redistributed copy.

### Noto Sans SC license (`fonts/`)

`fonts/OFL-NotoSansSC.txt` is the SIL Open Font License 1.1 from
<https://github.com/google/fonts/tree/main/ofl/notosanssc>. No font binary is vendored in this probe.
When a pinned font file or subset is added, keep this notice beside it.

## Locally generated placeholders

- `audio/tap.wav`: short decaying tap.
- `audio/success.wav`: C-major success chord.
- `audio/try-again.wav`: quiet descending retry cue.
- `lottie/celebration.json`: a simple animated star composed only of Lottie vector primitives.

The WAV files were synthesized from sine functions at 44.1 kHz; they contain no sampled recording.
The Lottie file was authored for this repository and contains no imported artwork. These placeholders can
be used, changed, or replaced with the application code.

## Production notes

- Keep effects below speech volume and expose mute controls.
- Do not use sound as the only correct/incorrect indicator.
- Lock third-party assets to a release or commit instead of `master`/`latest`.
- Optimize SVGs only if the optimizer preserves attribution records and visual correctness.
