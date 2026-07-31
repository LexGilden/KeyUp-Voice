param(
    [switch]$BuildApp
)

$ErrorActionPreference = "Stop"

$isccCandidates = @(
    "${env:LOCALAPPDATA}\Programs\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles}\Inno Setup 6\ISCC.exe"
)

$iscc = $isccCandidates |
    Where-Object { Test-Path -LiteralPath $_ } |
    Select-Object -First 1

if (-not $iscc) {
    throw "Inno Setup 6 was not found. Install JRSoftware.InnoSetup with winget."
}

if ($BuildApp) {
    if (
        (Get-Process -Name "KeyUpVoice" -ErrorAction SilentlyContinue) -or
        (Get-Process -Name "Golos" -ErrorAction SilentlyContinue)
    ) {
        throw "Close KeyUp Voice before rebuilding the application."
    }
    & (Join-Path $PSScriptRoot "build.ps1")
    if ($LASTEXITCODE -ne 0) {
        throw "KeyUp Voice build failed."
    }
}

$appExe = Join-Path $PSScriptRoot "dist\KeyUpVoice\KeyUpVoice.exe"
if (-not (Test-Path -LiteralPath $appExe -PathType Leaf)) {
    throw "Application build was not found. Run .\build.ps1 first."
}

& $iscc "$PSScriptRoot\installer.iss"
if ($LASTEXITCODE -ne 0) {
    throw "KeyUp Voice installer build failed."
}

$versionLine = Select-String `
    -LiteralPath (Join-Path $PSScriptRoot "installer.iss") `
    -Pattern '^\s*#define\s+MyAppVersion\s+"([^"]+)"\s*$' |
    Select-Object -First 1

if (-not $versionLine) {
    throw "MyAppVersion was not found in installer.iss."
}

$appVersion = $versionLine.Matches[0].Groups[1].Value
$installer = Join-Path $PSScriptRoot "installer-output\KeyUp-Voice-Setup-$appVersion.exe"
Write-Host ""
Write-Host "Thin installer complete:"
Write-Host "  $installer"
