# Hardware certification runbook: C4 on a physical USB interface

SOTA checklist item C4 (round-trip latency under 15 ms at a 128-frame buffer)
is currently backed by **server-loopback evidence**: the published
[`roundtrip-latency-report.json`](../.agent_workspace/round3/roundtrip-latency-report.json)
was measured through a PulseAudio null sink and its monitor source, because the
CI host has no sound card. The report says so in `physical_dac_adc: false`, and
[`usb-audio-probe-report.json`](../.agent_workspace/v1.0/usb-audio-probe-report.json)
corroborates it with a scan of the kernel, the USB bus, PortAudio and the sound
server. What the loopback evidence cannot contain — the DAC, the ADC, their
filters, the analogue path and a real device's interrupt cadence — is exactly
what this runbook adds.

This document is the step-by-step for a person standing at a bench with a
class-compliant USB audio interface (a Focusrite Scarlett 2i2 is the working
example throughout; any class-compliant interface with a line output and a
line input will do). The whole procedure is also automated as
[`scripts/run-hardware-certification.sh`](../scripts/run-hardware-certification.sh),
which runs the same steps in the same order and refuses honestly when the
hardware is not there.

Both probes involved gate themselves with `--require-physical`:

* [`benchmarks/usb_audio_probe.py`](../benchmarks/usb_audio_probe.py) — the
  device inventory. Proves a converter exists: a kernel-bound card, a USB
  audio-class interface, and a PortAudio device that addresses the card.
* [`benchmarks/roundtrip_latency_probe.py`](../benchmarks/roundtrip_latency_probe.py)
  — the measurement. Plays chirps out of the interface, captures them back
  through the loopback cable, and grades the delay against the 15 ms budget.

## What you need

* A Linux host with a spare USB port. The kernel evidence the probes read
  (`/dev/snd`, `/proc/asound/cards`, `/sys/class/sound`, `/sys/bus/usb/devices`)
  only exists on Linux; run on bare metal or in a container with the sound
  devices passed through (`--device /dev/snd -v /sys:/sys:ro` at minimum).
* A class-compliant USB audio interface — Focusrite Scarlett 2i2/4i4, MOTU M2,
  Behringer UMC202HD, or similar. "Class-compliant" means it advertises USB
  `bInterfaceClass 01` and works with the stock `snd-usb-audio` driver, which
  is what the USB-bus layer of the probe verifies.
* One balanced (TRS) or instrument cable to close the loop: line/monitor
  output → line input on the same interface.
* This repository, Python 3 with the project dependencies installed
  (`pip install -r requirements.txt`, which provides `sounddevice` and
  `numpy`), and the ALSA/PulseAudio userspace (`alsa-utils`, `pulseaudio-utils`
  or `pipewire-pulse` for `pactl`).
* Your user in the `audio` group (or root), so `/dev/snd` is readable.

## Step 1 — Attach the interface and load the kernel modules

Plug the interface in. On a stock desktop kernel, udev loads `snd-usb-audio`
automatically on hotplug; on a minimal or server kernel, load the modules
yourself:

```bash
sudo modprobe snd snd-usb-audio
```

Then verify each layer the probe will later verify for you:

```bash
lsusb | grep -i audio            # the device is on the bus
cat /proc/asound/cards           # the kernel bound a card to it
ls /dev/snd                      # PCM device nodes exist (pcmC*D*p / pcmC*D*c)
```

A healthy `/proc/asound/cards` looks like this — note the card id (`USB` here),
which appears again in every device name below:

```
 0 [PCH            ]: HDA-Intel - HDA Intel PCH
                      HDA Intel PCH at 0xf7e10000 irq 145
 1 [USB            ]: USB-Audio - Scarlett 2i2 USB
                      Focusrite Scarlett 2i2 USB at usb-0000:00:14.0-2, high speed
```

If no card appears, nothing above the kernel can fix it: check `dmesg` for the
enumeration, try another port or cable, and confirm `snd_usb_audio` is actually
loaded (`lsmod | grep snd_usb_audio`).

