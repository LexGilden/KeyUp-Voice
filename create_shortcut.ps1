$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$exePath = Join-Path $projectRoot "dist\KeyUpVoice\KeyUpVoice.exe"

if (-not (Test-Path -LiteralPath $exePath)) {
    throw "KeyUpVoice.exe was not found. Run build.ps1 first."
}

$desktopPath = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktopPath "KeyUp Voice.lnk"
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $exePath
$shortcut.WorkingDirectory = Split-Path -Parent $exePath
$shortcut.IconLocation = "$exePath,0"
$shortcut.Description = "Local voice input with Whisper"
$shortcut.Save()

Write-Host "Shortcut created: $shortcutPath"
