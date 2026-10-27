$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonExe = Join-Path $projectRoot ".venv\Scripts\python.exe"
$iconPath = Join-Path $projectRoot "keyup-voice.ico"

if (-not (Test-Path -LiteralPath $pythonExe)) {
    throw "Virtual environment was not found. Run setup.ps1 first."
}

& $pythonExe -m pip install "pyinstaller>=6.9,<7"
if ($LASTEXITCODE -ne 0) { throw "Could not prepare PyInstaller." }
& $pythonExe (Join-Path $projectRoot "make_icon.py")
if ($LASTEXITCODE -ne 0) { throw "Could not create application icon." }
$originalBuildPath = $env:PATH
try {
    # Do not bundle unrelated DLLs from tools added to the caller's PATH.
    $env:PATH = @(
        (Split-Path -Parent $pythonExe),
        (Join-Path $env:SystemRoot "System32"),
        $env:SystemRoot
    ) -join ";"
& $pythonExe -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --onedir `
    --name KeyUpVoice `
    --icon $iconPath `
    --collect-data faster_whisper `
    --exclude-module torch `
    --exclude-module transformers `
    --hidden-import av `
    --hidden-import sounddevice `
    (Join-Path $projectRoot "app.py")
if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed." }

$testExe = Join-Path $projectRoot "dist\KeyUpVoice\KeyUpVoice.exe"
$smokeTest = Start-Process -FilePath $testExe -ArgumentList "--self-test" -WindowStyle Hidden -PassThru
if (-not $smokeTest.WaitForExit(30000)) {
    Stop-Process -Id $smokeTest.Id -ErrorAction SilentlyContinue
    throw "Packaged application startup check timed out."
}
$smokeTest.WaitForExit()
if ($smokeTest.ExitCode -ne 0) { throw "Packaged application startup check failed: $($smokeTest.ExitCode)" }
} finally {
    $env:PATH = $originalBuildPath
}

Write-Host ""
Write-Host "Build complete:"
Write-Host "  $(Join-Path $projectRoot 'dist\KeyUpVoice\KeyUpVoice.exe')"
