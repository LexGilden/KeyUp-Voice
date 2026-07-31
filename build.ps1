$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonExe = Join-Path $projectRoot ".venv\Scripts\python.exe"
$iconPath = Join-Path $projectRoot "keyup-voice.ico"

if (-not (Test-Path -LiteralPath $pythonExe)) {
    throw "Virtual environment was not found. Run setup.ps1 first."
}

& $pythonExe -m pip install "pyinstaller>=6.9,<7"
& $pythonExe (Join-Path $projectRoot "make_icon.py")
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

Write-Host ""
Write-Host "Build complete:"
Write-Host "  $(Join-Path $projectRoot 'dist\KeyUpVoice\KeyUpVoice.exe')"
