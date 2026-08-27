# Build the Audio Studio desktop bundle for Windows and enforce its release gates.
#
# The PyInstaller spec deliberately produces a one-directory distribution so
# recipients can replace the LGPL DLLs. See packaging/pyinstaller.spec and
# packaging/LGPL-RELINKING.txt.
[CmdletBinding()]
param(
    [switch]$Clean,
    [switch]$InstallDeps,
    [string]$DistDir,
    [string]$WorkDir
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RootDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$AppDir = Join-Path $RootDir "audio-studio"
$SpecFile = Join-Path $RootDir "packaging\pyinstaller.spec"
$Name = "audio-studio"

if ([string]::IsNullOrWhiteSpace($DistDir)) {
    $DistDir = Join-Path $RootDir "dist"
} elseif (-not [System.IO.Path]::IsPathRooted($DistDir)) {
    $DistDir = Join-Path $RootDir $DistDir
}

if ([string]::IsNullOrWhiteSpace($WorkDir)) {
    $WorkDir = Join-Path $RootDir "build\pyinstaller"
} elseif (-not [System.IO.Path]::IsPathRooted($WorkDir)) {
    $WorkDir = Join-Path $RootDir $WorkDir
}

function Write-Step {
    param([Parameter(Mandatory)][string]$Message)
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Stop-Build {
    param([Parameter(Mandatory)][string]$Message)
    throw "Audio Studio Windows build failed: $Message"
}

function Assert-LastExitCode {
    param([Parameter(Mandatory)][string]$Operation)
    if ($LASTEXITCODE -ne 0) {
        Stop-Build "$Operation (exit code $LASTEXITCODE)"
    }
}

$PythonBin = $env:PYTHON_BIN
if ([string]::IsNullOrWhiteSpace($PythonBin)) {
    $VenvPython = Join-Path $AppDir ".venv\Scripts\python.exe"
    if (Test-Path -LiteralPath $VenvPython -PathType Leaf) {
        $PythonBin = $VenvPython
    } else {
        $PythonCommand = Get-Command python -ErrorAction SilentlyContinue
        if ($null -eq $PythonCommand) {
            Stop-Build "no Python interpreter found; set PYTHON_BIN"
        }
        $PythonBin = $PythonCommand.Source
    }
}

if (-not (Test-Path -LiteralPath $SpecFile -PathType Leaf)) {
    Stop-Build "missing spec file: $SpecFile"
}

$PythonVersion = & $PythonBin --version 2>&1
Assert-LastExitCode "could not run $PythonBin"
Write-Step "interpreter: $PythonBin ($PythonVersion)"

if ($InstallDeps) {
    Write-Step "installing build dependencies"
    & $PythonBin -m pip install --upgrade "pyinstaller>=6.3"
    Assert-LastExitCode "installing PyInstaller failed"
}

$PyInstallerVersion = & $PythonBin -m PyInstaller --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Stop-Build "PyInstaller is not installed in $PythonBin; re-run with -InstallDeps"
}
Write-Step "PyInstaller $PyInstallerVersion"

# Refuse a build environment containing pedalboard. It is GPL-3.0 and must
# never be pulled into an artifact distributed as MIT.
& $PythonBin -c "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('pedalboard') else 1)"
$PedalboardProbe = $LASTEXITCODE
if ($PedalboardProbe -eq 0) {
    Stop-Build (
        "pedalboard (GPL-3.0) is installed in this interpreter. " +
        "Build from an environment without the 'plugins' extra."
    )
}
if ($PedalboardProbe -ne 1) {
    Stop-Build "could not determine whether pedalboard is installed"
}

$Bundle = Join-Path $DistDir $Name
if ($Clean) {
    Write-Step "cleaning $Bundle and $WorkDir"
    Remove-Item -LiteralPath $Bundle -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $WorkDir -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Step "building $Name as a one-directory bundle"
$PreviousPythonPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = if ([string]::IsNullOrWhiteSpace($PreviousPythonPath)) {
        $AppDir
    } else {
        "$AppDir;$PreviousPythonPath"
    }
    Push-Location $RootDir
    try {
        & $PythonBin -m PyInstaller `
            --noconfirm `
            --distpath $DistDir `
            --workpath $WorkDir `
            $SpecFile
        Assert-LastExitCode "PyInstaller build failed"
    } finally {
        Pop-Location
    }
} finally {
    $env:PYTHONPATH = $PreviousPythonPath
}

$Launcher = Join-Path $Bundle "$Name.exe"
if (-not (Test-Path -LiteralPath $Bundle -PathType Container)) {
    Stop-Build "the build did not produce the one-directory bundle $Bundle"
}
if (-not (Test-Path -LiteralPath $Launcher -PathType Leaf)) {
    Stop-Build "the build produced no launcher at $Launcher"
}

# Separate Qt DLLs prove this is not a one-file executable and preserve the
# recipient's ability to replace the LGPL libraries.
Write-Step "checking that the LGPL libraries stayed replaceable"
$QtLibraries = @(
    Get-ChildItem -LiteralPath $Bundle -Recurse -File |
        Where-Object { $_.Name -ieq "Qt6Core.dll" }
)
if ($QtLibraries.Count -eq 0) {
    Stop-Build "no Qt6Core.dll in the bundle; the LGPL library is not replaceable"
}
$QtLibraries | ForEach-Object {
    Write-Host "    $($_.FullName.Substring($Bundle.Length + 1))"
}

$PedalboardArtifacts = @(
    Get-ChildItem -LiteralPath $Bundle -Recurse |
        Where-Object { $_.Name -match "(?i)pedalboard" }
)
if ($PedalboardArtifacts.Count -ne 0) {
    Stop-Build "pedalboard artifacts found in the bundle; refusing to call this an MIT build"
}

foreach ($Notice in @("THIRD_PARTY_LICENSES.md", "LGPL-RELINKING.txt")) {
    $InternalNotice = Join-Path $Bundle "_internal\licenses\$Notice"
    $RootNotice = Join-Path $Bundle "licenses\$Notice"
    if (
        -not (Test-Path -LiteralPath $InternalNotice -PathType Leaf) -and
        -not (Test-Path -LiteralPath $RootNotice -PathType Leaf)
    ) {
        Stop-Build "the bundle is missing licenses\$Notice"
    }
}

Write-Step "smoke-testing the bundle with --version"
& $Launcher --version
Assert-LastExitCode "the built launcher failed its --version smoke test"

Write-Step "bundle ready: $Bundle"
Write-Step "ship the complete directory, including its licenses folder"
