# Building the Windows distribution

Audio Studio ships on Windows as a PyInstaller one-directory bundle. Keeping
the DLLs as separate files is required so recipients can replace the LGPL
components as described in `packaging/LGPL-RELINKING.txt`; do not convert the
bundle to a `--onefile` executable.

## Local build

Use 64-bit Python 3.12 in an environment that does **not** include the
`plugins` extra. From a PowerShell prompt at the repository root:

```powershell
py -3.12 -m venv audio-studio\.venv
& .\audio-studio\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install "./audio-studio[installer]"
.\scripts\build-windows.ps1 -Clean
```

Use `-InstallDeps` to have the script install or update PyInstaller. Set
`PYTHON_BIN` to select a different interpreter, or pass `-DistDir` and
`-WorkDir` to relocate the generated files.

The result is `dist\audio-studio\audio-studio.exe` together with its
`_internal` directory. The script fails the build unless:

- PyInstaller produced a one-directory bundle with a separate `Qt6Core.dll`;
- pedalboard is absent from both the build environment and output;
- `THIRD_PARTY_LICENSES.md` and `LGPL-RELINKING.txt` are inside the bundle;
- `audio-studio.exe --version` exits successfully.

Distribute the complete `dist\audio-studio\` directory. Do not copy out the
executable by itself or remove wheel licence files from `_internal`.

## CI artifact

`.github/workflows/release-windows.yml` runs on `v*` tags and by manual
dispatch. It uploads the verified directory as
`audio-studio-windows-x64`.

## Authenticode status

The repository has no Authenticode signing certificate configured, and the
workflow therefore produces an **unsigned** executable. A release is signed
only when a release operator securely configures a Windows code-signing
certificate (for example as a `SIGNING_CERTIFICATE` secret), adds an explicit
`signtool` signing and verification step, and verifies the resulting
signature. Merely setting a variable does not sign the artifact; the current
script and workflow perform no Authenticode operation.
