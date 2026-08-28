# Song audio provenance

The thirteen `*-melody.ogg` files in this directory are original project assets, rendered
from the project-authored note sequences in `src/data/songs.js`. They contain no
third-party recordings or samples.

Run `python3 apps/literacy-app/scripts/generate-song-audio.py` from the repository
root to reproduce them. The renderer uses additive synthesis and FFmpeg's Vorbis
encoder; FFmpeg is only a development-time generation tool and is not shipped in
the application.

The three `*-vocal-*.ogg` files are synthetic “la” vocal guides. Round 12
introduced `sg5-literacy-vocal-pilot.ogg`; Round 13 added the `sg1` and `sg3`
guides. They were rendered offline with Piper 1.7.0 and the
`sv_SE-nst-medium` voice, then pitch-shifted to each project-authored melody.
The voice model was trained from scratch by KBLab from the National Library of
Sweden's CC0 NST dataset. Neither the model nor Piper ships in the app; only
the generated Ogg files do. Exact inputs, hashes, commands, and scope limits
are recorded in `.agent_workspace/r12-songs-vocal-pilot.md` and
`.agent_workspace/r13-vocal-batch.md`.
