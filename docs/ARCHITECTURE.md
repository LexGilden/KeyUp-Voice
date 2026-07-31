# Architecture

KeyUp Voice is a Windows tray application implemented in a single Python entry
point and packaged as an onedir PyInstaller application.

## Main components

```text
Global keyboard/mouse hooks
        │
        ▼
AudioRecorder ──► VoiceOverlay
        │
        ▼
faster-whisper / CTranslate2
        │
        ▼
Windows clipboard + SendInput (Ctrl+V)
```

- `KeyboardHook` installs low-level Windows keyboard hooks.
- `MouseHotkeyHook` supports Mouse 4/5, with optional keyboard modifiers.
- `KeyStatePoller` provides a secondary key-state path for reliable key release.
- `AudioRecorder` captures mono floating-point audio with `sounddevice`.
- `VoiceOverlay` renders the selected animation without taking keyboard focus.
- `VoiceApp` owns the tray menu, model lifecycle, recording state, processing,
  text insertion, and insertion undo.
- `ComponentSetupDialog` and `ComponentInstallWorker` download models and CUDA.

## State flow

```text
loading → ready → recording → transcribing → ready
   └──────────── error handling ──────────────┘
```

The first visual state appears immediately when the hotkey is pressed. The
active voice animation begins only after microphone activity crosses the
configured threshold.

## Models

Each supported model has a pinned repository revision and per-file SHA-256
metadata in `app.py`. Models are stored under:

```text
<install-dir>\models\faster-whisper-<model-id>
```

Models remain separate so switching back does not require another download.
The model manager measures actual disk usage and only permits deletion inside
the dedicated models directory. The model currently selected by the running
application cannot be removed.

## CUDA

On NVIDIA systems, the component installer downloads pinned official Windows
x64 wheels for cuBLAS and cuDNN, verifies them, and extracts required DLL files
to:

```text
<install-dir>\cuda-runtime
```

The directory is added to the process DLL search path before CTranslate2 loads.
AMD and Intel systems use CPU `int8`.

## Configuration and logs

```text
%APPDATA%\KeyUp Voice\config.json
%APPDATA%\KeyUp Voice\keyup-voice.log
```

Legacy `%APPDATA%\Golos` configuration is migrated automatically.

## Packaging

- `build.ps1` creates `dist\KeyUpVoice` with PyInstaller.
- `installer.iss` creates a thin bilingual Inno Setup installer.
- Models and CUDA are never embedded in the installer.
