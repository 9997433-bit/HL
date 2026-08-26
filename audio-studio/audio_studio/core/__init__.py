"""Qt-free audio core: decoding, transport, buffering, editing and waveform summaries."""

from __future__ import annotations

from .edit_session import (
    AudioDocument,
    Chunk,
    CutCommand,
    DeleteCommand,
    EditCommand,
    EditError,
    EditSession,
    FadeCommand,
    GainCommand,
    InsertSilenceCommand,
    PasteCommand,
    ReverseCommand,
    Segment,
    SilenceCommand,
    TrimCommand,
    UndoStack,
)
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
from .markers import Marker, MarkerItem, MarkerList, Region
from .output import AudioOutput, NullOutput, OutputDeviceError, PyAudioOutput, create_output
from .peaks import Envelope, PeakPyramid
from .ring_buffer import RingBuffer
from .sample_source import (
    MemorySampleSource,
    SampleSource,
    StreamingSampleSource,
    open_source,
)
from .session import Clip, MasterBus, MultitrackSession, SessionMixer, Track
from .sounddevice_output import SoundDeviceOutput
from .sources import LoopSource, RegionSource
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
    "AudioDocument",
    "AudioEngine",
    "AudioFormat",
    "AudioLoadError",
    "AudioOutput",
    "Chunk",
    "Clip",
    "CutCommand",
    "DeleteCommand",
    "EditCommand",
    "EditError",
    "EditSession",
    "Envelope",
    "FadeCommand",
    "GainCommand",
    "InsertSilenceCommand",
    "LevelReading",
    "LoadedAudio",
    "LoopSource",
    "Marker",
    "MarkerItem",
    "MarkerList",
    "MasterBus",
    "MemorySampleSource",
    "MultitrackSession",
    "NullOutput",
    "OutputDeviceError",
    "PasteCommand",
    "PeakPyramid",
    "PyAudioOutput",
    "Region",
    "RegionSource",
    "ReverseCommand",
    "RingBuffer",
    "SampleSource",
    "Segment",
    "SessionMixer",
    "SilenceCommand",
    "SoundDeviceOutput",
    "StreamingSampleSource",
    "TimeRange",
    "Track",
    "TransportState",
    "TrimCommand",
    "UndoStack",
    "amplitude_to_db",
    "create_output",
    "db_to_amplitude",
    "file_dialog_filter",
    "format_timecode",
    "load_audio",
    "open_source",
    "probe",
    "resample",
    "save_audio",
    "supported_formats",
]
