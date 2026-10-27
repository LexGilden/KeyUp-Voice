# Privacy

KeyUp Voice is designed for local speech recognition.

## Audio

- Microphone audio is captured only while the configured hotkey is held.
- Audio samples are kept in process memory for the active request.
- Audio is passed to the locally loaded Whisper model.
- Audio is discarded after recognition and is not written to an audio file.

## Recognized text and clipboard

The recognized text is placed on the Windows clipboard so it can be inserted
with `Ctrl+V`. KeyUp Voice clones the previous clipboard contents and restores
them after a short delay.

## Network access

The application uses the network for the following purposes:

- Whisper model files are downloaded from Hugging Face.
- NVIDIA cuBLAS and cuDNN packages are downloaded from PyPI on supported
  NVIDIA systems.
- Custom model metadata and compatibility are checked on Hugging Face.
- GitHub's public Releases API is checked for new stable versions. Automatic
  checks can be disabled in Settings; manual checks remain available.

Update requests do not include recordings, recognized text, settings, or machine
identifiers. GitHub and Hugging Face receive normal network metadata, including
the IP address. Custom repository IDs and pinned file metadata are stored locally
in `%APPDATA%\KeyUp Voice\custom-models.json`.
For local models, this file also stores the selected folder path. That path is
not sent to Hugging Face or GitHub, and the model files are not copied.

Downloaded files are checked against pinned sizes and SHA-256 hashes.
Recognition and translation do not require a network connection after setup.

## Logs

Operational logs are stored in:

```text
%APPDATA%\KeyUp Voice\keyup-voice.log
```

Logs contain application state, device/backend information, errors, durations,
and recognized character counts. They are not intended to contain recorded
audio or recognized text. Review logs before attaching them to a public issue.

## Telemetry

KeyUp Voice does not include analytics, advertising, account sign-in, or
telemetry.
