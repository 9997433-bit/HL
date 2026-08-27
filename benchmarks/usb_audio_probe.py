#!/usr/bin/env python3
"""Physical audio device probe: is there a converter on this host at all?

The C4 round-trip evidence in ``benchmarks/roundtrip_latency_probe.py`` is
measured through a PulseAudio null sink and its monitor source, because this
host has no sound card. That report says so in ``physical_dac_adc: false``, but
"no sound card" is an assertion a reader has to take on trust unless something
goes and looks. This probe goes and looks.

What it looks at
----------------
Four independent layers, each recorded whether or not it finds anything:

* **the kernel** — ``/dev/snd``, ``/proc/asound/cards`` and ``/sys/class/sound``.
  This is the only layer that can prove a converter exists: a PCM node and a
  card entry mean a driver bound to a device. Nothing above the kernel can
  manufacture one, so if the kernel exposes no card, no device the layers above
  advertise is physical, however convincing its name.
* **the USB bus** — every USB interface in sysfs whose ``bInterfaceClass`` is
  ``01`` (audio), with the vendor, product and manufacturer strings of the
  device it belongs to. A class-compliant USB interface is what "hardware
  certification" means in practice for this product, so it is enumerated
  separately from the card list rather than inferred from it.
* **PortAudio** — every device ``sounddevice`` advertises, with its host API,
  channel counts, default rate and default latencies, plus whether the format
  the product actually uses (48 kHz ``float32``) is accepted. Each device is
  classified against the kernel evidence: an ALSA name that addresses a card
  is physical, and ``pulse``, ``default``, ``dmix`` and friends are not.
* **the sound server** — PulseAudio's sinks and sources with their drivers, so
  a host running entirely on ``module-null-sink`` is visible as exactly that.

What it concludes
-----------------
``physical_hardware_present`` is true only when the kernel exposes a card *and*
PortAudio advertises a device that addresses it. On a host where that is false —
this one — the probe does not fail and does not pretend: it writes the report
with ``status: "not-certified"``, names the stages of the signal path that no
measurement on this host can include, and compares itself against the published
C4 baseline so the two artifacts agree about what was and was not in the loop.

``--require-physical`` turns the absence into exit code 1, which is what a
hardware runner should use as its gate. Without the flag the run succeeds and
publishes an honest negative result, which is the useful thing to do in a CI
job that cannot have a sound card.

Examples::

    python3 benchmarks/usb_audio_probe.py
    python3 benchmarks/usb_audio_probe.py --require-physical
    python3 benchmarks/usb_audio_probe.py --output /tmp/devices.json --quiet
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

#: The checklist item this probe supports. It does not grade C4 — the
#: round-trip probe does — it establishes what kind of evidence C4 can be.
CHECKLIST_ITEM: str = "C4"

#: The format the product's own device path uses, and therefore the one worth
#: asking each device about.
DEFAULT_SAMPLE_RATE: int = 48_000
DEFAULT_CHANNELS: int = 2
DEFAULT_BUFFER_FRAMES: int = 128

DEFAULT_BASELINE_PATH = (
    REPOSITORY_ROOT / ".agent_workspace/round3/roundtrip-latency-report.json"
)
DEFAULT_REPORT_PATH = REPOSITORY_ROOT / ".agent_workspace/v1.0/usb-audio-probe-report.json"

#: ``bInterfaceClass`` for USB Audio, per the USB device class definition.
USB_AUDIO_INTERFACE_CLASS: str = "01"

#: ALSA PCM names that are plugins over something else rather than a card of
#: their own. ``default`` and ``sysdefault`` without a ``CARD=`` qualifier
#: resolve to whatever the host has configured, which on a server-only host is
#: the server.
ALSA_PLUGIN_NAMES: frozenset[str] = frozenset(
    {
        "default",
        "sysdefault",
        "dmix",
        "dsnoop",
        "null",
        "lavrate",
        "samplerate",
        "speexrate",
        "upmix",
        "vdownmix",
        "oss",
    }
)

#: Sound servers and virtual cables. Anything whose name carries one of these
#: is software pretending to be a device, on every platform this runs on.
VIRTUAL_NAME_MARKERS: tuple[str, ...] = (
    "pulse",
    "pipewire",
    "jack",
    "loopback",
    "monitor",
    "dummy",
    "blackhole",
    "soundflower",
    "vb-audio",
    "vb audio",
    "virtual",
    "aggregate",
    "null",
)

#: ALSA PCM name forms that address a card directly. ``CARD=`` covers the long
#: form PortAudio usually reports (``front:CARD=USB,DEV=0``).
HARDWARE_NAME_PREFIXES: tuple[str, ...] = ("hw:", "plughw:")
HARDWARE_NAME_MARKERS: tuple[str, ...] = ("card=", "(hw:")

#: What a DAC and an ADC would add to the round trip, as stated in the C4
#: report's own limitation text. Quoted here so the two artifacts cannot drift
#: apart, and labelled everywhere it appears as an estimate rather than a
#: measurement: nothing on this host measured it.
CONVERTER_ESTIMATE_MS: tuple[float, float] = (1.0, 3.0)

#: The stages a sample passes through, and whether each one is in the loop the
#: C4 report measured (a null sink and its monitor) or in the loop a physical
#: interface would close. ``optional`` means it depends on how the hardware run
#: is configured — reaching a card through PulseAudio keeps the server stages,
#: opening it directly does not.
SIGNAL_PATH_STAGES: tuple[dict[str, str], ...] = (
    {
        "stage": "application render path (AudioEngine ring buffer, feeder, gain)",
        "measured_here": "present",
        "on_physical_hardware": "present",
        "note": "the engine-render scenario puts the product's own transport in the loop",
    },
    {
        "stage": "PortAudio duplex callback",
        "measured_here": "present",
        "on_physical_hardware": "present",
        "note": "same API, same 128-frame block, same float32 format",
    },
    {
        "stage": "ALSA PCM device",
        "measured_here": "present",
        "on_physical_hardware": "present",
        "note": "the plugin PCM here; the card's own PCM there",
    },
    {
        "stage": "ALSA-to-PulseAudio plugin",
        "measured_here": "present",
        "on_physical_hardware": "optional",
        "note": "present when the card is reached through the server, absent when opened directly",
    },
    {
        "stage": "PulseAudio scheduler and mixer",
        "measured_here": "present",
        "on_physical_hardware": "optional",
        "note": "as above",
    },
    {
        "stage": "null-sink timer scheduling",
        "measured_here": "present",
        "on_physical_hardware": "absent",
        "note": "a sink with no device behind it advances on a timer, not on interrupts",
    },
    {
        "stage": "device interrupt cadence and DMA transfer",
        "measured_here": "absent",
        "on_physical_hardware": "present",
        "note": "what the null sink's timer stands in for",
    },
    {
        "stage": "USB isochronous transfer",
        "measured_here": "absent",
        "on_physical_hardware": "present",
        "note": "for a USB interface; a PCI card substitutes its own bus transfer",
    },
    {
        "stage": "digital-to-analogue converter and reconstruction filter",
        "measured_here": "absent",
        "on_physical_hardware": "present",
        "note": "no converter exists on this host to measure",
    },
    {
        "stage": "analogue output stage, cable and analogue input stage",
        "measured_here": "absent",
        "on_physical_hardware": "present",
        "note": "the loop is closed inside the server instead of by a cable",
    },
    {
        "stage": "analogue-to-digital converter and anti-alias filter",
        "measured_here": "absent",
        "on_physical_hardware": "present",
        "note": "no converter exists on this host to measure",
    },
)


class ProbeError(RuntimeError):
    """The probe could not produce a report."""


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Enumerate physical audio hardware and state what C4 evidence it allows.",
    )
    parser.add_argument("--sample-rate", type=int, default=DEFAULT_SAMPLE_RATE)
    parser.add_argument("--channels", type=int, default=DEFAULT_CHANNELS)
    parser.add_argument(
        "--require-physical",
        action="store_true",
        help="exit 1 when no physical audio device is present, instead of "
        "publishing an honest negative report",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=DEFAULT_BASELINE_PATH,
        help="the C4 round-trip report to compare this host against",
    )
    parser.add_argument(
        "--sysroot",
        type=Path,
        default=Path("/"),
        help="filesystem root to read kernel audio evidence from (default /); "
        "the tests point it at synthetic trees so the scanners are exercised "
        "on hosts that do and do not have sound cards",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--quiet", action="store_true", help="suppress progress on stderr")
    return parser.parse_args(argv)


def _progress(quiet: bool, message: str) -> None:
    if not quiet:
        print(f"[usb-audio-probe] {message}", file=sys.stderr, flush=True)


def _repository_relative(path: Path) -> str:
    """Paths inside the repository are published relative to it, not absolutely.

    An artifact that records where somebody's checkout happened to live is
    harder to compare between runs than one that records the file.
    """
    resolved = Path(path).resolve()
    try:
        return str(resolved.relative_to(REPOSITORY_ROOT))
    except ValueError:
        return str(resolved)


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return None


# ------------------------------------------------------------------ the kernel


@dataclass(frozen=True)
class SoundCard:
    """One card the kernel has bound a driver to."""

    index: int
    card_id: str
    driver: str
    description: str
    #: ``usb``, ``pci``, another bus name, or ``unknown`` when sysfs did not say.
    bus: str = "unknown"
    sysfs_path: str | None = None

    @property
    def usb(self) -> bool:
        return self.bus == "usb"


@dataclass
class KernelEvidence:
    """What the kernel says about sound devices on this host."""

    #: False on platforms where these paths mean nothing (macOS, Windows).
    applicable: bool
    platform: str
    dev_snd_present: bool
    dev_snd_nodes: list[str]
    pcm_nodes: list[str]
    proc_asound_present: bool
    sys_class_sound_present: bool
    cards: list[SoundCard]
    detail: str

    @property
    def card_ids(self) -> set[str]:
        identifiers: set[str] = set()
        for card in self.cards:
            identifiers.add(card.card_id.lower())
            if card.description:
                identifiers.add(card.description.lower())
        return identifiers

    def as_dict(self) -> dict[str, Any]:
        return {
            "applicable": self.applicable,
            "platform": self.platform,
            "dev_snd_present": self.dev_snd_present,
            "dev_snd_nodes": self.dev_snd_nodes,
            "pcm_nodes": self.pcm_nodes,
            "proc_asound_present": self.proc_asound_present,
            "sys_class_sound_present": self.sys_class_sound_present,
            "cards": [{**asdict(card), "usb": card.usb} for card in self.cards],
            "card_count": len(self.cards),
            "detail": self.detail,
        }


#: ``  0 [PCH  ]: HDA-Intel - HDA Intel PCH`` — index, id, driver, description.
_CARD_LINE = re.compile(r"^\s*(\d+)\s+\[(?P<id>[^\]]+)\]\s*:\s*(?P<driver>\S+)\s*-\s*(?P<desc>.*)$")


def parse_asound_cards(text: str) -> list[SoundCard]:
    """Read ``/proc/asound/cards`` into card records.

    The file alternates a header line per card with a continuation line of
    driver detail, which is ignored here: the header carries everything a
    reader needs to tell one card from another.
    """
    cards: list[SoundCard] = []
    for line in text.splitlines():
        match = _CARD_LINE.match(line)
        if match is None:
            continue
        cards.append(
            SoundCard(
                index=int(match.group(1)),
                card_id=match.group("id").strip(),
                driver=match.group("driver").strip(),
                description=match.group("desc").strip(),
            )
        )
    return cards


def _card_bus(sysroot: Path, card_index: int) -> tuple[str, str | None]:
    """Which bus a card sits on, read from its sysfs ``device`` symlink.

    A USB interface resolves to a path under ``/sys/devices/.../usb``; a
    built-in codec resolves to a PCI path. The bus is taken from the resolved
    path rather than guessed from the driver name.
    """
    link = sysroot / "sys/class/sound" / f"card{card_index}" / "device"
    if not link.exists():
        return "unknown", None
    resolved = os.path.realpath(link)
    # Components are read from the device outwards, because a USB card hangs
    # off the PCI controller its bus belongs to and the bus nearest the device
    # is the one that describes it.
    for part in reversed(Path(resolved).parts):
        lowered = part.lower()
        for bus in ("usb", "pci", "platform", "firewire", "thunderbolt"):
            if lowered.startswith(bus):
                return bus, resolved
    return "unknown", resolved


def scan_kernel(sysroot: Path = Path("/")) -> KernelEvidence:
    """Ask the kernel, and only the kernel, whether a sound card exists."""
    system = platform.system()
    sysroot = Path(sysroot)
    applicable = system == "Linux" or (sysroot / "proc/asound").exists()

    dev_snd = sysroot / "dev/snd"
    nodes: list[str] = []
    if dev_snd.is_dir():
        try:
            nodes = sorted(entry.name for entry in dev_snd.iterdir())
        except OSError:
            nodes = []
    pcm_nodes = [name for name in nodes if name.startswith("pcm")]

    cards_file = sysroot / "proc/asound/cards"
    cards_text = _read_text(cards_file) if cards_file.exists() else None
    cards = parse_asound_cards(cards_text) if cards_text else []

    sys_class_sound = sysroot / "sys/class/sound"
    resolved_cards: list[SoundCard] = []
    for card in cards:
        bus, path = _card_bus(sysroot, card.index)
        resolved_cards.append(
            SoundCard(card.index, card.card_id, card.driver, card.description, bus, path)
        )

    if not applicable:
        detail = (
            f"{system} does not expose ALSA device nodes; physical devices are "
            "identified from the host API instead"
        )
    elif resolved_cards:
        named = ", ".join(f"{card.card_id} ({card.driver}, {card.bus})" for card in resolved_cards)
        detail = f"the kernel has bound {len(resolved_cards)} card(s): {named}"
    elif dev_snd.is_dir():
        detail = (
            "/dev/snd exists but no card appears in /proc/asound/cards: the "
            "container can see the device directory without a driver behind it"
        )
    else:
        detail = (
            "no /dev/snd, no /proc/asound/cards: this host has no sound card, "
            "so nothing above the kernel can be a physical audio device"
        )

    return KernelEvidence(
        applicable=applicable,
        platform=system,
        dev_snd_present=dev_snd.is_dir(),
        dev_snd_nodes=nodes,
        pcm_nodes=pcm_nodes,
        proc_asound_present=cards_file.exists(),
        sys_class_sound_present=sys_class_sound.is_dir(),
        cards=resolved_cards,
        detail=detail,
    )


# --------------------------------------------------------------- the USB bus


@dataclass(frozen=True)
class UsbAudioInterface:
    """A USB interface whose class is Audio, and the device it belongs to."""

    sysfs_path: str
    interface: str
    interface_class: str
    interface_subclass: str | None
    vendor_id: str | None
    product_id: str | None
    product: str | None
    manufacturer: str | None
    speed: str | None


@dataclass
class UsbEvidence:
    sysfs_available: bool
    interfaces: list[UsbAudioInterface]
    lsusb_available: bool
    lsusb_audio_lines: list[str]
    detail: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "sysfs_available": self.sysfs_available,
            "audio_class_interfaces": [asdict(item) for item in self.interfaces],
            "audio_class_interface_count": len(self.interfaces),
            "lsusb_available": self.lsusb_available,
            "lsusb_audio_lines": self.lsusb_audio_lines,
            "detail": self.detail,
        }


def scan_usb_audio(sysroot: Path = Path("/")) -> UsbEvidence:
    """Enumerate USB Audio class interfaces from sysfs.

    Reading the interface class directly is what distinguishes an audio
    interface from any other USB device: a class-compliant DAC advertises
    ``bInterfaceClass=01`` whatever it calls itself.
    """
    devices_dir = Path(sysroot) / "sys/bus/usb/devices"
    interfaces: list[UsbAudioInterface] = []
    if devices_dir.is_dir():
        for entry in sorted(devices_dir.iterdir()):
            interface_class = _read_text(entry / "bInterfaceClass")
            if interface_class is None or interface_class.strip() != USB_AUDIO_INTERFACE_CLASS:
                continue
            parent = entry.parent / entry.name.split(":")[0]
            interfaces.append(
                UsbAudioInterface(
                    sysfs_path=str(entry),
                    interface=entry.name,
                    interface_class=interface_class.strip(),
                    interface_subclass=_read_text(entry / "bInterfaceSubClass"),
                    vendor_id=_read_text(parent / "idVendor"),
                    product_id=_read_text(parent / "idProduct"),
                    product=_read_text(parent / "product"),
                    manufacturer=_read_text(parent / "manufacturer"),
                    speed=_read_text(parent / "speed"),
                )
            )

    lsusb_lines: list[str] = []
    lsusb_available = shutil.which("lsusb") is not None
    if lsusb_available and Path(sysroot) == Path("/"):
        try:
            completed = subprocess.run(
                ["lsusb"], capture_output=True, text=True, check=False, timeout=10
            )
            lsusb_lines = [
                line for line in completed.stdout.splitlines() if "audio" in line.lower()
            ]
        except (OSError, subprocess.SubprocessError):
            lsusb_available = False

    if interfaces:
        named = ", ".join(
            f"{item.manufacturer or '?'} {item.product or '?'}".strip() for item in interfaces
        )
        detail = f"{len(interfaces)} USB audio class interface(s): {named}"
    elif devices_dir.is_dir():
        detail = "the USB bus is visible in sysfs and carries no audio class interface"
    else:
        detail = (
            "/sys/bus/usb/devices is not present: this container has no view of "
            "a USB bus, so a USB interface could not be seen even if one existed"
        )
    return UsbEvidence(devices_dir.is_dir(), interfaces, lsusb_available, lsusb_lines, detail)


# ------------------------------------------------------------------ PortAudio


@dataclass
class AudioDevice:
    """One PortAudio device, and what this probe concluded about it."""

    index: int
    name: str
    hostapi_index: int
    hostapi: str
    max_input_channels: int
    max_output_channels: int
    default_samplerate: float
    default_low_input_latency_ms: float
    default_low_output_latency_ms: float
    default_high_input_latency_ms: float
    default_high_output_latency_ms: float
    classification: str
    physical: bool
    reason: str
    format_check: dict[str, Any] = field(default_factory=dict)


@dataclass
class PortAudioEvidence:
    available: bool
    sounddevice_version: str
    portaudio_version: str
    host_apis: list[dict[str, Any]]
    devices: list[AudioDevice]
    default_input_device: int | None
    default_output_device: int | None
    detail: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "sounddevice": self.sounddevice_version,
            "portaudio": self.portaudio_version,
            "host_apis": self.host_apis,
            "devices": [asdict(device) for device in self.devices],
            "device_count": len(self.devices),
            "physical_device_count": sum(1 for device in self.devices if device.physical),
            "default_input_device": self.default_input_device,
            "default_output_device": self.default_output_device,
            "detail": self.detail,
        }


def classify_device(name: str, hostapi: str, kernel: KernelEvidence) -> tuple[str, bool, str]:
    """Decide what a PortAudio device actually is.

    The kernel has the last word. On a Linux host with no card, every device
    PortAudio advertises is a plugin over a sound server or over nothing at
    all, and no name can override that. Where the kernel evidence does not
    apply — macOS, Windows — the name is all there is, so the classification
    says so in its reason rather than implying it inspected a bus.
    """
    lowered = name.strip().lower()
    base = lowered.split(":", 1)[0].split(",", 1)[0].strip()

    if any(marker in lowered for marker in VIRTUAL_NAME_MARKERS):
        return "virtual", False, f"{name!r} names a sound server or a virtual device"
    if base in ALSA_PLUGIN_NAMES:
        return "alsa-plugin", False, f"{name!r} is an ALSA plugin, not a card"

    addresses_card = lowered.startswith(HARDWARE_NAME_PREFIXES) or any(
        marker in lowered for marker in HARDWARE_NAME_MARKERS
    )
    matches_card = any(
        card_id and card_id in lowered for card_id in kernel.card_ids if len(card_id) > 2
    )

    if kernel.applicable:
        if not kernel.cards:
            return (
                "unbacked",
                False,
                (
                    f"{name!r} is advertised by the {hostapi} host API, but the "
                    "kernel exposes no sound card for it to address"
                ),
            )
        if addresses_card or matches_card:
            return "physical", True, f"{name!r} addresses a card the kernel has bound"
        return (
            "indeterminate",
            False,
            f"{name!r} does not name any card the kernel reported; not counted as physical",
        )

    return (
        "hostapi-reported",
        True,
        (
            f"{name!r} is reported by the {hostapi} host API on a platform without "
            "ALSA device nodes; classified from the host API and the name alone"
        ),
    )


def _check_format(
    module: Any, index: int, device: dict[str, Any], rate: int, channels: int
) -> dict[str, Any]:
    """Does the device accept the format the product uses, at this rate?

    ``check_*_settings`` asks PortAudio to validate the parameters without
    opening a stream, so this is safe to run against every device including
    ones the probe has no business starting.
    """
    result: dict[str, Any] = {"sample_rate": rate, "dtype": "float32"}
    for direction, key, checker in (
        ("input", "max_input_channels", "check_input_settings"),
        ("output", "max_output_channels", "check_output_settings"),
    ):
        available = int(device.get(key, 0))
        if available <= 0:
            result[direction] = {"supported": False, "reason": "the device has no channels here"}
            continue
        try:
            getattr(module, checker)(
                device=index,
                channels=min(channels, available),
                dtype="float32",
                samplerate=rate,
            )
        except Exception as error:  # noqa: BLE001 - PortAudio raises its own type
            result[direction] = {"supported": False, "reason": str(error).strip()}
        else:
            result[direction] = {"supported": True, "channels": min(channels, available)}
    return result


def enumerate_portaudio(
    kernel: KernelEvidence, sample_rate: int, channels: int
) -> PortAudioEvidence:
    """Enumerate every device PortAudio advertises, and classify each one."""
    try:
        import sounddevice as sd
    except Exception as error:  # noqa: BLE001 - an absent backend is a finding
        return PortAudioEvidence(
            available=False,
            sounddevice_version="unavailable",
            portaudio_version="unavailable",
            host_apis=[],
            devices=[],
            default_input_device=None,
            default_output_device=None,
            detail=f"sounddevice could not be imported: {error}",
        )

    host_apis: list[dict[str, Any]] = []
    for index, api in enumerate(sd.query_hostapis()):
        host_apis.append(
            {
                "index": index,
                "name": api["name"],
                "device_count": len(api.get("devices", ())),
                "default_input_device": api.get("default_input_device"),
                "default_output_device": api.get("default_output_device"),
            }
        )

    devices: list[AudioDevice] = []
    for index, raw in enumerate(sd.query_devices()):
        api_index = int(raw["hostapi"])
        api_name = host_apis[api_index]["name"] if api_index < len(host_apis) else "unknown"
        classification, physical, reason = classify_device(raw["name"], api_name, kernel)
        devices.append(
            AudioDevice(
                index=index,
                name=raw["name"],
                hostapi_index=api_index,
                hostapi=api_name,
                max_input_channels=int(raw["max_input_channels"]),
                max_output_channels=int(raw["max_output_channels"]),
                default_samplerate=float(raw["default_samplerate"]),
                default_low_input_latency_ms=round(raw["default_low_input_latency"] * 1e3, 4),
                default_low_output_latency_ms=round(raw["default_low_output_latency"] * 1e3, 4),
                default_high_input_latency_ms=round(raw["default_high_input_latency"] * 1e3, 4),
                default_high_output_latency_ms=round(raw["default_high_output_latency"] * 1e3, 4),
                classification=classification,
                physical=physical,
                reason=reason,
                format_check=_check_format(sd, index, raw, sample_rate, channels),
            )
        )

    default_input, default_output = (None, None)
    try:
        default_input, default_output = (int(value) for value in sd.default.device)
    except (TypeError, ValueError):
        pass

    physical_count = sum(1 for device in devices if device.physical)
    detail = (
        f"{len(devices)} device(s) across {len(host_apis)} host API(s); "
        f"{physical_count} classified as physical"
    )
    return PortAudioEvidence(
        available=True,
        sounddevice_version=str(getattr(sd, "__version__", "unknown")),
        portaudio_version=str(sd.get_portaudio_version()[1]),
        host_apis=host_apis,
        devices=devices,
        default_input_device=default_input,
        default_output_device=default_output,
        detail=detail,
    )


# ------------------------------------------------------------- the sound server


def _pactl(*arguments: str) -> str | None:
    if shutil.which("pactl") is None:
        return None
    try:
        completed = subprocess.run(
            ["pactl", *arguments], capture_output=True, text=True, check=False, timeout=15
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return completed.stdout if completed.returncode == 0 else None


def _pactl_short(kind: str) -> list[dict[str, str]]:
    output = _pactl("list", "short", kind)
    entries: list[dict[str, str]] = []
    for line in (output or "").splitlines():
        parts = line.split("\t")
        if len(parts) < 4:
            continue
        driver = parts[2]
        entries.append(
            {
                "index": parts[0],
                "name": parts[1],
                "driver": driver,
                "sample_spec": parts[3],
                "kind": "null-sink"
                if "null-sink" in driver
                else ("hardware" if "alsa" in driver else "other"),
            }
        )
    return entries


def scan_sound_server() -> dict[str, Any]:
    """PulseAudio's own view: which of its endpoints have a device behind them."""
    info = _pactl("info")
    if info is None:
        return {
            "pulseaudio_available": False,
            "detail": "pactl is absent or no PulseAudio server answered",
        }
    server_version = "unknown"
    default_sink = default_source = "unknown"
    for line in info.splitlines():
        if line.startswith("Server Version:"):
            server_version = line.split(":", 1)[1].strip()
        elif line.startswith("Default Sink:"):
            default_sink = line.split(":", 1)[1].strip()
        elif line.startswith("Default Source:"):
            default_source = line.split(":", 1)[1].strip()

    sinks = _pactl_short("sinks")
    sources = _pactl_short("sources")
    hardware_sinks = [sink for sink in sinks if sink["kind"] == "hardware"]
    null_sinks = [sink for sink in sinks if sink["kind"] == "null-sink"]
    return {
        "pulseaudio_available": True,
        "server_version": server_version,
        "default_sink": default_sink,
        "default_source": default_source,
        "sinks": sinks,
        "sources": sources,
        "hardware_sink_count": len(hardware_sinks),
        "null_sink_count": len(null_sinks),
        "null_sink_only": bool(sinks) and not hardware_sinks,
        "detail": (
            f"{len(sinks)} sink(s), of which {len(null_sinks)} are null sinks and "
            f"{len(hardware_sinks)} are backed by an ALSA card"
        ),
    }


