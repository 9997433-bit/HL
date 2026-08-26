# Third-Party Software Notices

Audit snapshot: 2026-08-26, branch `agent/audio-analysis-software`.

Audio Studio is declared as MIT in `audio-studio/pyproject.toml`. This file is
an inventory and distribution policy, not a replacement for the license texts
that accompany each upstream package. Version ranges below come from the
repository manifests; a release must also retain the license files installed
inside each wheel or native package.

## Distribution profiles

| Profile | Manifest | Included |
|---|---|---|
| Default application | `audio-studio/pyproject.toml` | NumPy, SciPy, SoundFile, PySide6-Essentials |
| Hardware-audio extra | `audio-studio/pyproject.toml` `[audio]` | sounddevice, PyAudio, and a PortAudio library that is bundled by the sounddevice wheel or loaded dynamically |
| Plugin-host extra | `audio-studio/pyproject.toml` `[plugins]` | pedalboard (GPL-3.0; opt-in only, lazily imported, never bundled into MIT artifacts — see the pedalboard section below) |
| Full developer install | `audio-studio/requirements.txt` and `requirements-dev.txt` | Default application, sounddevice, PyAudio, and test/quality tools |
| Probe/benchmark environment | root `requirements.txt` and `requirements-dev.txt` | NumPy, SciPy, sounddevice, SoundFile, librosa, platformdirs, and test/quality tools |
| CI | `.github/requirements.in` and `.github/requirements.lock` | Default application test stack, pinned with direct CI transitives |

The default application profile contains no component licensed under the
unmodified GPL. PyQt6 is absent from all manifests; pedalboard appears only
as the opt-in `[plugins]` extra and is never part of the default profile.
The GPL exceptions and opt-in policy are documented below.

## Application and repository runtime dependencies

“License pointer” links to the upstream license text or canonical licensing
page, satisfying the full-text-or-pointer requirement. Wheel builds can carry
additional notices for bundled numerical or codec libraries; those notices
must be redistributed unchanged.

