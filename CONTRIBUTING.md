# Contributing

Thank you for helping improve KeyUp Voice.

## Development environment

KeyUp Voice currently targets Windows 11 x64 and Python 3.11.

```powershell
git clone <repository-url>
cd KeyUp-Voice
.\setup.ps1
.\run.ps1
```

The setup script creates a local `.venv` and installs the runtime dependencies.

## Before opening a pull request

1. Keep changes focused on one problem or feature.
2. Preserve both Russian and English interface strings.
3. Do not commit models, CUDA files, logs, local configuration, virtual
   environments, installers, or other generated artifacts.
4. Run the checks:

   ```powershell
   .\.venv\Scripts\python.exe -m py_compile app.py
   .\.venv\Scripts\python.exe -m unittest discover -s tests -v
   ```

5. Test tray actions, both hotkeys, dictation, translation, settings, and
   model loading when the change affects those areas.
6. Update `CHANGELOG.md` and documentation for user-visible changes.

## Code guidelines

- Prefer clear, typed Python and small focused functions.
- Keep Windows API calls narrowly scoped and document non-obvious behavior.
- Use the existing `tr(russian, english)` helper for user-facing text.
- Pin downloadable model revisions and verify every file with SHA-256.
- Never add telemetry or upload audio without explicit design discussion and
  clear user consent.

## Issues

Use the supplied bug and feature templates. Include the application version,
Windows version, selected model, CPU/GPU mode, and relevant log excerpts.
Remove personal or sensitive information from logs before posting.