# --------------------------------------------------------- the hardware verdict


@dataclass
class HardwareEvidence:
    """The one question this probe exists to answer, with its reasons.

    :func:`detect_hardware` builds it, and ``roundtrip_latency_probe`` reads it
    for ``--require-physical`` so the two probes cannot disagree about whether
    a converter is present.
    """

    present: bool
    reason: str
    kernel: KernelEvidence
    usb: UsbEvidence
    portaudio: PortAudioEvidence

    @property
    def physical_devices(self) -> list[AudioDevice]:
        return [device for device in self.portaudio.devices if device.physical]

    @property
    def playback_devices(self) -> list[AudioDevice]:
        return [device for device in self.physical_devices if device.max_output_channels > 0]

    @property
    def capture_devices(self) -> list[AudioDevice]:
        return [device for device in self.physical_devices if device.max_input_channels > 0]


def detect_hardware(
    sysroot: Path = Path("/"),
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    channels: int = DEFAULT_CHANNELS,
) -> HardwareEvidence:
    """Is there a physical audio device on this host, and how do we know?

    The bar is deliberately high in one direction only: a card the kernel has
    bound *and* a PortAudio device that addresses it. Half of that is not a
    device anyone can measure a round trip through — a card with no usable PCM
    cannot carry a stream, and a PortAudio name with no card behind it is a
    plugin over the sound server.
    """
    kernel = scan_kernel(sysroot)
    usb = scan_usb_audio(sysroot)
    portaudio = enumerate_portaudio(kernel, sample_rate, channels)
    physical = [device for device in portaudio.devices if device.physical]

    if not portaudio.available:
        reason = (
            "PortAudio is unavailable, so no device could be opened even if the "
            f"kernel had one: {portaudio.detail}"
        )
        return HardwareEvidence(False, reason, kernel, usb, portaudio)
    if kernel.applicable and not kernel.cards:
        reason = kernel.detail
        return HardwareEvidence(False, reason, kernel, usb, portaudio)
    if not physical:
        reason = (
            "the kernel reports "
            f"{len(kernel.cards)} card(s) but PortAudio advertises no device that "
            "addresses one"
        )
        return HardwareEvidence(False, reason, kernel, usb, portaudio)

    names = ", ".join(f"{device.name!r} ({device.hostapi})" for device in physical)
    usb_note = (
        f", {len(usb.interfaces)} of them on the USB bus" if usb.interfaces else ""
    )
    return HardwareEvidence(
        True,
        f"{len(physical)} physical device(s) backed by a kernel sound card{usb_note}: {names}",
        kernel,
        usb,
        portaudio,
    )