| Component | Declared version | Use | License | Upstream / license pointer |
|---|---|---|---|---|
| NumPy | `>=1.24`; root/CI pin `2.5.2` | Arrays, buffers, DSP kernels | BSD-3-Clause; wheels also carry notices for bundled code | [upstream](https://numpy.org/) / [license](https://github.com/numpy/numpy/blob/main/LICENSE.txt) |
| SciPy | `>=1.10`; root/CI pin `1.18.1` | Signal processing, filters, resampling | BSD-3-Clause; wheel-dependent OpenBLAS/LAPACK/GCC runtime notices apply | [upstream](https://scipy.org/) / [license and bundled notices](https://github.com/scipy/scipy/blob/main/LICENSE.txt) |
| SoundFile (`python-soundfile`) | `>=0.12.1`; root/CI pin `0.14.0` | Python binding for audio file I/O | BSD-3-Clause | [upstream](https://github.com/bastibe/python-soundfile) / [license](https://github.com/bastibe/python-soundfile/blob/master/LICENSE) |
| PySide6-Essentials | `>=6.6`; CI pin `6.11.2` | Qt 6 GUI binding | LGPL-3.0-only OR GPL/commercial; this project selects LGPL-3.0 | [upstream](https://doc.qt.io/qtforpython-6/) / [licensing](https://doc.qt.io/qtforpython-6/licenses.html) |
| Shiboken6 | transitive through PySide6-Essentials; CI pin `6.11.2` | Python/C++ binding runtime | LGPL-3.0-only OR GPL/commercial; this project selects LGPL-3.0 | [upstream](https://code.qt.io/cgit/pyside/pyside-setup.git/) / [LGPL-3.0 text](https://www.gnu.org/licenses/lgpl-3.0.html) |
| PyAudio | `[audio] >=0.2.13`; included by the full developer requirements | Optional PortAudio input backend and fallback output backend | MIT | [upstream](https://people.csail.mit.edu/hubert/pyaudio/) / [license](https://github.com/jleb/pyaudio/blob/master/LICENSE.txt) |
| sounddevice | `[audio] >=0.4.6`; root pin `0.5.6` | Preferred PortAudio output backend; also the device probe and repository audio environment | MIT; wheels bundle PortAudio, whose notice must be redistributed | [upstream](https://python-sounddevice.readthedocs.io/) / [license](https://github.com/spatialaudio/python-sounddevice/blob/master/LICENSE) |
| librosa | root pin `1.0.0` | Analysis/probe environment | ISC | [upstream](https://librosa.org/) / [license](https://github.com/librosa/librosa/blob/main/LICENSE.md) |
| platformdirs | root pin `4.11.4` | Cross-platform data/cache locations for repository tooling | MIT | [upstream](https://platformdirs.readthedocs.io/) / [license](https://github.com/tox-dev/platformdirs/blob/main/LICENSE) |

The root probe environment is not packaged into the default Audio Studio
wheel. Its resolver may install additional transitive packages, especially
through librosa. Those packages retain their own wheel notices. A desktop
installer must be built from a lock/SBOM and include those notices; the root
requirements file by itself is not a redistributable binary bill of materials.

## Native, codec, and build-dependent libraries

| Component | Status and use | License | Upstream / license pointer |
|---|---|---|---|
| libsndfile | Loaded dynamically by SoundFile; PyPI SoundFile wheels may bundle it | LGPL-2.1-or-later | [upstream](https://libsndfile.github.io/libsndfile/) / [license](https://github.com/libsndfile/libsndfile/blob/master/COPYING) |
| PortAudio | Bundled in the sounddevice wheels, otherwise loaded dynamically by PyAudio/sounddevice or installed by the OS | MIT | [upstream](https://www.portaudio.com/) / [license](https://github.com/PortAudio/portaudio/blob/master/LICENSE.txt) |
| FFmpeg | Invoked only as a separate `subprocess`; Docker/dev environments install an OS package; it is not linked into or bundled with the application | LGPL-2.1-or-later by default; GPL-2.0-or-later when built with GPL parts; some builds are non-redistributable | [upstream](https://ffmpeg.org/) / [legal and license information](https://ffmpeg.org/legal.html) |
| libsoxr / python-soxr | May be resolved transitively by the root librosa environment; not a direct application dependency | LGPL-2.1-or-later | [upstream](https://sourceforge.net/projects/soxr/) / [license](https://sourceforge.net/p/soxr/code/ci/master/tree/LICENCE) |
| OpenBLAS and LAPACK | May be bundled in NumPy/SciPy wheels | BSD-family | [OpenBLAS license](https://github.com/OpenMathLib/OpenBLAS/blob/develop/LICENSE) / [LAPACK license](https://github.com/Reference-LAPACK/lapack/blob/master/LICENSE) |
| GCC runtime libraries | Build-dependent NumPy/SciPy wheel runtime; includes libgfortran and libquadmath on some platforms | GPL-3.0-or-later WITH GCC-exception-3.1; libquadmath LGPL-2.1-or-later | [GCC runtime exception](https://www.gnu.org/licenses/gcc-exception-3.1.html) / [GCC licenses](https://gcc.gnu.org/onlinedocs/libstdc++/manual/license.html) |
| FLAC, Ogg, Vorbis, Opus | Codec libraries that may be linked into a libsndfile/SoundFile distribution | BSD-3-Clause | [Xiph licenses](https://www.xiph.org/licenses/) |
| mpg123 | Build-dependent MP3 decoder behind libsndfile | LGPL-2.1-only | [upstream](https://www.mpg123.de/) / [license](https://www.mpg123.de/cgi-bin/scm/mpg123/trunk/COPYING?view=markup) |
| LAME | Build-dependent MP3 encoder behind libsndfile/FFmpeg | LGPL-2.0-or-later | [upstream](https://lame.sourceforge.io/) / [license](https://sourceforge.net/p/lame/svn/HEAD/tree/trunk/lame/COPYING) |

Presence of a build-dependent library must be determined from the exact release
artifact, not inferred from this table. Preserve the `licenses/` directories
from Python wheels and the notices from native packages in any installer.

## LGPL components: relinking and source availability

Audio Studio uses LGPL components only through replaceable shared libraries:

- **PySide6/Qt/Shiboken6:** Python imports dynamically linked Qt shared
  libraries. Do not statically link Qt or freeze it into a non-replaceable
  executable. Recipients must be able to replace the LGPL libraries. Matching
  source is available from the [Qt source archives](https://download.qt.io/archive/qt/)
  and [PySide source repository](https://code.qt.io/cgit/pyside/pyside-setup.git/).
- **libsndfile:** SoundFile loads a shared libsndfile. Keep it replaceable and
  provide this notice plus the [corresponding source releases](https://github.com/libsndfile/libsndfile/releases)
  when distributing a bundled binary.
- **libsoxr:** when present through the probe environment, keep it dynamically
  replaceable and provide the [source](https://sourceforge.net/p/soxr/code/ci/master/tree/).
- **FFmpeg:** the application currently discovers an independently installed
  executable and communicates through files/pipes. If an installer later
  bundles FFmpeg, use an LGPL build without GPL/nonfree options, include its
  exact configure flags and license, and provide the matching source or a
  durable written source offer as required by that build's license.

## GPL and proprietary opt-ins

### pedalboard

[pedalboard](https://github.com/spotify/pedalboard) is GPL-3.0 and incorporates
GPL/commercial components including JUCE, Rubber Band, and FFTW. It is **not a
default dependency and is never imported at application import time**. It is
declared only as the explicit `plugins` optional extra
(`pip install "audio-studio[plugins]"`, `pedalboard>=0.9.0`) and the entire
contact surface is the isolated bridge module
`audio-studio/audio_studio/plugins/pedalboard_bridge.py`, which imports
pedalboard lazily the first time a plugin is loaded and raises a clear error
when the extra is absent. No other module imports pedalboard, and the extra is
excluded from the CI lock and from every default/developer requirements file.

Installing pedalboard for private use does not change the license of this
repository's source. Distributing it together with Audio Studio in one wheel,
application bundle, or installer creates a GPL distribution: that entire
combined distribution must comply with GPL-3.0, including corresponding-source
obligations. The project must not publish a pedalboard-enabled MIT binary.
License pointer: [pedalboard LICENSE](https://github.com/spotify/pedalboard/blob/master/LICENSE).

### VST3 SDK

The VST3 SDK is not included. VST3 SDK 3.8 and later is MIT-licensed, so a
future direct host can remain on the MIT path while preserving the SDK notice.
This does not relax pedalboard's independent GPL obligations.
[VST3 licensing information](https://steinbergmedia.github.io/vst3_dev_portal/pages/FAQ/Licensing.html).

### ASIO SDK

The ASIO SDK and ASIO source code are **not included, linked, or redistributed**.
Audio Studio does not set `SD_ENABLE_ASIO` and does not claim default ASIO
support. A user may independently opt into a compatible sounddevice/PortAudio
ASIO binary by setting that environment variable; that is a user-controlled
configuration outside the default distribution.

ASIO is offered under GPL-3.0 or a separately signed Steinberg proprietary
license. Any future official ASIO distribution requires a fresh legal review;
the proprietary SDK must not be committed or redistributed.
[ASIO licensing information](https://www.steinberg.net/developers/).

## Development and CI-only dependencies

These packages do not ship in the default application wheel.

| Component | Declared/pinned version | License | License pointer |
|---|---|---|---|
| pytest | `>=7.4`; root/CI pin `9.1.1` | MIT | [license](https://github.com/pytest-dev/pytest/blob/main/LICENSE) |
| pytest-qt | `>=4.2`; CI pin `4.5.0` | MIT | [license](https://github.com/pytest-dev/pytest-qt/blob/main/LICENSE) |
| pytest-cov | root pin `7.1.0` | MIT | [license](https://github.com/pytest-dev/pytest-cov/blob/master/LICENSE) |
| mypy | `>=1.8`; root pin `2.3.1` | MIT | [license](https://github.com/python/mypy/blob/master/LICENSE) |
| Ruff | `>=0.3`; root/CI pin `0.16.4` | MIT | [license](https://github.com/astral-sh/ruff/blob/main/LICENSE) |
| build | root pin `1.5.0` | MIT | [license](https://github.com/pypa/build/blob/main/LICENSE) |
| setuptools | build requirement `>=68` | MIT | [license](https://github.com/pypa/setuptools/blob/main/LICENSE) |
| wheel | build requirement, unpinned | MIT | [license](https://github.com/pypa/wheel/blob/main/LICENSE.txt) |
| cffi | CI transitive `2.1.1` | MIT-0 | [license](https://github.com/python-cffi/cffi/blob/main/LICENSE) |
| pycparser | CI transitive `3.0` | BSD-3-Clause | [license](https://github.com/eliben/pycparser/blob/main/LICENSE) |
| iniconfig | CI transitive `2.3.0` | MIT | [license](https://github.com/pytest-dev/iniconfig/blob/main/LICENSE) |
| packaging | CI transitive `26.3` | Apache-2.0 OR BSD-2-Clause | [license](https://github.com/pypa/packaging/blob/main/LICENSE) |
| pluggy | CI transitive `1.6.0` | MIT | [license](https://github.com/pytest-dev/pluggy/blob/main/LICENSE) |
| Pygments | CI transitive `2.21.0` | BSD-2-Clause | [license](https://github.com/pygments/pygments/blob/master/LICENSE) |
| typing-extensions | CI transitive `4.16.0` | PSF-2.0 | [license](https://github.com/python/typing_extensions/blob/main/LICENSE) |

## Manifest reconciliation and release checks

The repository's intentionally different profiles are reconciled as follows:

1. `audio-studio/pyproject.toml` is the authoritative default install. Both
   sounddevice and PyAudio are optional there; `audio-studio/requirements.txt`
   is the full desktop developer profile and therefore includes that extra.
2. Root requirements support probes and benchmarks, not the application wheel;
   their librosa/platformdirs entries are listed above. sounddevice now appears
   in both the root probe pin and the application `[audio]` extra.
3. `.github/requirements.lock` is consistent with `.github/requirements.in`
   and pins PySide6-Essentials, not PyQt6.
4. FFmpeg is an external executable and appears only as an OS package in
   `Dockerfile.dev`; it is not a Python dependency or linked library.
5. PyQt6 and ASIO are absent from every manifest. `pedalboard` appears in
   exactly one place — the `[plugins]` optional extra of
   `audio-studio/pyproject.toml` — and is absent from the default dependency
   set, the developer requirements files, and the CI lock.

Before publishing any binary artifact:

- resolve from the release lock and generate an SBOM for that exact platform;
- verify `PyQt6`, `pedalboard`, and ASIO SDK files are absent from the default
  artifact;
- preserve every installed wheel/native `LICENSE*`, `COPYING*`, and
  `licenses/` file;
- confirm Qt, Shiboken, libsndfile, and any soxr library remain replaceable;
- record FFmpeg configure flags if FFmpeg is bundled at all.

This inventory addresses the five mandatory items in
`.agent_workspace/round2/fable-sota-round2-review.md` §4.4: per-runtime
component metadata and license pointers; LGPL linking/source statements;
pedalboard's optional-GPL rule; the no-ASIO default; and reconciliation with
all dependency manifests and the CI lock.
