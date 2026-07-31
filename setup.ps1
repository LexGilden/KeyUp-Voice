$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $venvPython)) {
    $pythonLauncher = Get-Command "py" -ErrorAction SilentlyContinue
    if ($pythonLauncher) {
        & $pythonLauncher.Source -3.11 -c "import sys" 2>$null
        if ($LASTEXITCODE -eq 0) {
            & $pythonLauncher.Source -3.11 -m venv (Join-Path $projectRoot ".venv")
        }
    }

    if (-not (Test-Path -LiteralPath $venvPython)) {
        $systemPython = Get-Command "python" -ErrorAction SilentlyContinue
        if (-not $systemPython) {
            throw "Python 3.11 was not found. Install it or make it available through the Python launcher."
        }
        $version = & $systemPython.Source -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
        if ($version -ne "3.11") {
            throw "Python 3.11 is required; found Python $version."
        }
        & $systemPython.Source -m venv (Join-Path $projectRoot ".venv")
    }
}

& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r (Join-Path $projectRoot "requirements.txt")

Write-Host ""
Write-Host "Setup complete. Start the app with:"
Write-Host "  .\run.ps1"