# ----------------------------------------------------------- the C4 comparison


def load_baseline(path: Path) -> dict[str, Any]:
    """Read the published C4 round-trip report, if it exists."""
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def compare_with_baseline(
    baseline: dict[str, Any], hardware: HardwareEvidence, server: dict[str, Any], path: Path
) -> dict[str, Any]:
    """Set this host's device inventory against the C4 evidence that was published.

    The point of the comparison is not to re-grade C4 — the round-trip probe
    did that and its number stands — but to make the two artifacts say the same
    thing about the same host. The baseline claims no converter was in its
    loop; this probe went looking for one and found none, so the claim is
    corroborated rather than merely repeated. What the comparison then adds is
    the arithmetic a reader would otherwise have to do by hand: the stages that
    are missing, and whether the estimated cost of the missing ones would still
    fit under the budget the measurement cleared.
    """
    relative = _repository_relative(path)
    if not baseline:
        return {
            "report": relative,
            "available": False,
            "detail": (
                "no C4 round-trip report was found, so this inventory stands on "
                "its own; run benchmarks/roundtrip_latency_probe.py to publish one"
            ),
        }

    measured = float(baseline.get("roundtrip_latency_ms", 0.0))
    threshold = float(baseline.get("threshold_ms", 0.0))
    margin = round(threshold - measured, 4)
    baseline_claims_converter = bool(baseline.get("physical_dac_adc", False))
    low, high = CONVERTER_ESTIMATE_MS
    worst_case = round(measured + high, 4)

    missing = [
        stage["stage"]
        for stage in SIGNAL_PATH_STAGES
        if stage["measured_here"] == "absent" and stage["on_physical_hardware"] == "present"
    ]

    if hardware.present:
        conclusion = (
            "this host has physical audio hardware, so the C4 measurement can be "
            "repeated on a real converter; until it is, the published number "
            "remains server-loopback evidence"
        )
    else:
        conclusion = (
            "the baseline was measured through a sound-server loopback and this "
            "host has no converter to measure through, so C4 cannot be upgraded "
            "to hardware evidence here. The measurement stands for every software "
            "stage it contains; the converter path is unmeasured and is stated as "
            "such in both artifacts"
        )

    return {
        "report": relative,
        "available": True,
        "checklist_item": baseline.get("checklist_item"),
        "status": baseline.get("status"),
        "evidence": baseline.get("evidence"),
        "loopback_path": baseline.get("loopback_path"),
        "buffer_frames": baseline.get("buffer_frames"),
        "sample_rate": baseline.get("sample_rate"),
        "roundtrip_latency_ms": measured,
        "threshold_ms": threshold,
        "margin_ms": margin,
        "baseline_claims_physical_dac_adc": baseline_claims_converter,
        # The two artifacts have to agree about the same host, or one of them is
        # describing a machine it did not run on.
        "agrees_with_this_probe": baseline_claims_converter == hardware.present,
        "pulseaudio_null_sink_only": bool(server.get("null_sink_only", False)),
        "signal_path": list(SIGNAL_PATH_STAGES),
        "stages_absent_from_this_host": missing,
        "converter_overhead": {
            "measured": False,
            "estimate_ms": [low, high],
            "source": (
                "the estimate stated in benchmarks/roundtrip_latency_probe.py for "
                "typical converters; no converter on this host was measured"
            ),
            "worst_case_roundtrip_with_estimate_ms": worst_case,
            "still_within_threshold": worst_case < threshold if threshold else False,
            "headroom_after_estimate_ms": round(threshold - worst_case, 4) if threshold else None,
        },
        "conclusion": conclusion,
    }