## Step 2 — Cable the loopback

Connect the interface's line/monitor output back into its own line input:

* **Scarlett 2i2**: right monitor output (TRS) → input 1. Set input 1 to
  line level (`INST` off), 48V phantom power **off**, and — important —
  **Direct Monitor off**. Direct Monitor mixes the input straight to the
  output inside the interface, which would give the chirp a second, shorter
  path around the loop and corrupt the measurement.
* Set the input gain so a full-scale playback comes back well below clipping;
  around a quarter turn is typically right. The probe's chirps are emitted at
  0.5 amplitude and detected by cross-correlation, so exact level does not
  matter — clipping and silence do.

## Step 3 — Point the sound server at the card and set the default device

The probes name their endpoints explicitly, so they do not depend on the
system default — but setting it makes every ad-hoc check (`speaker-test`,
`arecord`, your ears) go to the right place, and unmuting is not optional.

Find the interface's sink and source:

```bash
pactl list short sinks
pactl list short sources
```

The hardware sink is the one whose driver column says `module-alsa-card.c`
(a `null-sink` driver means there is no device behind it), named like
`alsa_output.usb-Focusrite_Scarlett_2i2_USB-00.analog-stereo`. Make it the
default and make sure both directions are unmuted at full scale:

```bash
SINK=alsa_output.usb-Focusrite_Scarlett_2i2_USB-00.analog-stereo
SOURCE=alsa_input.usb-Focusrite_Scarlett_2i2_USB-00.analog-stereo

pactl set-default-sink   "$SINK"
pactl set-default-source "$SOURCE"
pactl set-sink-mute      "$SINK" 0
pactl set-sink-volume    "$SINK" 100%
pactl set-source-mute    "$SOURCE" 0
pactl set-source-volume  "$SOURCE" 100%
```

## Step 4 — Run the device probe with `--require-physical`

```bash
python3 benchmarks/usb_audio_probe.py --require-physical \
  --output .agent_workspace/v1.0/hardware/usb-audio-probe-report.json
```

`--require-physical` turns "no converter on this host" into exit code 1, so a
run on the wrong machine stops here instead of publishing a hardware report
that describes no hardware. On success the report's `status` is `"certified"`,
`physical_hardware_present` is `true`, and — the part you need for step 5 —
`portaudio.devices` lists every device with `"physical": true` and the reason
it was classified that way. Pick the full-duplex one that addresses your card,
e.g. `front:CARD=USB,DEV=0` or `hw:CARD=USB,DEV=0`.

The `--output` path is deliberately **not** the default: the default path,
`.agent_workspace/v1.0/usb-audio-probe-report.json`, is the CI host's honest
negative inventory, and the probe's own `required_to_certify` list says to
publish hardware evidence *alongside* the loopback evidence rather than in
place of it.

## Step 5 — Run the round-trip probe with `--require-physical`

```bash
python3 benchmarks/roundtrip_latency_probe.py --require-physical \
  --device "hw:CARD=USB,DEV=0" \
  --sink   "$SINK" \
  --output .agent_workspace/v1.0/hardware/roundtrip-latency-report.json
```

* `--device` is the PortAudio device from step 4. Opening `hw:` (or `front:`)
  directly puts the card's own DMA, interrupt cadence, DAC, your cable and the
  ADC inside the measured loop, with no sound-server stage in the way. If
  PortAudio reports the device as busy, PulseAudio is holding it — release it
  for the duration of the run with `pasuspender -- python3 benchmarks/...`, or
  `pactl suspend-sink "$SINK" 1` (and `suspend-source`) before and `... 0`
  after.
* `--sink` names the hardware sink so the run can verify the loop it is asked
  about is the one backed by the card. With `--require-physical`, the probe
  refuses to measure (exit code 2) unless the host has a physical device *and*
  that sink is hardware-backed — the same two facts that later become
  `physical_dac_adc: true` in the report.

