# Third-party notices

KeyUp Voice depends on third-party software and model files. This document is
an overview, not a replacement for the license files distributed by each
project.

## Runtime dependencies

| Project | Purpose | License |
| --- | --- | --- |
| [faster-whisper](https://github.com/SYSTRAN/faster-whisper) | Whisper inference integration | MIT |
| [CTranslate2](https://github.com/OpenNMT/CTranslate2) | Optimized CPU and GPU inference | MIT |
| [PySide6 / Qt for Python](https://doc.qt.io/qtforpython-6) | Desktop user interface | LGPLv3/GPLv3 or commercial Qt license |
| [NumPy](https://github.com/numpy/numpy) | Audio array processing | BSD-3-Clause |
| [python-sounddevice](https://github.com/spatialaudio/python-sounddevice) | Microphone capture | MIT |
| [PyAV](https://github.com/PyAV-Org/PyAV) | Audio support used by faster-whisper | BSD-3-Clause |
| [ONNX Runtime](https://github.com/microsoft/onnxruntime) | Voice activity detection runtime | MIT |
| [Hugging Face Hub](https://github.com/huggingface/huggingface_hub) | Model download support | Apache-2.0 |

PySide6 is available under open-source and commercial licensing options.
Distributors are responsible for selecting and complying with the license that
applies to their build.

## Whisper model files

Model files are not committed to this repository or embedded in the installer.
They are downloaded at runtime from the
[Systran faster-whisper collection](https://huggingface.co/collections/Systran/faster-whisper).
The selected repositories identify their license as MIT. Review the model card
and license of each model before redistribution.

## NVIDIA CUDA runtime

NVIDIA CUDA libraries are not committed to this repository or embedded in the
installer. On compatible NVIDIA systems, KeyUp Voice can download selected
official `nvidia-cublas-cu12` and `nvidia-cudnn-cu12` packages from PyPI.
Those files are subject to NVIDIA's applicable software license terms, including
the [CUDA Toolkit EULA](https://docs.nvidia.com/cuda/eula/index.html).

## Binary distributions

Python wheels and generated application bundles may include additional
transitive dependencies. Preserve the license files included in those packages
when redistributing a binary build.
