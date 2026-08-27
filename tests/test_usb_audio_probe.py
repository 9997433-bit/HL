"""Checks for the physical-device inventory behind the C4 hardware claim.

Three kinds of check live here, and they answer different questions.

The first reads the published report and asks whether it says what an honest
inventory has to say: what was looked for, what was found, and — on a host with
no sound card — that no measurement taken here can include a converter.

The second exercises the scanners against synthetic filesystem trees, in both
directions. A probe that reports "no hardware" on a host that genuinely has
none is indistinguishable from a probe that reports "no hardware" because it
cannot see. So the same code is pointed at a tree containing a USB audio
interface and required to find it, card, bus, PortAudio name and all.

The third asks the live host the same question the report was generated from,
so a report committed on one machine cannot silently describe another.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from benchmarks import usb_audio_probe as probe

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = REPOSITORY_ROOT / ".agent_workspace/v1.0/usb-audio-probe-report.json"
C4_REPORT_PATH = REPOSITORY_ROOT / ".agent_workspace/round3/roundtrip-latency-report.json"

#: A real ``/proc/asound/cards`` from a laptop with a class-compliant USB
#: interface plugged into it, alongside its built-in codec.
ASOUND_CARDS = """\
 0 [PCH            ]: HDA-Intel - HDA Intel PCH
                      HDA Intel PCH at 0xf7e10000 irq 145
 1 [USB            ]: USB-Audio - Scarlett 2i2 USB
                      Focusrite Scarlett 2i2 USB at usb-0000:00:14.0-2, high speed
