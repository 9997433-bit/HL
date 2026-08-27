# Building and shipping the Audio Studio Linux distribution

This is the release engineer's guide to producing a publishable Linux
artifact: how to build it, how to prove the licence obligations are met, and
what must ship next to the binary. The licence rationale behind every rule
here lives in `THIRD_PARTY_LICENSES.md`; this file is the procedure.

## What a release consists of

| Piece | Where it comes from |
|---|---|
| One-directory bundle `dist/audio-studio/` | `scripts/build-linux.sh` (PyInstaller, `packaging/pyinstaller.spec`) |
| Bundle-scoped SBOM (CycloneDX-shaped) | `tools/generate_sbom.py` → `.agent_workspace/v1.1/linux-sbom.json` |
| Build-environment SBOM (SPDX-shaped) | `tools/generate_sbom.py` → `packaging/SBOM.json` |
| Build report with launcher hash and gate results | `tools/generate_sbom.py` → `.agent_workspace/v1.1/linux-build-report.json` |
| Licence notices inside the bundle | `_internal/licenses/THIRD_PARTY_LICENSES.md` and `_internal/licenses/LGPL-RELINKING.txt`, placed by the spec |

The bundle directory itself is never committed to git (`dist/` is ignored);
the SBOMs and the build report are, because they are the reviewable evidence
of what a build contained.

## Building

Build from an environment **without** the `plugins` extra — pedalboard is
GPL-3.0 and its presence would relicense the whole artifact. The build script
refuses to run when pedalboard is importable.

```bash
# from the repository root; uses audio-studio/.venv by default
scripts/build-linux.sh --install-deps --clean
```

The script performs the PyInstaller build and then acts as a distribution
gate. It fails, rather than produce a bundle, when:

- the Qt/PySide6 shared objects are missing from the output (which would mean
  the LGPL libraries are no longer replaceable — e.g. someone switched the
  spec to `--onefile`);
- pedalboard artifacts appear anywhere in the bundle;
- the licence notices are absent from `_internal/licenses/`;
- the offscreen smoke test (`--offscreen --null-audio --exit-after 2`) fails.

Useful variants: `--no-smoke` for headless machines without an offscreen Qt
platform plugin, `--dist-dir PATH` to build elsewhere, `PYTHON_BIN=... ` to
select the interpreter. `ALLOW_GPL=1` exists only for deliberately producing
a GPL-3.0 artifact and must never be used for a published MIT binary.

## Generating and checking the SBOM

```bash
audio-studio/.venv/bin/python tools/generate_sbom.py
audio-studio/.venv/bin/python -m pytest tests/test_sbom.py
```

The generator inventories the build virtualenv (wheel metadata first, the
curated table in the tool as fallback), scans the built bundle for evidence of
what was actually included (package directories, PYZ modules, native shared
objects), and re-runs the distribution checks. Its exit status is non-zero if
any check fails. It still writes `packaging/SBOM.json` when the bundle is
missing or incomplete, so a partially failed build leaves a reviewable
dependency inventory.

`tests/test_sbom.py` validates the schema of all three artifacts and enforces
the licence policy in CI: every component carries a licence, pedalboard is in
no default profile and no bundle, and the Qt binding is recorded as received
under LGPL-3.0.

## Verifying LGPL compliance on the built artifact

The LGPL is satisfied by keeping its libraries replaceable. Concretely, on
the bundle you are about to publish:

1. **Confirm the LGPL shared objects are present and separate.**

   ```bash
   find dist/audio-studio -name 'libQt6Core.so*' -o -name 'libpyside6*' \
        -o -name 'libsndfile*' -o -name 'libsoxr*'
   ```

   Every hit must be a plain `.so` file beside the launcher (under
   `_internal/`), not embedded in the executable. The build script and the
   `qt_libraries_replaceable` check in the build report both assert this.

2. **Confirm nothing rewrote them.** UPX is disabled in the spec; a
   compressed or otherwise transformed shared object is no longer a drop-in
   replacement target. `strip=False` and `upx=False` in
   `packaging/pyinstaller.spec` are licence obligations, not tuning knobs.

3. **Exercise the replacement path once per release.** Swap
   `_internal/libQt6Core.so.6` for the same-major stock distribution build
   (or point `LD_LIBRARY_PATH` at one) and start the launcher. If the
   application does not come up with a replaced library, the distribution
   does not meet the terms described in `LGPL-RELINKING.txt`.

4. **Confirm the notices and the written offer ship.** The bundle must
   contain `_internal/licenses/LGPL-RELINKING.txt` (replacement instructions
   and the three-year written source offer) and
   `_internal/licenses/THIRD_PARTY_LICENSES.md` (full inventory and licence
   pointers). The `license_notices_shipped` check covers this.

5. **Keep matching sources obtainable.** The upstream source locations for
   every LGPL component are listed in `LGPL-RELINKING.txt`. If any of those
   ever becomes unreachable, the distributor named in the release notes is on
   the hook for the written offer — archive the exact source versions of the
   shipped Qt, libsndfile, libsoxr and libquadmath builds with the release.

## Publishing a GitHub release

`.github/workflows/publish-release.yml` is the only workflow triggered by a
`v*` tag. It builds the PyInstaller one-directory bundle independently on
Linux, Windows, and macOS, then waits for all three builds before creating one
GitHub Release for the tag.

To publish, make sure the tag points at the reviewed release commit and push
it to GitHub:

```bash
git tag -a v1.1.0 -m "Audio Studio v1.1.0"
git push origin v1.1.0
```

The workflow runs the Linux distribution gates and generates the bundle-scoped
CycloneDX SBOM from that exact Linux build. Each runner invokes
`scripts/prepare-release-assets.sh` to create a host-native ZIP. The publish job
downloads all build artifacts, invokes the same script to generate the final
checksum manifest, and attaches exactly these files:

- `audio-studio-linux.zip`
- `audio-studio-windows.zip`
- `audio-studio-macos.zip`
- `audio-studio-sbom.json`
- `SHA256SUMS`

The release is not created if any platform build, SBOM gate, expected-asset
check, or checksum step fails. To verify downloaded assets, put all five files
in one directory and run `sha256sum -c SHA256SUMS` (or an equivalent SHA-256
checker on Windows).

## Shipping notices

Publish, together with the binary directory or the archive made from it:

- the bundle's own `_internal/licenses/` directory, unmodified;
- the wheel licence files that PyInstaller collected (`*.dist-info/licenses`
  inside `_internal/`) — do not prune them from the archive;
- the two SBOM files and the build report for that exact build;
- release notes naming the distributor responsible for the written source
  offer in `LGPL-RELINKING.txt`.

## What must never happen

- **No pedalboard in a published artifact.** Three independent layers enforce
  this: the spec excludes it, the build script refuses to run when it is
  importable, and the SBOM generator/tests fail when any trace reaches a
  bundle. Do not weaken any single layer on the grounds that the others exist.
- **No `--onefile` builds.** A self-extracting binary unpacks to a throwaway
  directory each run, so a recipient's replaced LGPL library would be
  overwritten on the next launch.
- **No publishing without the SBOM.** The pre-publication checklist in
  `THIRD_PARTY_LICENSES.md` ("Manifest reconciliation and release checks")
  requires an SBOM generated from the exact release artifact; a rebuilt or
  hand-edited SBOM is not evidence.
