# KeyUp Voice

[Русская версия](README.ru.md)

## [⬇ Download KeyUp Voice for Windows](https://github.com/LexGilden/KeyUp-Voice/releases/latest)

Latest stable installer for Windows 11 x64.

![Windows 11](https://img.shields.io/badge/Windows-11-0078D4?logo=windows11&logoColor=white)
![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)

KeyUp Voice is a local push-to-talk voice typing application for Windows 11.
Hold a configurable key, speak, and release it to insert recognized text into
the currently focused text field.

Recognition runs locally with
[faster-whisper](https://github.com/SYSTRAN/faster-whisper). A second hotkey
can translate speech directly to English using Whisper's built-in translation
mode.

## Features

- Voice typing in any application that accepts pasted text.
- Separate configurable hotkeys for dictation and translation to English.
- Modern animated microphone indicator with seven visual styles.
- Five multilingual Whisper models selectable at first launch or later.
- Automatic NVIDIA GPU detection and optional CUDA acceleration.
- CPU fallback for AMD, Intel, and systems without supported NVIDIA CUDA.
- Russian and English application and installer interfaces.
- Optional Windows startup entry.
- Resumable component downloads with size and SHA-256 verification.
- No saved voice recordings: audio is processed in memory and discarded.

## Download and installation

1. Open the repository's **[Releases](https://github.com/LexGilden/KeyUp-Voice/releases/latest)** page.
2. Download `KeyUp-Voice-Setup-<version>.exe`.
3. Choose Russian or English in the installer.
4. Start KeyUp Voice and select a Whisper model.
5. If required, allow the application to download the model and NVIDIA CUDA
   runtime files.

The installer is intentionally small and does not embed Whisper or CUDA.
Recognition works offline after the required components have been downloaded.

## Usage

1. Place the cursor in a text field.
2. Hold the dictation hotkey and speak.
3. Release the key.
4. KeyUp Voice recognizes the speech and pastes the result.

Default hotkeys:

| Action | Default |
| --- | --- |
| Dictation | Right Alt |
| Translate speech to English | Right Ctrl |

Both keys can be changed in **Settings** from the system tray menu.

## Whisper models

| Model | Approximate download | Intended use |
| --- | ---: | --- |
| Tiny | 75 MB | Minimum size and fastest CPU processing |
| Base | 141 MB | Lightweight everyday use |
| Small | 464 MB | Better accuracy with moderate resource use |
| Medium | 1.4 GB | Recommended quality/speed balance |
| Large-v3 | 2.9 GB | Highest available accuracy |

Installed models are kept separately. Switching to an installed model does not
download it again. Missing models are downloaded after the selection is saved.

Model files come from the official
[Systran faster-whisper collection](https://huggingface.co/collections/Systran/faster-whisper)
and are pinned to specific revisions.

## GPU and CPU processing

- **NVIDIA:** KeyUp Voice can download the required CUDA 12 libraries and use
  `float16` inference.
- **AMD / Intel / no compatible GPU:** processing falls back to CPU with
  `int8` compute.

CUDA libraries are downloaded from the official NVIDIA packages on PyPI.

## Privacy

- Recognition and translation run locally.
- Recorded audio is held in memory only for the current request.
- Audio is discarded after processing and is not written to disk.
- Network access is used only to download selected models and optional CUDA
  components.
- Recognized text is placed on the clipboard temporarily; the previous
  clipboard contents are restored after insertion.

See [docs/PRIVACY.md](docs/PRIVACY.md) for details.

## Build from source

Requirements:

- Windows 11 x64
- Python 3.11 available in `PATH`
- PowerShell
- Inno Setup 6 to build the installer

```powershell
.\setup.ps1
.\run.ps1
```

Build the desktop application:

```powershell
.\build.ps1
```

Build the thin installer:

```powershell
.\build-installer.ps1 -BuildApp
```

The result is written to `installer-output`. Build directories, downloaded
models, CUDA files, local configuration, and installer binaries are excluded
from Git.

More details are available in [docs/BUILDING.md](docs/BUILDING.md) and
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Data locations

| Data | Location |
| --- | --- |
| Settings and logs | `%APPDATA%\KeyUp Voice` |
| Application and downloaded components | `%LOCALAPPDATA%\Programs\KeyUp Voice` |

Upgraded installations may retain the legacy `Programs\Golos` directory while
displaying the current KeyUp Voice name everywhere in the user interface.

## Known limitations

- A selected hotkey is reserved while KeyUp Voice is running.
- Pasting into an elevated application may fail when KeyUp Voice is running
  without administrator privileges.
- Whisper's built-in translation mode translates speech only to English.
- Large models require more memory and take longer to load.

## Contributing and security

See [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request.
Please report security issues according to [SECURITY.md](SECURITY.md).

## License

KeyUp Voice is released under the [MIT License](LICENSE).
Third-party projects and model licenses are listed in
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

Copyright © 2026 LexGilden.
