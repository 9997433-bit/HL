"""The sounddevice output backend and the ``create_output()`` selection ladder.

The device tests drive :class:`SoundDeviceOutput` against a synthetic stream
injected as ``sys.modules["sounddevice"]``, so the callback contract, the
padding rules and the xrun counters are exercised on a machine with no sound
card. The few checks that need the real binding are skipped when it is absent.
"""

from __future__ import annotations

import sys
import types
from typing import Any

import numpy as np
import pytest

from audio_studio.core import output as output_module
from audio_studio.core import sounddevice_output as sounddevice_module
from audio_studio.core.output import (
    OUTPUT_BACKEND_ENV_VAR,
    AudioOutput,
    NullOutput,
    OutputDeviceError,
    create_output,
)
from audio_studio.core.sounddevice_output import SoundDeviceOutput

SAMPLE_RATE = 48000
CHANNELS = 2
BLOCK = 256
REPORTED_LATENCY = 0.0123


# --------------------------------------------------------------------------- #
# Synthetic PortAudio stream
# --------------------------------------------------------------------------- #


class FakeStatus:
    """Stand-in for ``sounddevice.CallbackFlags``."""

    def __init__(self, *, output_underflow: bool = False, output_overflow: bool = False) -> None:
        self.output_underflow = output_underflow
        self.output_overflow = output_overflow

    def __bool__(self) -> bool:
        return self.output_underflow or self.output_overflow


class FakeOutputStream:
    """Records how the backend configured the device and replays its callback."""

    def __init__(self, **kwargs: Any) -> None:
        self.config = kwargs
        self.channels: int = kwargs["channels"]
        self.blocksize: int = kwargs["blocksize"]
        self.callback = kwargs["callback"]
        self.latency = REPORTED_LATENCY
        self.active = False
        self.closed = False

    def start(self) -> None:
        self.active = True

    def stop(self) -> None:
        self.active = False

    def close(self) -> None:
        self.active = False
        self.closed = True

    def pump(self, frames: int | None = None, status: FakeStatus | None = None) -> np.ndarray:
        """Invoke the render callback the way PortAudio would."""
        n = self.blocksize if frames is None else frames
        outdata = np.full((n, self.channels), np.nan, dtype=np.float32)
        self.callback(outdata, n, None, status or FakeStatus())
        return outdata


class FakeSoundDevice(types.ModuleType):
    """Minimal ``sounddevice`` module exposing only what the backend touches."""

    def __init__(self, *, open_error: Exception | None = None) -> None:
        super().__init__("sounddevice")
        self.open_error = open_error
        self.attempted_block_sizes: list[int] = []
        self.streams: list[FakeOutputStream] = []

    def OutputStream(self, **kwargs: Any) -> FakeOutputStream:  # noqa: N802 - mirrors the binding
        self.attempted_block_sizes.append(kwargs["blocksize"])
        if self.open_error is not None:
            raise self.open_error
        stream = FakeOutputStream(**kwargs)
        self.streams.append(stream)
        return stream


@pytest.fixture()
def fake_sd(monkeypatch: pytest.MonkeyPatch) -> FakeSoundDevice:
    module = FakeSoundDevice()
    monkeypatch.setitem(sys.modules, "sounddevice", module)
    return module


def ramp(n_frames: int, channels: int = CHANNELS) -> np.ndarray:
    """Distinct, easily-compared block: channel c holds ``i + c``."""
    column = np.arange(n_frames, dtype=np.float32)[:, np.newaxis]
    return column + np.arange(channels, dtype=np.float32)


def open_backend(
    callback: Any, *, channels: int = CHANNELS, block_size: int = BLOCK
) -> SoundDeviceOutput:
    backend = SoundDeviceOutput()
    backend.open(SAMPLE_RATE, channels, callback, block_size=block_size)
    return backend


# --------------------------------------------------------------------------- #
# Stream lifecycle
# --------------------------------------------------------------------------- #


def test_open_requests_a_float32_callback_stream(fake_sd: FakeSoundDevice) -> None:
    backend = open_backend(ramp)
    try:
        assert len(fake_sd.streams) == 1
        config = fake_sd.streams[0].config
        assert config["samplerate"] == SAMPLE_RATE
        assert config["channels"] == CHANNELS
        assert config["dtype"] == "float32"
        assert config["blocksize"] == BLOCK
        assert config["device"] is None
        assert backend.is_open
        assert not backend.is_running
    finally:
        backend.close()


def test_block_size_is_configurable(fake_sd: FakeSoundDevice) -> None:
    backend = open_backend(ramp, block_size=64)
    try:
        assert backend.block_size == 64
        assert fake_sd.streams[0].config["blocksize"] == 64
    finally:
        backend.close()