"""


@pytest.fixture(scope="module")
def report() -> dict[str, Any]:
    assert REPORT_PATH.is_file(), (
        "run `python3 benchmarks/usb_audio_probe.py` to publish the device inventory"
    )
    return json.loads(REPORT_PATH.read_text(encoding="utf-8"))


# ------------------------------------------------------------------ the report


def test_report_identifies_itself(report: dict[str, Any]) -> None:
    assert report["schema_version"] == 1
    assert report["harness"] == "benchmarks/usb_audio_probe.py"
    assert report["checklist_item"] == "C4"
    assert report["evidence"] == "device-enumeration"
    assert report["status"] in {"certified", "not-certified"}
    assert isinstance(report["physical_hardware_present"], bool)
    assert report["verdict"].strip()
    assert {"python", "platform", "sounddevice", "portaudio"} <= set(report["environment"])


def test_the_verdict_follows_from_the_layers_that_were_scanned(report: dict[str, Any]) -> None:
    """Every claim in the headline has to be visible in the evidence under it."""
    counts = report["counts"]
    assert counts["kernel_cards"] == report["kernel"]["card_count"]
    assert counts["usb_audio_interfaces"] == report["usb"]["audio_class_interface_count"]
    assert counts["portaudio_devices"] == report["portaudio"]["device_count"]
    assert counts["physical_devices"] == report["portaudio"]["physical_device_count"]
    assert counts["physical_devices"] == sum(
        1 for device in report["portaudio"]["devices"] if device["physical"]
    )
    certified = report["status"] == "certified"
    assert certified is report["physical_hardware_present"]
    assert certified is report["certification"]["certified_on_physical_hardware"]
    assert certified == (counts["physical_devices"] > 0)


def test_every_device_carries_the_reason_it_was_classified(report: dict[str, Any]) -> None:
    devices = report["portaudio"]["devices"]
    assert devices, "PortAudio advertised nothing at all, which is itself a finding to record"
    for device in devices:
        assert device["classification"]
        assert device["reason"].strip()
        assert isinstance(device["physical"], bool)
        assert device["max_input_channels"] >= 0
        assert device["max_output_channels"] >= 0
        # Enumeration is only useful if it also says whether the product's own
        # format would be accepted, so a "device" that cannot carry 48 kHz
        # float32 is visible as such.
        assert {"input", "output"} <= set(device["format_check"])


def test_a_host_without_hardware_says_so_rather_than_staying_quiet(
    report: dict[str, Any],
) -> None:
    if report["physical_hardware_present"]:
        pytest.skip("this host has physical audio hardware")
    assert report["status"] == "not-certified"
    assert report["counts"]["physical_devices"] == 0
    assert report["certification"]["blocking_reason"].strip()
    assert report["certification"]["required_to_certify"]
    limitation = report["limitation"]
    assert "DAC" in limitation and "ADC" in limitation
    # And each layer records what it looked at, so "not found" can be told
    # apart from "not looked for".
    assert report["kernel"]["detail"].strip()
    assert report["usb"]["detail"].strip()
    assert report["portaudio"]["detail"].strip()
    assert not any(observation["found"] for observation in report["observations"])


def test_the_inventory_and_the_c4_report_describe_the_same_host(
    report: dict[str, Any],
) -> None:
    """Two artifacts about one machine must not disagree about its hardware."""
    comparison = report["c4_baseline_comparison"]
    if not comparison["available"]:
        pytest.skip("no C4 round-trip report has been published")
    baseline = json.loads(C4_REPORT_PATH.read_text(encoding="utf-8"))
    assert comparison["roundtrip_latency_ms"] == baseline["roundtrip_latency_ms"]
    assert comparison["threshold_ms"] == baseline["threshold_ms"]
    assert comparison["baseline_claims_physical_dac_adc"] == baseline["physical_dac_adc"]
    assert comparison["agrees_with_this_probe"] is True
    assert baseline["physical_dac_adc"] is report["physical_hardware_present"]


def test_the_comparison_names_the_stages_the_loopback_could_not_contain(
    report: dict[str, Any],
) -> None:
    comparison = report["c4_baseline_comparison"]
    if not comparison["available"]:
        pytest.skip("no C4 round-trip report has been published")
    stages = comparison["signal_path"]
    assert stages
    for stage in stages:
        assert stage["measured_here"] in {"present", "absent", "optional"}
        assert stage["on_physical_hardware"] in {"present", "absent", "optional"}

    absent = comparison["stages_absent_from_this_host"]
    if report["physical_hardware_present"]:
        return
    assert any("digital-to-analogue" in stage for stage in absent)
    assert any("analogue-to-digital" in stage for stage in absent)
    # The converter cost is an estimate quoted from the round-trip probe, and
    # has to be labelled as one wherever it appears.
    overhead = comparison["converter_overhead"]
    assert overhead["measured"] is False
    assert overhead["estimate_ms"] == list(probe.CONVERTER_ESTIMATE_MS)
    assert overhead["worst_case_roundtrip_with_estimate_ms"] == pytest.approx(
        comparison["roundtrip_latency_ms"] + probe.CONVERTER_ESTIMATE_MS[1], abs=1e-3
    )
    assert overhead["still_within_threshold"] is (
        overhead["worst_case_roundtrip_with_estimate_ms"] < comparison["threshold_ms"]
    )
    assert comparison["conclusion"].strip()


def test_a_null_sink_only_server_is_recorded_as_such(report: dict[str, Any]) -> None:
    server = report["sound_server"]
    if not server.get("pulseaudio_available"):
        pytest.skip("no PulseAudio server answered on this host")
    assert server["null_sink_count"] + server["hardware_sink_count"] <= len(server["sinks"])
    if server["null_sink_only"]:
        assert server["hardware_sink_count"] == 0
        assert report["physical_hardware_present"] is False


# ------------------------------------------------------- the scanners, both ways


def _host_without_sound(root: Path) -> Path:
    """A container like this one: a Linux host with no card and no USB view."""
    (root / "proc").mkdir(parents=True, exist_ok=True)
    (root / "sys/class").mkdir(parents=True, exist_ok=True)
    return root


def _host_with_a_usb_interface(root: Path) -> Path:
    """A laptop with a built-in codec and a class-compliant interface attached."""
    snd = root / "dev/snd"
    snd.mkdir(parents=True)
    for node in ("controlC0", "pcmC0D0p", "pcmC0D0c", "controlC1", "pcmC1D0p", "pcmC1D0c", "timer"):
        (snd / node).touch()

    asound = root / "proc/asound"
    asound.mkdir(parents=True)
    (asound / "cards").write_text(ASOUND_CARDS, encoding="utf-8")

    pci_card = root / "sys/devices/pci0000:00/0000:00:1f.3"
    pci_card.mkdir(parents=True)
    usb_card = root / "sys/devices/pci0000:00/0000:00:14.0/usb1/1-2/1-2:1.0"
    usb_card.mkdir(parents=True)

    sound_class = root / "sys/class/sound"
    sound_class.mkdir(parents=True)
    (sound_class / "card0").mkdir()
    (sound_class / "card0" / "device").symlink_to(pci_card)
    (sound_class / "card1").mkdir()
    (sound_class / "card1" / "device").symlink_to(usb_card)

    devices = root / "sys/bus/usb/devices"
    devices.mkdir(parents=True)
    interface = devices / "1-2:1.0"
    interface.mkdir()
    (interface / "bInterfaceClass").write_text("01\n", encoding="utf-8")
    (interface / "bInterfaceSubClass").write_text("01\n", encoding="utf-8")
    parent = devices / "1-2"
    parent.mkdir()
    for name, value in (
        ("idVendor", "1235"),
        ("idProduct", "8210"),
        ("product", "Scarlett 2i2 USB"),
        ("manufacturer", "Focusrite"),
        ("speed", "480"),
    ):
        (parent / name).write_text(f"{value}\n", encoding="utf-8")
    # A neighbouring keyboard, so the class filter has something to reject.
    keyboard = devices / "1-3:1.0"
    keyboard.mkdir()
    (keyboard / "bInterfaceClass").write_text("03\n", encoding="utf-8")
    return root


def test_kernel_scan_finds_nothing_on_a_host_with_no_card(tmp_path: Path) -> None:
    kernel = probe.scan_kernel(_host_without_sound(tmp_path))

    assert kernel.cards == []
    assert kernel.dev_snd_present is False
    assert kernel.pcm_nodes == []
    assert "no sound card" in kernel.detail


def test_kernel_scan_finds_the_cards_and_their_buses(tmp_path: Path) -> None:
    kernel = probe.scan_kernel(_host_with_a_usb_interface(tmp_path))

    assert kernel.dev_snd_present is True
    assert "pcmC1D0p" in kernel.pcm_nodes
    assert [card.card_id for card in kernel.cards] == ["PCH", "USB"]
    assert [card.driver for card in kernel.cards] == ["HDA-Intel", "USB-Audio"]
    assert kernel.cards[1].description == "Scarlett 2i2 USB"
    # The bus comes from the sysfs path, not from the driver's name.
    assert kernel.cards[0].bus == "pci"
    assert kernel.cards[0].usb is False
    assert kernel.cards[1].bus == "usb"
    assert kernel.cards[1].usb is True


def test_card_parser_ignores_the_continuation_lines() -> None:
    cards = probe.parse_asound_cards(ASOUND_CARDS)

    assert len(cards) == 2
    assert cards[0] == probe.SoundCard(0, "PCH", "HDA-Intel", "HDA Intel PCH")


def test_usb_scan_keeps_audio_class_interfaces_and_drops_the_rest(tmp_path: Path) -> None:
    evidence = probe.scan_usb_audio(_host_with_a_usb_interface(tmp_path))

    assert evidence.sysfs_available is True
    assert len(evidence.interfaces) == 1
    found = evidence.interfaces[0]
    assert found.interface == "1-2:1.0"
    assert found.interface_class == probe.USB_AUDIO_INTERFACE_CLASS
    # Read from the parent device, which is where the strings live.
    assert found.product == "Scarlett 2i2 USB"
    assert found.manufacturer == "Focusrite"
    assert (found.vendor_id, found.product_id) == ("1235", "8210")


def test_usb_scan_distinguishes_an_empty_bus_from_no_bus_at_all(tmp_path: Path) -> None:
    """"Nothing attached" and "cannot see the bus" are different findings."""
    empty_bus = tmp_path / "empty"
    (empty_bus / "sys/bus/usb/devices").mkdir(parents=True)
    seen = probe.scan_usb_audio(empty_bus)
    unseen = probe.scan_usb_audio(_host_without_sound(tmp_path / "blind"))

    assert seen.sysfs_available is True
    assert "no audio class interface" in seen.detail
    assert unseen.sysfs_available is False
    assert "no view of a USB bus" in unseen.detail


# ------------------------------------------------------------- classification


def _kernel(cards: list[probe.SoundCard], *, applicable: bool = True) -> probe.KernelEvidence:
    return probe.KernelEvidence(
        applicable=applicable,
        platform="Linux" if applicable else "Darwin",
        dev_snd_present=bool(cards),
        dev_snd_nodes=[],
        pcm_nodes=[],
        proc_asound_present=bool(cards),
        sys_class_sound_present=bool(cards),
        cards=cards,
        detail="synthetic",
    )


@pytest.mark.parametrize(
    "name",
    ["pulse", "default", "sysdefault", "dmix", "pipewire", "jack", "null", "loopback48.monitor"],
)
def test_no_plugin_is_called_physical_on_a_host_with_a_card(name: str) -> None:
    """The classifier must not be fooled by a plugin sitting next to real hardware."""
    kernel = _kernel([probe.SoundCard(0, "PCH", "HDA-Intel", "HDA Intel PCH", "pci")])

    classification, physical, reason = probe.classify_device(name, "ALSA", kernel)

    assert physical is False
    assert classification in {"virtual", "alsa-plugin", "indeterminate"}
    assert reason.strip()


@pytest.mark.parametrize(
    "name",
    [
        "front:CARD=USB,DEV=0",
        "hw:1,0",
        "plughw:1,0",
        "Scarlett 2i2 USB: USB Audio (hw:1,0)",
    ],
)
def test_a_name_that_addresses_a_card_is_physical(name: str) -> None:
    kernel = _kernel(
        [
            probe.SoundCard(0, "PCH", "HDA-Intel", "HDA Intel PCH", "pci"),
            probe.SoundCard(1, "USB", "USB-Audio", "Scarlett 2i2 USB", "usb"),
        ]
    )

    classification, physical, reason = probe.classify_device(name, "ALSA", kernel)

    assert (classification, physical) == ("physical", True)
    assert reason.strip()


def test_nothing_is_physical_when_the_kernel_has_no_card() -> None:
    """The kernel has the last word: a name cannot conjure a converter."""
    kernel = _kernel([])

    classification, physical, reason = probe.classify_device("hw:0,0", "ALSA", kernel)

    assert (classification, physical) == ("unbacked", False)
    assert "no sound card" in reason


def test_a_platform_without_alsa_nodes_says_where_its_answer_came_from() -> None:
    kernel = _kernel([], applicable=False)

    classification, physical, reason = probe.classify_device(
        "MacBook Pro Speakers", "Core Audio", kernel
    )

    assert (classification, physical) == ("hostapi-reported", True)
    assert "host API" in reason


# --------------------------------------------------------- the assembled report


def _evidence(*, present: bool, sysroot: Path) -> probe.HardwareEvidence:
    """A hardware verdict assembled by hand, so both outcomes can be rendered."""
    kernel = probe.scan_kernel(sysroot)
    usb = probe.scan_usb_audio(sysroot)
    device = probe.AudioDevice(
        index=0,
        name="Scarlett 2i2 USB: USB Audio (hw:1,0)",
        hostapi_index=0,
        hostapi="ALSA",
        max_input_channels=2,
        max_output_channels=2,
        default_samplerate=48_000.0,
        default_low_input_latency_ms=2.667,
        default_low_output_latency_ms=2.667,
        default_high_input_latency_ms=10.667,
        default_high_output_latency_ms=10.667,
        classification="physical",
        physical=True,
        reason="synthetic",
        format_check={"input": {"supported": True}, "output": {"supported": True}},
    )
    portaudio = probe.PortAudioEvidence(
        available=True,
        sounddevice_version="0.5.6",
        portaudio_version="synthetic",
        host_apis=[{"index": 0, "name": "ALSA"}],
        devices=[device] if present else [],
        default_input_device=0,
        default_output_device=0,
        detail="synthetic",
    )
    return probe.HardwareEvidence(
        present=present,
        reason="synthetic verdict",
        kernel=kernel,
        usb=usb,
        portaudio=portaudio,
    )


def test_report_from_a_host_with_hardware_is_certified(tmp_path: Path) -> None:
    args = probe._parse_args(["--quiet"])
    evidence = _evidence(present=True, sysroot=_host_with_a_usb_interface(tmp_path))
    baseline = json.loads(C4_REPORT_PATH.read_text(encoding="utf-8"))
    comparison = probe.compare_with_baseline(
        baseline, evidence, {"null_sink_only": False}, args.baseline
    )

    built = probe.build_report(args, evidence, {"hardware_sink_count": 1}, comparison)

    assert built["status"] == "certified"
    assert built["physical_hardware_present"] is True
    assert built["counts"]["usb_audio_interfaces"] == 1
    assert built["counts"]["physical_playback_devices"] == 1
    assert built["counts"]["physical_capture_devices"] == 1
    assert built["certification"]["blocking_reason"] is None
    # The baseline was measured without a converter, so with hardware present
    # the two artifacts describe different situations and the report says so
    # instead of quietly agreeing.
    assert comparison["agrees_with_this_probe"] is False
    assert "can be repeated on a real converter" in comparison["conclusion"]
    json.dumps(built)


def test_report_from_a_host_without_hardware_refuses_to_claim_certification(
    tmp_path: Path,
) -> None:
    args = probe._parse_args(["--quiet"])
    evidence = _evidence(present=False, sysroot=_host_without_sound(tmp_path))
    comparison = probe.compare_with_baseline({}, evidence, {}, args.baseline)

    built = probe.build_report(args, evidence, {"pulseaudio_available": False}, comparison)

    assert built["status"] == "not-certified"
    assert built["physical_hardware_present"] is False
    assert built["counts"]["physical_devices"] == 0
    assert built["certification"]["blocking_reason"] == "synthetic verdict"
    assert "No physical device was found" in built["limitation"]
    # A missing baseline is reported as missing rather than assumed away.
    assert comparison["available"] is False
    json.dumps(built)


def test_require_physical_fails_the_run_on_a_host_with_no_card(tmp_path: Path) -> None:
    output = tmp_path / "report.json"
    root = _host_without_sound(tmp_path / "root")

    code = probe.main(
        ["--sysroot", str(root), "--require-physical", "--quiet", "--output", str(output)]
    )

    assert code == 1
    # The gate fails the run and still publishes what it found, because the
    # inventory is the evidence for why the run failed.
    written = json.loads(output.read_text(encoding="utf-8"))
    assert written["physical_hardware_present"] is False
    assert written["certification"]["require_physical_requested"] is True


def test_without_the_flag_an_absent_card_is_a_result_not_an_error(tmp_path: Path) -> None:
    output = tmp_path / "report.json"
    root = _host_without_sound(tmp_path / "root")

    assert probe.main(["--sysroot", str(root), "--quiet", "--output", str(output)]) == 0
    assert json.loads(output.read_text(encoding="utf-8"))["status"] == "not-certified"


# --------------------------------------------------------------- the live host


def test_the_live_host_agrees_with_the_published_report(report: dict[str, Any]) -> None:
    """Re-run the scan here: a committed report must not describe another machine.

    Only the hardware verdict is compared. Device counts and latencies are
    allowed to differ between the machine that published the report and the one
    running the tests; whether a converter exists is not.
    """
    live = probe.detect_hardware()

    assert live.present == report["physical_hardware_present"]
    assert live.reason.strip()
    if not live.present:
        assert not live.physical_devices
        assert live.kernel.cards == [] or not live.portaudio.devices


def test_the_live_scan_is_internally_consistent() -> None:
    live = probe.detect_hardware()

    if live.kernel.applicable and not live.kernel.cards:
        assert live.present is False
        assert all(not device.physical for device in live.portaudio.devices)
    assert all(device in live.physical_devices for device in live.playback_devices)
    assert all(device.max_output_channels > 0 for device in live.playback_devices)
    assert all(device.max_input_channels > 0 for device in live.capture_devices)