The probe runs its full protocol regardless of the loop being physical: five
sessions per scenario, an engine-render scenario that puts the product's own
transport in the loop, cold-start and settling measurements published
separately, and four controls (silence, injected delay, latency sensitivity,
wall clock). Exit code 0 with `status: "pass"` means the worst steady-state
round trip of every kept measurement cleared the 15 ms budget with zero xruns
and all controls passing.

## Step 6 — Republish the reports

Two new artifacts now exist, and they go in **alongside** the loopback
evidence, never in place of it:

```
.agent_workspace/v1.0/hardware/usb-audio-probe-report.json
.agent_workspace/v1.0/hardware/roundtrip-latency-report.json
```

Sanity-check them before committing:

* the usb probe report has `status: "certified"` and names your interface
  under `usb.audio_class_interfaces`;
* the round-trip report has `physical_dac_adc: true`,
  `loopback_path: "hardware-sink-monitor"`, `status: "pass"`, and its
  `hardware` block records the sink driver it verified;
* the two agree — the round-trip report's `hardware` block is produced by the
  same scan the usb probe publishes.

Then commit both files with a message that names the interface and the host
they were measured on. The pre-existing reports at the default paths
(`.agent_workspace/round3/roundtrip-latency-report.json` and
`.agent_workspace/v1.0/usb-audio-probe-report.json`) describe the CI host and
stay as they are; note that `tests/test_usb_audio_probe.py` cross-checks those
default-path artifacts against the live host, so run that suite on the CI
host — on the bench it would correctly complain that the committed CI
inventory does not describe the bench.

Finally, run the documentation suite anywhere:

```bash
python3 -m pytest tests/test_hardware_certification_docs.py
```

## The one-command version

```bash
scripts/run-hardware-certification.sh
```

runs steps 4 and 5 in order: the device probe with `--require-physical`, then
— only if a converter was proven — sink and device auto-discovery, then the
round-trip probe with `--require-physical`. Both reports land in
`.agent_workspace/v1.0/hardware/`. On a host without hardware it exits 1
after publishing the usb probe's honest negative report, which is the correct
behaviour for a CI job that merely *hopes* a runner has an interface attached.

Options and environment overrides (`--device`, `--sink`, `--report-dir`,
`HARDWARE_REPORT_DIR`, `PYTHON_BIN`) are documented in
`scripts/run-hardware-certification.sh --help`.

Exit codes:

| Code | Meaning |
|---|---|
| 0 | Both probes passed on physical hardware; reports published. |
| 1 | No physical audio device on this host (the usb probe's `--require-physical` gate fired, or no hardware sink / full-duplex device could be found). |
| 2 | Hardware is present but the round-trip run refused or failed — device busy, cable not looped, xruns, controls, or the budget. |

## Troubleshooting

* **`no /dev/snd`** — the kernel never saw a card: step 1, `dmesg`, another
  port. In a container, the host's `/dev/snd` must be passed through.
* **Card visible but the usb probe says `not-certified`** — read the report's
  `portaudio.devices[].reason` fields: PortAudio must advertise a device that
  addresses the card (`hw:`/`front:`/`CARD=` names). An ALSA install without
  the card's PCM plugins, or a `sounddevice` built without ALSA, both look
  like this.
* **Round-trip probe exits 2 with "the sink … is driven by module-null-sink"**
  — `--sink` names a virtual sink; pick the `module-alsa-card.c` one from
  `pactl list short sinks`.
* **`no confident detections`** — the chirp never came back: the cable is in
  the wrong jack, the input is muted or at zero gain, or Direct Monitor is
  feeding the loop internally. Verify by playing anything and watching
  `pactl list sources` levels, or `arecord -D hw:CARD=USB -f FLOAT_LE -r 48000 -c 2 -d 3 -t wav check.wav`.
* **xruns discard every session** — close other audio clients, keep the
  128-frame buffer, and prefer the direct `hw:` device over routing through
  the server; a loaded desktop may also need `threadirqs` or an `-rt` kernel
  to hold a 2.7 ms buffer.