def test_default_block_size_falls_back_when_the_device_rejects_256(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class RejectLowLatencyBlock(FakeSoundDevice):
        def OutputStream(self, **kwargs: Any) -> FakeOutputStream:  # noqa: N802
            self.attempted_block_sizes.append(kwargs["blocksize"])
            if kwargs["blocksize"] == 256:
                raise RuntimeError("unsupported block size")
            stream = FakeOutputStream(**kwargs)
            self.streams.append(stream)
            return stream

    module = RejectLowLatencyBlock()
    monkeypatch.setitem(sys.modules, "sounddevice", module)
    backend = SoundDeviceOutput()
    backend.open(SAMPLE_RATE, CHANNELS, ramp)
    try:
        assert module.attempted_block_sizes == [256, 512]
        assert backend.block_size == 512
    finally:
        backend.close()


def test_pyaudio_default_block_size_falls_back_through_1024(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempts: list[int] = []

    class FakeStream:
        def start_stream(self) -> None:
            pass

        def stop_stream(self) -> None:
            pass

        def close(self) -> None:
            pass

    class FakePyAudioInstance:
        def open(self, **kwargs: Any) -> FakeStream:
            block_size = kwargs["frames_per_buffer"]
            attempts.append(block_size)
            if block_size < 1024:
                raise RuntimeError("unsupported block size")
            return FakeStream()

        def terminate(self) -> None:
            pass

    module = types.ModuleType("pyaudio")
    module.paFloat32 = 1  # type: ignore[attr-defined]
    module.paContinue = 0  # type: ignore[attr-defined]
    module.PyAudio = FakePyAudioInstance  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "pyaudio", module)
    backend = output_module.PyAudioOutput()
    backend.open(SAMPLE_RATE, CHANNELS, ramp)
    try:
        assert attempts == [256, 512, 1024]
        assert backend.block_size == 1024
    finally:
        backend.close()


def test_start_stop_close_track_the_device(fake_sd: FakeSoundDevice) -> None:
    backend = open_backend(ramp)
    stream = fake_sd.streams[0]

    backend.start()
    assert backend.is_running and stream.active

    backend.stop()
    assert not backend.is_running and not stream.active

    backend.close()
    assert stream.closed
    assert not backend.is_open


def test_start_before_open_raises() -> None:
    with pytest.raises(OutputDeviceError):
        SoundDeviceOutput().start()


def test_open_failure_is_wrapped_and_leaves_no_stream(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(
        sys.modules, "sounddevice", FakeSoundDevice(open_error=RuntimeError("no device"))
    )
    backend = SoundDeviceOutput()
    with pytest.raises(OutputDeviceError, match="Cannot open output stream"):
        backend.open(SAMPLE_RATE, CHANNELS, ramp)
    assert backend._stream is None  # noqa: SLF001 - teardown is the property under test


def test_missing_binding_raises_output_device_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "sounddevice", None)
    with pytest.raises(OutputDeviceError, match="sounddevice is unavailable"):
        SoundDeviceOutput().open(SAMPLE_RATE, CHANNELS, ramp)


def test_invalid_format_is_rejected_before_the_device_is_touched(
    fake_sd: FakeSoundDevice,
) -> None:
    with pytest.raises(OutputDeviceError):
        SoundDeviceOutput().open(0, CHANNELS, ramp)
    assert fake_sd.streams == []


# --------------------------------------------------------------------------- #
# Render callback contract
# --------------------------------------------------------------------------- #


def test_callback_writes_the_rendered_block(fake_sd: FakeSoundDevice) -> None:
    backend = open_backend(ramp)
    try:
        rendered = fake_sd.streams[0].pump()
        assert rendered.dtype == np.float32
        np.testing.assert_array_equal(rendered, ramp(BLOCK))
    finally:
        backend.close()


def test_short_render_is_zero_padded(fake_sd: FakeSoundDevice) -> None:
    backend = open_backend(lambda n: ramp(n // 2))
    try:
        rendered = fake_sd.streams[0].pump()
        np.testing.assert_array_equal(rendered[: BLOCK // 2], ramp(BLOCK // 2))
        assert np.all(rendered[BLOCK // 2 :] == 0.0)
    finally:
        backend.close()


def test_raising_render_yields_silence_instead_of_aborting(fake_sd: FakeSoundDevice) -> None:
    def explode(_n: int) -> np.ndarray:
        raise ValueError("engine fell over")

    backend = open_backend(explode)
    try:
        rendered = fake_sd.streams[0].pump()
        assert np.all(rendered == 0.0)
        assert not fake_sd.streams[0].closed
    finally:
        backend.close()


def test_channel_mismatch_is_silenced_not_raised(fake_sd: FakeSoundDevice) -> None:
    """A mono render into a stereo device fills channel 0 and mutes the rest."""
    backend = open_backend(lambda n: np.arange(n, dtype=np.float32))
    try:
        rendered = fake_sd.streams[0].pump()
        np.testing.assert_array_equal(rendered[:, 0], np.arange(BLOCK, dtype=np.float32))
        assert np.all(rendered[:, 1] == 0.0)
    finally:
        backend.close()


def test_closed_backend_renders_silence(fake_sd: FakeSoundDevice) -> None:
    backend = open_backend(ramp)
    stream = fake_sd.streams[0]
    backend.close()
    assert np.all(stream.pump() == 0.0)


# --------------------------------------------------------------------------- #
# xrun accounting
# --------------------------------------------------------------------------- #


def test_clean_callbacks_report_no_xruns(fake_sd: FakeSoundDevice) -> None:
    backend = open_backend(ramp)
    try:
        for _ in range(4):
            fake_sd.streams[0].pump()
        assert backend.xruns == 0
        assert backend.underflows == 0
        assert backend.overflows == 0
    finally:
        backend.close()


def test_status_flags_are_counted(fake_sd: FakeSoundDevice) -> None:
    backend = open_backend(ramp)
    stream = fake_sd.streams[0]
    try:
        stream.pump(status=FakeStatus(output_underflow=True))
        stream.pump(status=FakeStatus(output_underflow=True))
        stream.pump(status=FakeStatus(output_overflow=True))
        stream.pump()
        assert backend.underflows == 2
        assert backend.overflows == 1
        assert backend.xruns == 3
    finally:
        backend.close()


def test_reopening_resets_the_counters(fake_sd: FakeSoundDevice) -> None:
    backend = open_backend(ramp)
    try:
        fake_sd.streams[0].pump(status=FakeStatus(output_underflow=True))
        assert backend.xruns == 1
        backend.open(SAMPLE_RATE, CHANNELS, ramp, block_size=BLOCK)
        assert backend.xruns == 0
    finally:
        backend.close()


# --------------------------------------------------------------------------- #
# Latency reporting
# --------------------------------------------------------------------------- #


def test_latency_prefers_the_device_report(fake_sd: FakeSoundDevice) -> None:
    backend = open_backend(ramp)
    try:
        assert backend.latency == pytest.approx(REPORTED_LATENCY)
    finally:
        backend.close()


def test_latency_falls_back_to_the_nominal_estimate(fake_sd: FakeSoundDevice) -> None:
    backend = open_backend(ramp)
    fake_sd.streams[0].latency = 0.0
    assert backend.latency == pytest.approx(BLOCK / SAMPLE_RATE)
    backend.close()
    assert backend.latency == pytest.approx(BLOCK / SAMPLE_RATE)


def test_duplex_latency_tuple_uses_the_output_element(fake_sd: FakeSoundDevice) -> None:
    backend = open_backend(ramp)
    try:
        fake_sd.streams[0].latency = (0.5, 0.25)
        assert backend.latency == pytest.approx(0.25)
    finally:
        backend.close()


# --------------------------------------------------------------------------- #
# The real binding, when it is installed
# --------------------------------------------------------------------------- #


def test_is_available_matches_the_import() -> None:
    try:
        import sounddevice  # noqa: F401
    except Exception:  # noqa: BLE001 - a missing PortAudio library is the point
        assert not SoundDeviceOutput.is_available()
    else:
        assert SoundDeviceOutput.is_available()


def test_real_binding_opens_or_reports_a_device_error() -> None:
    """On a headless host opening must fail cleanly, never with a raw PortAudio error."""
    pytest.importorskip("sounddevice", reason="sounddevice is an optional [audio] extra")
    backend = SoundDeviceOutput()
    try:
        backend.open(SAMPLE_RATE, CHANNELS, ramp)
    except OutputDeviceError:
        pass
    else:
        assert backend.is_open
        assert backend.xruns == 0
    finally:
        backend.close()


# --------------------------------------------------------------------------- #
# create_output() backend selection
# --------------------------------------------------------------------------- #


class StubBackend(AudioOutput):
    """Backend whose availability and open-ability the selection tests control."""

    available = True
    opens = True
    instances: list[StubBackend]

    def __init__(self) -> None:
        super().__init__()
        type(self).instances.append(self)

    @classmethod
    def is_available(cls) -> bool:
        return cls.available

    def _open_stream(self) -> None:
        if not type(self).opens:
            raise OutputDeviceError(f"{type(self).name} refuses to open")

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False


@pytest.fixture()
def stubs(monkeypatch: pytest.MonkeyPatch) -> tuple[type[StubBackend], type[StubBackend]]:
    """Replace both hardware backends with controllable stand-ins."""

    class StubSoundDevice(StubBackend):
        name = "stub-sounddevice"
        available = True
        opens = True
        instances: list[StubBackend] = []

    class StubPyAudio(StubBackend):
        name = "stub-pyaudio"
        available = True
        opens = True
        instances: list[StubBackend] = []

    monkeypatch.delenv(OUTPUT_BACKEND_ENV_VAR, raising=False)
    monkeypatch.setattr(sounddevice_module, "SoundDeviceOutput", StubSoundDevice)
    monkeypatch.setattr(output_module, "PyAudioOutput", StubPyAudio)
    return StubSoundDevice, StubPyAudio


def test_sounddevice_is_preferred_when_it_opens(
    stubs: tuple[type[StubBackend], type[StubBackend]],
) -> None:
    stub_sd, stub_pa = stubs
    backend = create_output()
    assert isinstance(backend, stub_sd)
    assert stub_pa.instances == []


def test_returned_backend_is_a_fresh_instance(
    stubs: tuple[type[StubBackend], type[StubBackend]],
) -> None:
    stub_sd, _ = stubs
    backend = create_output()
    assert len(stub_sd.instances) == 2  # the throwaway probe, then the real one
    assert backend is stub_sd.instances[-1]
    assert not backend.is_open


def test_falls_back_to_pyaudio_when_sounddevice_is_absent(
    stubs: tuple[type[StubBackend], type[StubBackend]],
) -> None:
    stub_sd, stub_pa = stubs
    stub_sd.available = False
    assert isinstance(create_output(), stub_pa)


def test_falls_back_to_pyaudio_when_sounddevice_cannot_open(
    stubs: tuple[type[StubBackend], type[StubBackend]],
) -> None:
    stub_sd, stub_pa = stubs
    stub_sd.opens = False
    assert isinstance(create_output(), stub_pa)


def test_falls_back_to_null_when_no_device_opens(
    stubs: tuple[type[StubBackend], type[StubBackend]],
) -> None:
    stub_sd, stub_pa = stubs
    stub_sd.opens = False
    stub_pa.opens = False
    assert isinstance(create_output(), NullOutput)


def test_env_var_forces_pyaudio(
    stubs: tuple[type[StubBackend], type[StubBackend]], monkeypatch: pytest.MonkeyPatch
) -> None:
    stub_sd, stub_pa = stubs
    monkeypatch.setenv(OUTPUT_BACKEND_ENV_VAR, "pyaudio")
    backend = create_output()
    assert isinstance(backend, stub_pa)
    assert stub_sd.instances == []


def test_env_var_forcing_pyaudio_still_falls_back_to_null(
    stubs: tuple[type[StubBackend], type[StubBackend]], monkeypatch: pytest.MonkeyPatch
) -> None:
    _, stub_pa = stubs
    stub_pa.opens = False
    monkeypatch.setenv(OUTPUT_BACKEND_ENV_VAR, "pyaudio")
    assert isinstance(create_output(), NullOutput)


def test_env_var_forces_sounddevice(
    stubs: tuple[type[StubBackend], type[StubBackend]], monkeypatch: pytest.MonkeyPatch
) -> None:
    stub_sd, stub_pa = stubs
    stub_sd.opens = False
    monkeypatch.setenv(OUTPUT_BACKEND_ENV_VAR, "SoundDevice")
    assert isinstance(create_output(), NullOutput)
    assert stub_pa.instances == []


def test_env_var_null_skips_every_device(
    stubs: tuple[type[StubBackend], type[StubBackend]], monkeypatch: pytest.MonkeyPatch
) -> None:
    stub_sd, stub_pa = stubs
    monkeypatch.setenv(OUTPUT_BACKEND_ENV_VAR, "null")
    assert isinstance(create_output(), NullOutput)
    assert stub_sd.instances == []
    assert stub_pa.instances == []


def test_unknown_env_value_keeps_the_default_order(
    stubs: tuple[type[StubBackend], type[StubBackend]], monkeypatch: pytest.MonkeyPatch
) -> None:
    stub_sd, _ = stubs
    monkeypatch.setenv(OUTPUT_BACKEND_ENV_VAR, "jack")
    assert isinstance(create_output(), stub_sd)


def test_prefer_null_probes_nothing(
    stubs: tuple[type[StubBackend], type[StubBackend]],
) -> None:
    stub_sd, stub_pa = stubs
    assert isinstance(create_output(prefer_null=True), NullOutput)
    assert stub_sd.instances == []
    assert stub_pa.instances == []
