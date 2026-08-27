# Authenticode-sign Windows release artifacts when a certificate is configured,
# and say plainly that nothing was signed when one is not.
#
# This repository has no Authenticode certificate. On a machine that has one —
# a Windows host with the Windows SDK's signtool.exe and either a PFX file or a
# certificate in the local store — this script signs with SHA-256, countersigns
# through an RFC 3161 timestamp server, and then verifies the result with
# signtool itself before calling anything signed. Anywhere else it refuses to
# improvise: it will not invent a signature because a variable was set, and the
# JSON report it always writes records signed=false with the reason.
#
# Setting WINDOWS_SIGNING_CERT does not sign anything by itself; signtool
# running to completion and signtool verify accepting the result does. Only
# that path reports signed=true. An unsigned Windows build raises a SmartScreen
# warning on a user's machine, and that is the honest state of this project's
# Windows artifacts today.
#
# Usage:
#   .\scripts\sign-windows-artifact.ps1 dist\audio-studio\audio-studio.exe
#   $env:WINDOWS_SIGNING_CERT = "C:\keys\release.pfx"
#   .\scripts\sign-windows-artifact.ps1 -RequireSignature dist\*.exe
[CmdletBinding()]
param(
    # Certificate to sign with: a .pfx path, or a 40-character SHA-1 thumbprint
    # of a certificate in the current user's or machine's store.
    [string]$Certificate,
    [string]$CertificatePassword,
    [string]$TimestampUrl,
    [string]$Report,
    [string]$ManifestDir,
    [string]$ManifestName = "SHA256SUMS",
    [switch]$RequireSignature,
    # Position 0 keeps the artifact list positional and, because every other
    # parameter then becomes name-only, stops a bare path from binding to
    # -Certificate.
    [Parameter(Position = 0, ValueFromRemainingArguments = $true)]
    [string[]]$Artifact
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$SchemaVersion = 1
$ToolName = "scripts/sign-windows-artifact.ps1"
$RootDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

function Write-Step {
    param([Parameter(Mandatory)][string]$Message)
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Stop-Signing {
    param([Parameter(Mandatory)][string]$Message)
    throw "Windows signing failed: $Message"
}

function Stop-Usage {
    param([Parameter(Mandatory)][string]$Message)
    [Console]::Error.WriteLine("error: $Message")
    exit 2
}

# PowerShell's current location and the .NET process directory can differ, so
# paths are resolved through the session state rather than [System.IO.Path].
function Resolve-FullPath {
    param([Parameter(Mandatory)][string]$Path)
    return $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($Path)
}

function Get-RelativePath {
    param([Parameter(Mandatory)][string]$Path)
    $full = Resolve-FullPath $Path
    if ($full.StartsWith($RootDir, [System.StringComparison]::OrdinalIgnoreCase)) {
        return $full.Substring($RootDir.Length).TrimStart('\', '/').Replace('\', '/')
    }
    return $full.Replace('\', '/')
}

function Test-IsWindows {
    # $IsWindows exists in PowerShell 6+; Windows PowerShell 5.1 is Windows only.
    if (Test-Path variable:global:IsWindows) {
        return [bool]$IsWindows
    }
    return $true
}

# Lower case to match sha256sum and the reports the other platforms write.
function Get-Sha256 {
    param([Parameter(Mandatory)][string]$Path)
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Get-HostSystem {
    if (Test-IsWindows) { return "Windows" }
    if (Test-Path variable:global:IsMacOS) {
        if ($IsMacOS) { return "Darwin" }
    }
    if (Test-Path variable:global:IsLinux) {
        if ($IsLinux) { return "Linux" }
    }
    return "Unknown"
}

function Find-SignTool {
    $command = Get-Command signtool.exe -ErrorAction SilentlyContinue
    if ($null -ne $command) {
        return $command.Source
    }
    $roots = @(${env:ProgramFiles(x86)}, $env:ProgramFiles) |
        Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
    foreach ($root in $roots) {
        $kit = Join-Path $root "Windows Kits\10\bin"
        if (-not (Test-Path -LiteralPath $kit -PathType Container)) { continue }
        $found = Get-ChildItem -LiteralPath $kit -Recurse -Filter signtool.exe `
            -ErrorAction SilentlyContinue |
            Where-Object { $_.FullName -match '\\x64\\' } |
            Sort-Object FullName -Descending |
            Select-Object -First 1
        if ($null -ne $found) {
            return $found.FullName
        }
    }
    return $null
}

$HostSystem = Get-HostSystem

if ([string]::IsNullOrWhiteSpace($Certificate)) {
    $Certificate = $env:WINDOWS_SIGNING_CERT
}
if ([string]::IsNullOrWhiteSpace($CertificatePassword)) {
    $CertificatePassword = $env:WINDOWS_SIGNING_CERT_PASSWORD
}
if ([string]::IsNullOrWhiteSpace($TimestampUrl)) {
    $TimestampUrl = $env:WINDOWS_SIGNING_TIMESTAMP_URL
}
if ([string]::IsNullOrWhiteSpace($TimestampUrl)) {
    $TimestampUrl = "http://timestamp.digicert.com"
}
if ([string]::IsNullOrWhiteSpace($Report)) {
    $Report = $env:WINDOWS_SIGNING_REPORT
}
if ([string]::IsNullOrWhiteSpace($Report)) {
    $Report = Join-Path $RootDir ".agent_workspace/v1.2/windows-signing-report.json"
}

if ($null -eq $Artifact -or $Artifact.Count -eq 0) {
    Stop-Usage "no artifacts given; pass one or more files to sign"
}
foreach ($candidate in $Artifact) {
    if ($candidate.StartsWith("-")) {
        Stop-Usage "unknown option: $candidate"
    }
}

$Artifacts = @()
foreach ($candidate in $Artifact) {
    if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) {
        Stop-Signing "no such artifact: $candidate (a directory cannot be Authenticode-signed)"
    }
    $Artifacts += (Resolve-Path -LiteralPath $candidate).Path
}

Write-Step "artifacts: $($Artifacts.Count)"

# The manifest lists bare file names so `sha256sum --check SHA256SUMS` and
# PowerShell's Get-FileHash agree from the directory a user downloaded into.
if ([string]::IsNullOrWhiteSpace($ManifestDir)) {
    $ManifestDir = Split-Path -Parent $Artifacts[0]
}
if (-not (Test-Path -LiteralPath $ManifestDir -PathType Container)) {
    New-Item -ItemType Directory -Path $ManifestDir -Force | Out-Null
}
$ManifestPath = Join-Path $ManifestDir $ManifestName

$CertificateSource = $null
if (-not [string]::IsNullOrWhiteSpace($Certificate)) {
    if ($Certificate -match '^[0-9a-fA-F]{40}$') {
        $CertificateSource = "store-thumbprint"
    } elseif (Test-Path -LiteralPath $Certificate -PathType Leaf) {
        $CertificateSource = "pfx-file"
    } else {
        Stop-Signing (
            "WINDOWS_SIGNING_CERT is neither a readable .pfx path nor a " +
            "40-character certificate thumbprint: $Certificate"
        )
    }
}

$Signed = $false
$Reason = ""
$SignToolPath = $null
$Subject = $null

if ([string]::IsNullOrWhiteSpace($Certificate)) {
    $Reason = (
        "no WINDOWS_SIGNING_CERT configured: artifacts are checksummed but " +
        "unsigned, and SmartScreen will warn a downloader about them"
    )
    if ($RequireSignature) {
        Stop-Signing "$Reason (-RequireSignature was given)"
    }
    Write-Warning $Reason
} elseif (-not (Test-IsWindows)) {
    Stop-Signing (
        "a signing certificate is configured but this host is not Windows; " +
        "signtool.exe exists only there. Refusing to report a signature that " +
        "was never made."
    )
} else {
    $SignToolPath = Find-SignTool
    if ($null -eq $SignToolPath) {
        Stop-Signing (
            "a signing certificate is configured but signtool.exe was not " +
            "found; install the Windows SDK signing tools."
        )
    }

    $signArguments = @("sign", "/fd", "SHA256", "/td", "SHA256", "/tr", $TimestampUrl, "/v")
    if ($CertificateSource -eq "pfx-file") {
        $signArguments += @("/f", $Certificate)
        if (-not [string]::IsNullOrWhiteSpace($CertificatePassword)) {
            $signArguments += @("/p", $CertificatePassword)
        }
    } else {
        $signArguments += @("/sha1", $Certificate)
    }

    Write-Step "signing with signtool ($CertificateSource)"
    foreach ($path in $Artifacts) {
        & $SignToolPath @signArguments $path
        if ($LASTEXITCODE -ne 0) {
            Stop-Signing "signtool sign failed for $path (exit code $LASTEXITCODE)"
        }
        # A signature this script cannot verify is not one it will report.
        & $SignToolPath verify /pa /v $path
        if ($LASTEXITCODE -ne 0) {
            Stop-Signing "signtool verify rejected $path (exit code $LASTEXITCODE)"
        }
    }

    $signature = Get-AuthenticodeSignature -LiteralPath $Artifacts[0]
    if ($signature.Status -ne "Valid") {
        Stop-Signing "Get-AuthenticodeSignature reports $($signature.Status) for $($Artifacts[0])"
    }
    $Subject = $signature.SignerCertificate.Subject
    $Signed = $true
    $Reason = (
        "signtool sign /fd SHA256 with an RFC 3161 timestamp, accepted by " +
        "signtool verify /pa for every artifact"
    )
}

$manifestLines = @()
foreach ($path in $Artifacts) {
    $hash = Get-Sha256 $path
    $manifestLines += "$hash  $(Split-Path -Leaf $path)"
}
Set-Content -LiteralPath $ManifestPath -Value $manifestLines -Encoding ascii
Write-Step "manifest:  $ManifestPath"

$artifactRecords = @()
foreach ($path in $Artifacts) {
    $item = Get-Item -LiteralPath $path
    $artifactRecords += [ordered]@{
        path               = Get-RelativePath $path
        kind               = "file"
        size_bytes         = $item.Length
        sha256             = Get-Sha256 $path
        digest_scope       = "file"
        signature          = $(if ($Signed) { "embedded-authenticode" } else { $null })
        signature_verified = $Signed
    }
}

$manifestItem = Get-Item -LiteralPath $ManifestPath
$manifestRecord = [ordered]@{
    path               = Get-RelativePath $ManifestPath
    kind               = "file"
    size_bytes         = $manifestItem.Length
    sha256             = Get-Sha256 $ManifestPath
    digest_scope       = "file"
    # The manifest is a text file beside the artifacts, never a signed PE.
    signature          = $null
    signature_verified = $false
}

$reportDocument = [ordered]@{
    schema_version  = $SchemaVersion
    tool            = $ToolName
    target_platform = "windows"
    generated_at    = (Get-Date).ToUniversalTime().ToString("yyyy-MM-dd'T'HH:mm:ssK")
    # The host this ran on, which is not necessarily Windows: the unsigned path
    # runs anywhere, and a report that named the target platform here would
    # read like a Windows machine had been involved.
    platform        = [ordered]@{
        system  = $HostSystem
        machine = [System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture.ToString()
        release = [System.Environment]::OSVersion.Version.ToString()
    }
    signing         = [ordered]@{
        method                 = "authenticode-signtool"
        certificate_requested  = -not [string]::IsNullOrWhiteSpace($Certificate)
        certificate_source     = $CertificateSource
        certificate            = $(
            if ($CertificateSource -eq "pfx-file") { Get-RelativePath $Certificate }
            elseif ([string]::IsNullOrWhiteSpace($Certificate)) { $null }
            else { $Certificate }
        )
        subject                = $Subject
        digest_algorithm       = "SHA256"
        timestamp_url          = $TimestampUrl
        timestamped            = $Signed
        signtool_path          = $SignToolPath
        host_is_windows        = (Test-IsWindows)
    }
    signed          = $Signed
    reason          = $Reason
    manifest        = $manifestRecord
    artifacts       = $artifactRecords
    artifact_count  = $artifactRecords.Count
    # Spelled out so no downstream summary can widen this into a platform
    # nobody signed for.
    scope           = [ordered]@{
        linux_gpg_detached_signature = $false
        macos_codesign               = $false
        macos_notarization           = $false
        windows_authenticode         = $Signed
        note                         = (
            "Windows Authenticode only. This repository has no code-signing " +
            "certificate, so a run without WINDOWS_SIGNING_CERT checksums the " +
            "artifacts and signs nothing; Linux GPG signing is " +
            "scripts/sign-linux-artifact.sh and macOS codesigning is " +
            "scripts/sign-macos-artifact.sh."
        )
    }
}

$reportPath = Resolve-FullPath $Report
$reportDirectory = Split-Path -Parent $reportPath
if (-not [string]::IsNullOrWhiteSpace($reportDirectory) -and
    -not (Test-Path -LiteralPath $reportDirectory -PathType Container)) {
    New-Item -ItemType Directory -Path $reportDirectory -Force | Out-Null
}
# WriteAllText leaves no byte-order mark, which Windows PowerShell's -Encoding
# utf8 would add and every JSON reader would then trip over.
[System.IO.File]::WriteAllText(
    $reportPath, ($reportDocument | ConvertTo-Json -Depth 8) + "`n")
Write-Step "report: $reportPath"

if ($Signed) {
    Write-Step "signed: $Reason"
} else {
    Write-Step "not signed: $Reason"
}
