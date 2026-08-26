"""Qt-free audio core: decoding, transport, buffering and waveform summaries."""

from __future__ import annotations

from .engine import AudioEngine
from .loader import (
    SUPPORTED_EXTENSIONS,
    AudioLoadError,
    LoadedAudio,
    file_dialog_filter,
    load_audio,
    probe,
    resample,
    save_audio,
    supported_formats,
)
from .output import AudioOutput, NullOutput, OutputDeviceError, PyAudioOutput, create_output
from .peaks import Envelope, PeakPyramid
from .ring_buffer import RingBuffer
from .types import (
    AudioBuffer,
    AudioFormat,
    LevelReading,
    TimeRange,
    TransportState,
    amplitude_to_db,
    db_to_amplitude,
    format_timecode,
)

__all__ = [
    "SUPPORTED_EXTENSIONS",
    "AudioBuffer",
    "AudioEngine",
    "AudioFormat",
    "AudioLoadError",
    "AudioOutput",
    "Envelope",
    "LevelReading",
    "LoadedAudio",
    "NullOutput",
    "OutputDeviceError",
    "PeakPyramid",
    "PyAudioOutput",
    "RingBuffer",
    "TimeRange",
    "TransportState",
    "amplitude_to_db",
    "create_output",
    "db_to_amplitude",
    "file_dialog_filter",
    "format_timecode",
    "load_audio",
    "probe",
    "resample",
    "save_audio",
    "supported_formats",
]
