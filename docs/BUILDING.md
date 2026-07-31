# Building KeyUp Voice

## Prerequisites

- Windows 11 x64
- Python 3.11 in `PATH`
- PowerShell
- Inno Setup 6 for installer builds

## Create the environment

```powershell
.\setup.ps1
```

This creates `.venv` and installs `requirements.txt`.

## Run from source

```powershell
.\run.ps1
```

The development build can use an existing model path from
`config.example.json` or download components through the application.

## Run checks

```powershell
.\.venv\Scripts\python.exe -m py_compile app.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Build the application

Close every running KeyUp Voice process, then run:

```powershell
.\build.ps1
```

Output:

```text
dist\KeyUpVoice\KeyUpVoice.exe
```

## Build the installer

```powershell
.\build-installer.ps1 -BuildApp
```

Output:

```text
installer-output\KeyUp-Voice-Setup-<version>.exe
```

The version is defined in both `app.py` and `installer.iss`. Tests verify that
the two values stay synchronized.

## Release checklist

1. Update `APP_VERSION` and `MyAppVersion`.
2. Update `CHANGELOG.md`.
3. Run tests.
4. Build and install the release candidate.
5. Verify Russian and English installer modes.
6. Verify CPU fallback and NVIDIA CUDA loading where available.
7. Verify dictation, translation, model switching, settings, startup, and
   uninstall.
8. Create a Git tag such as `v1.4.1`.
9. Attach the installer produced by the GitHub build workflow to a Release.
