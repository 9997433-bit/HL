"""Offline batch processing: glob in, operations per file, directory out.

The pipeline lives in :mod:`audio_studio.batch.pipeline`; the command-line
front end (``python -m audio_studio.batch.cli`` / ``audio-studio-batch``) in
:mod:`audio_studio.batch.cli`.
"""

from .macro import (
    EditMacro,
    MacroError,
    deserialize_macro,
    load_macro,
    save_macro,
    serialize_session,
)
from .pipeline import (
    ApplyGain,
    BatchJob,
    BatchReport,
    Fade,
    FileResult,
    NormalizeLoudness,
    Operation,
    process_file,
    run_batch,
)

__all__ = [
    "ApplyGain",
    "BatchJob",
    "BatchReport",
    "EditMacro",
    "Fade",
    "FileResult",
    "MacroError",
    "NormalizeLoudness",
    "Operation",
    "deserialize_macro",
    "load_macro",
    "process_file",
    "run_batch",
    "save_macro",
    "serialize_session",
]
