"""Audio Studio -- a professional audio editing and analysis workstation.

The package is split into a Qt-free core (:mod:`audio_studio.core`) holding the
decoding, transport and analysis primitives, and a Qt front-end
(:mod:`audio_studio.ui`). Keeping the boundary strict means the engine stays
unit-testable head-lessly and remains portable to a future C++/JUCE host.
"""

from __future__ import annotations

__version__ = "1.1.0"
__app_name__ = "Audio Studio"

__all__ = ["__app_name__", "__version__"]
