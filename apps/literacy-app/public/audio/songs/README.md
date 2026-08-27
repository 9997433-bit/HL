# Song audio provenance

The three `.ogg` files in this directory are original project assets, rendered
from the project-authored note sequences in `src/data/songs.js`. They contain no
third-party recordings or samples.

Run `python3 apps/literacy-app/scripts/generate-song-audio.py` from the repository
root to reproduce them. The renderer uses additive synthesis and FFmpeg's Vorbis
encoder; FFmpeg is only a development-time generation tool and is not shipped in
the application.