# ------------------------------------------------------------------- the report


def build_report(
    args: argparse.Namespace,
    hardware: HardwareEvidence,
    server: dict[str, Any],
    baseline_comparison: dict[str, Any],
) -> dict[str, Any]:
    """Assemble the published inventory. Nothing here decides anything new."""
    kernel, usb, portaudio = hardware.kernel, hardware.usb, hardware.portaudio
    certified = hardware.present

    observations = [
        {
            "id": "kernel-sound-card",
            "title": "the kernel has bound a driver to a sound card",
            "found": bool(kernel.cards),
            "detail": kernel.detail,
        },
        {
            "id": "alsa-pcm-nodes",
            "title": "/dev/snd exposes PCM device nodes",
            "found": bool(kernel.pcm_nodes),
            "detail": (
                f"{len(kernel.pcm_nodes)} PCM node(s) of {len(kernel.dev_snd_nodes)} entries"
                if kernel.dev_snd_present
                else "/dev/snd does not exist on this host"
            ),
        },
        {
            "id": "usb-audio-class-interface",
            "title": "a USB Audio class interface is attached",
            "found": bool(usb.interfaces),
            "detail": usb.detail,
        },
        {
            "id": "portaudio-physical-device",
            "title": "PortAudio advertises a device backed by a card",
            "found": bool(hardware.physical_devices),
            "detail": portaudio.detail,
        },
        {
            "id": "sound-server-hardware-sink",
            "title": "the sound server has a sink backed by an ALSA card",
            "found": bool(server.get("hardware_sink_count", 0)),
            "detail": str(server.get("detail", "no sound server answered")),
        },
    ]

    return {
        "schema_version": 1,
        "harness": "benchmarks/usb_audio_probe.py",
        "checklist_item": CHECKLIST_ITEM,
        "evidence": "device-enumeration",
        # Deliberately not "pass"/"fail": this probe grades nothing. It reports
        # whether the host can carry hardware certification at all, and a host
        # that cannot has not failed a test, it has failed to have a sound card.
        "status": "certified" if certified else "not-certified",
        "physical_hardware_present": hardware.present,
        "verdict": hardware.reason,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "counts": {
            "kernel_cards": len(kernel.cards),
            "usb_audio_interfaces": len(usb.interfaces),
            "portaudio_devices": len(portaudio.devices),
            "physical_devices": len(hardware.physical_devices),
            "physical_playback_devices": len(hardware.playback_devices),
            "physical_capture_devices": len(hardware.capture_devices),
        },
        "kernel": kernel.as_dict(),
        "usb": usb.as_dict(),
        "portaudio": portaudio.as_dict(),
        "sound_server": server,
        "c4_baseline_comparison": baseline_comparison,
        "certification": {
            "certified_on_physical_hardware": certified,
            "blocking_reason": None if certified else hardware.reason,
            "require_physical_requested": bool(args.require_physical),
            "required_to_certify": [
                (
                    "attach a class-compliant audio interface to a host that "
                    "exposes /dev/snd, so the kernel binds a card"
                ),
                "python3 benchmarks/usb_audio_probe.py --require-physical",
                (
                    "python3 benchmarks/roundtrip_latency_probe.py "
                    "--require-physical --device <the interface> "
                    "--sink <its hardware sink>"
                ),
                (
                    "publish both reports alongside the existing loopback "
                    "evidence rather than in place of it"
                ),
            ],
        },
        "observations": observations,
        "config": {
            "sample_rate": args.sample_rate,
            "channels": args.channels,
            "buffer_frames_referenced": DEFAULT_BUFFER_FRAMES,
            "sysroot": str(args.sysroot),
            "baseline": _repository_relative(args.baseline),
        },
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor() or "unknown",
            "sounddevice": portaudio.sounddevice_version,
            "portaudio": portaudio.portaudio_version,
        },
        "limitation": (
            "This is an inventory, not a measurement: it establishes what kind of "
            "audio device exists on the host and therefore what kind of evidence "
            "a latency run on it can be. It opens no stream and times nothing. "
            + (
                "A physical device was found, so a round trip measured here can "
                "include a DAC and an ADC — but only once it is actually run "
                "against that device."
                if hardware.present
                else "No physical device was found: no /dev/snd, no card in "
                "/proc/asound, no USB audio class interface, and every PortAudio "
                "device is a plugin over PulseAudio's null sinks. Any latency "
                "measured on this host therefore excludes the DAC, the ADC, their "
                "filters and the analogue path, which is what the C4 report "
                "already states in physical_dac_adc: false. This probe "
                "corroborates that claim; it does not remove the limitation."
            )
        ),
    }


# ----------------------------------------------------------------------- main


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    hardware = detect_hardware(args.sysroot, args.sample_rate, args.channels)
    _progress(args.quiet, hardware.kernel.detail)
    _progress(args.quiet, hardware.usb.detail)
    _progress(args.quiet, hardware.portaudio.detail)

    server = scan_sound_server()
    _progress(args.quiet, str(server.get("detail", "no sound server answered")))

    baseline = load_baseline(args.baseline)
    comparison = compare_with_baseline(baseline, hardware, server, args.baseline)
    report = build_report(args, hardware, server, comparison)

    rendered = json.dumps(report, indent=2)
    print(rendered)
    if args.output is not None:
        try:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered + "\n", encoding="utf-8")
        except OSError as error:
            print(f"[usb-audio-probe] could not write {args.output}: {error}", file=sys.stderr)
            return 2
        _progress(args.quiet, f"report written to {args.output}")

    _progress(args.quiet, f"physical hardware present: {hardware.present} — {hardware.reason}")
    if args.require_physical and not hardware.present:
        print(
            "[usb-audio-probe] --require-physical: no physical audio device on this host; "
            f"{hardware.reason}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
