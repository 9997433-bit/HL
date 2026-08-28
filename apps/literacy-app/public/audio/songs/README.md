# Song audio provenance

The thirteen `*-melody.ogg` files in this directory are original project assets, rendered
from the project-authored note sequences in `src/data/songs.js`. They contain no
third-party recordings or samples.

Run `python3 apps/literacy-app/scripts/generate-song-audio.py` from the repository
root to reproduce them. The renderer uses additive synthesis and FFmpeg's Vorbis
encoder; FFmpeg is only a development-time generation tool and is not shipped in
the application.

All thirteen `*-vocal-human.ogg` files (`sg1`–`sg13`) are vowel guides adapted
from a studio recording by an anonymous professional singer in VocalSet 1.2.
The pinned source is the straight-vowel C-major arpeggio exposed as
`Bill13579/vocalset-mirror`, `default/train` row 55 (source SHA-256
`451381cd80d9006251a3af694251abb9c756bafa5051130635142abbc210f3de`).
VocalSet is © Julia Wilkins, Prem Seetharaman, Alison Wahl, and Bryan Pardo,
licensed CC BY 4.0 at <https://doi.org/10.5281/zenodo.1442513>. This project
trimmed four steady notes, tuned them, time-stretched them to the authored
rhythm, assembled each guide, and normalized loudness. These are real-human
vowel performances, not Chinese-lyric recordings. Reproduction commands,
output hashes, and modification details are in
`.agent_workspace/r14-songs-vocal-full.md`.

Round 12 and Round 13 shipped synthetic “la” guides for `sg1`, `sg3`, and `sg5`
(`sg1-climb-vocal-guide.ogg`, `sg3-wash-hands-vocal-guide.ogg`,
`sg5-literacy-vocal-pilot.ogg`), rendered offline with Piper 1.7.0 and the
`sv_SE-nst-medium` voice. Round 14 replaced all three with human-source guides
and removed the Piper Ogg files from the package; the generator still supports
that path via `--model`/`--config`, and the historical inputs, hashes, and
commands stay recorded in `.agent_workspace/r12-songs-vocal-pilot.md` and
`.agent_workspace/r13-vocal-batch.md`.
