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

`.github/workflows/publish-release.yml` runs on `v*` tags. Its
`windows-latest` job builds and verifies the bundle with this same script,
zips it as `audio-studio-windows.zip`, and attaches it to the GitHub Release
alongside the other platforms' assets and the `SHA256SUMS` manifest.

## Authenticode status

The repository has no Authenticode signing certificate configured, and the
workflow therefore produces an **unsigned** executable.

`scripts/sign-windows-artifact.ps1` is the signing step, and it is a scaffold
rather than a signature. Given `WINDOWS_SIGNING_CERT` — a `.pfx` path, or the
thumbprint of a certificate in the store, with `WINDOWS_SIGNING_CERT_PASSWORD`
for the former — it runs `signtool sign /fd SHA256` with an RFC 3161
countersignature and only reports success after `signtool verify /pa` and
`Get-AuthenticodeSignature` accept the file:

```powershell
$env:WINDOWS_SIGNING_CERT = "C:\keys\release.pfx"
.\scripts\sign-windows-artifact.ps1 -RequireSignature dist\audio-studio\audio-studio.exe
```

Without a certificate the script still succeeds: it writes `SHA256SUMS` and a
report at `.agent_workspace\v1.2\windows-signing-report.json` recording
`signed: false` and why. `-RequireSignature` turns that state into a failure
for a release job that must not ship unsigned, and
`scripts\release-signing-manifest.sh` folds the report into the release-wide
manifest.

Setting a variable still does not sign anything. A release is signed only when
an operator holds a real code-signing certificate — on an HSM or hardware token,
as the CA/Browser Forum baseline requires — runs the script on Windows with it,
and gets `signed: true` in the report.
