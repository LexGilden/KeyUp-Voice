from __future__ import annotations

import ctypes
import array
import gc
import hashlib
import json
import math
import os
import shutil
import sys
import threading
import time
import traceback
import urllib.request
import wave
import winreg
import zipfile
from ctypes import wintypes
from pathlib import Path
from typing import Any

import numpy as np
import sounddevice as sd
from PySide6.QtCore import (
    QByteArray,
    QMimeData,
    QObject,
    QPoint,
    QRectF,
    QRunnable,
    QThreadPool,
    QTimer,
    Qt,
    Signal,
)
from PySide6.QtGui import (
    QAction,
    QBrush,
    QColor,
    QConicalGradient,
    QCursor,
    QIcon,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QRadialGradient,
)
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QStyle,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)


APP_NAME = "KeyUp Voice"
LEGACY_APP_NAME = "Golos"
APP_VERSION = "1.4.1"
APP_DIR = Path(__file__).resolve().parent
INSTALL_DIR = (
    Path(sys.executable).resolve().parent
    if getattr(sys, "frozen", False)
    else APP_DIR
)
MODELS_DIR = INSTALL_DIR / "models"
INSTALLED_CUDA_PATH = INSTALL_DIR / "cuda-runtime"
COMPONENT_DOWNLOAD_DIR = INSTALL_DIR / ".component-downloads"
DEFAULT_MODEL_ID = "medium"
WHISPER_MODELS: dict[str, dict[str, Any]] = {
    "tiny": {
        "repository": "Systran/faster-whisper-tiny",
        "revision": "d90ca5fe260221311c53c58e660288d3deb8d356",
        "labels": ("Tiny — самый быстрый", "Tiny — fastest"),
        "files": {
            "config.json": (2249, "a73a28cdfe1c43ccc7202fa333d1f89c202477271407ae9a7f19afa52039cac8"),
            "model.bin": (75538270, "dcb76c6586fc06cbdac6dd21f14cfd129cc4cdd9dce19bf4ffa62e59cbe6e6d1"),
            "tokenizer.json": (2203239, "fb7b63191e9bb045082c79fd742a3106a12c99513ab30df4a0d47fa6cb6fd0ab"),
            "vocabulary.txt": (459861, "34ce3fe1c5041027b3f8d42912270993f986dbc4bb34cf27f951e34a1e453913"),
        },
    },
    "base": {
        "repository": "Systran/faster-whisper-base",
        "revision": "ebe41f70d5b6dfa9166e2c581c45c9c0cfc57b66",
        "labels": ("Base — быстрый", "Base — fast"),
        "files": {
            "config.json": (2309, "56a6d8110d311f19c8f0471e562832c7527f146b567275bfca59fcf7c184da9a"),
            "model.bin": (145217532, "d01c3014881c9c6f3133c182f3d2887eb6ca1c789a7538c5c007196857a0a6a9"),
            "tokenizer.json": (2203239, "fb7b63191e9bb045082c79fd742a3106a12c99513ab30df4a0d47fa6cb6fd0ab"),
            "vocabulary.txt": (459861, "34ce3fe1c5041027b3f8d42912270993f986dbc4bb34cf27f951e34a1e453913"),
        },
    },
    "small": {
        "repository": "Systran/faster-whisper-small",
        "revision": "536b0662742c02347bc0e980a01041f333bce120",
        "labels": ("Small — баланс скорости", "Small — speed balanced"),
        "files": {
            "config.json": (2370, "b55496ac7940a7ae47d2c01eab40edfd8701feec1229d9cce3b40014383fb828"),
            "model.bin": (483546902, "3e305921506d8872816023e4c273e75d2419fb89b24da97b4fe7bce14170d671"),
            "tokenizer.json": (2203239, "fb7b63191e9bb045082c79fd742a3106a12c99513ab30df4a0d47fa6cb6fd0ab"),
            "vocabulary.txt": (459861, "34ce3fe1c5041027b3f8d42912270993f986dbc4bb34cf27f951e34a1e453913"),
        },
    },
    "medium": {
        "repository": "Systran/faster-whisper-medium",
        "revision": "7832330bcea9a8d5fd6d6637c49fe5d256e98277",
        "labels": ("Medium — рекомендуется", "Medium — recommended"),
        "files": {
            "config.json": (2257, "3622a2ddc41ec0e0fd4e68c13c6830f03b90c38d89aaad184de02c8c642cf807"),
            "model.bin": (1527906378, "9b45e1009dcc4ab601eff815b61d80e60ce3fd8c74c1a14f4a282258286b51ae"),
            "tokenizer.json": (2203239, "fb7b63191e9bb045082c79fd742a3106a12c99513ab30df4a0d47fa6cb6fd0ab"),
            "vocabulary.txt": (459861, "34ce3fe1c5041027b3f8d42912270993f986dbc4bb34cf27f951e34a1e453913"),
        },
    },
    "large-v3": {
        "repository": "Systran/faster-whisper-large-v3",
        "revision": "edaa852ec7e145841d8ffdb056a99866b5f0a478",
        "labels": ("Large-v3 — максимальная точность", "Large-v3 — highest accuracy"),
        "files": {
            "config.json": (2394, "a9306624f5ec14270a014b647e5c316b6e03a662c369758d1b90697a7b0655b9"),
            "model.bin": (3087284237, "69f74147e3334731bc3a76048724833325d2ec74642fb52620eda87352e3d4f1"),
            "preprocessor_config.json": (340, "7ccc62c6f2765af1f3b46c00c9b5894426835a05021c8b9c01eecb6dfb542711"),
            "tokenizer.json": (2480617, "6d8cbd7cd0d8d5815e478dac67b85a26bbe77c1f5e0c6d76d1ce2abc0e5f21ca"),
        },
    },
}
NVIDIA_PACKAGES = (
    ("nvidia-cublas-cu12", "12.8.3.14"),
    ("nvidia-cudnn-cu12", "9.8.0.87"),
)
DEFAULT_MODEL_PATH = MODELS_DIR / "faster-whisper-medium"
ROAMING_DIR = Path(os.environ.get("APPDATA", APP_DIR))
DATA_DIR = ROAMING_DIR / APP_NAME
LEGACY_DATA_DIR = ROAMING_DIR / LEGACY_APP_NAME
CONFIG_PATH = DATA_DIR / "config.json"
LOG_PATH = DATA_DIR / "keyup-voice.log"
SOUND_DIR = DATA_DIR / "sounds"
_sound_lock = threading.Lock()
_dll_directory_handles: list[Any] = []
LEGACY_CONFIG_PATH = APP_DIR / "config.json"
LEGACY_ROAMING_CONFIG_PATH = LEGACY_DATA_DIR / "config.json"
DEFAULT_CONFIG: dict[str, Any] = {
    "model_id": DEFAULT_MODEL_ID,
    "model_path": str(DEFAULT_MODEL_PATH),
    "language": "ru",
    "hotkey": "right_alt",
    "translation_hotkey": "right_ctrl",
    "device": "auto",
    "compute_type": "auto",
    "microphone": None,
    "output_device": None,
    "min_recording_seconds": 0.25,
    "max_recording_seconds": 300,
    "paste_restore_delay_ms": 700,
    "sound_cues": False,
    "autostart": False,
    "overlay_position": "bottom_center",
    "animation_style": "live_ball",
}

APP_REGISTRY_PATH = rf"Software\LexGilden\{APP_NAME}"
INTERFACE_LANGUAGE_VALUE_NAME = "InterfaceLanguage"


def installed_interface_language() -> str:
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            APP_REGISTRY_PATH,
            0,
            winreg.KEY_READ,
        ) as key:
            value, _ = winreg.QueryValueEx(
                key,
                INTERFACE_LANGUAGE_VALUE_NAME,
            )
            if str(value).lower() in {"ru", "en"}:
                return str(value).lower()
    except (FileNotFoundError, OSError):
        pass
    return "ru"


UI_LANGUAGE = installed_interface_language()
DEFAULT_CONFIG["interface_language"] = UI_LANGUAGE


def set_interface_language(language: Any) -> None:
    global UI_LANGUAGE
    UI_LANGUAGE = "en" if str(language).lower() == "en" else "ru"


def tr(russian: str, english: str) -> str:
    return english if UI_LANGUAGE == "en" else russian


VK_CODES = {
    "left_alt": 0xA4,
    "right_alt": 0xA5,
    "left_ctrl": 0xA2,
    "caps_lock": 0x14,
    "scroll_lock": 0x91,
    "pause": 0x13,
    "right_ctrl": 0xA3,
    "f6": 0x75,
    "f7": 0x76,
    "f8": 0x77,
    "f9": 0x78,
    "f10": 0x79,
    "f11": 0x7A,
    "f12": 0x7B,
}

HOTKEY_LABELS = {
    "left_alt": ("Левый Alt", "Left Alt"),
    "right_alt": ("Правый Alt", "Right Alt"),
    "left_ctrl": ("Левый Ctrl", "Left Ctrl"),
    "right_ctrl": ("Правый Ctrl", "Right Ctrl"),
    "scroll_lock": ("Scroll Lock", "Scroll Lock"),
    "pause": ("Pause/Break", "Pause/Break"),
    "caps_lock": ("Caps Lock", "Caps Lock"),
    "f6": ("F6", "F6"),
    "f7": ("F7", "F7"),
    "f8": ("F8", "F8"),
    "f9": ("F9", "F9"),
    "f10": ("F10", "F10"),
    "f11": ("F11", "F11"),
    "f12": ("F12", "F12"),
}

ANIMATION_LABELS = {
    "live_ball": ("1. Живой шар", "1. Living ball"),
    "light_ring": ("2. Световое кольцо", "2. Light ring"),
    "wave_dot": ("3. Волновая точка", "3. Wave dot"),
    "morph": ("4. Морф-анимация", "4. Morph animation"),
    "orb": ("5. Орб (сфера)", "5. Orb (sphere)"),
    "mini_eq": ("6. Мини-эквалайзер", "6. Mini equalizer"),
    "liquid": ("7. Жидкая капля", "7. Liquid drop"),
}


def localized_label(labels: tuple[str, str]) -> str:
    return labels[1] if UI_LANGUAGE == "en" else labels[0]

AUTOSTART_REGISTRY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
AUTOSTART_VALUE_NAME = APP_NAME
LEGACY_AUTOSTART_VALUE_NAME = LEGACY_APP_NAME


def autostart_command() -> str:
    if getattr(sys, "frozen", False):
        return f'"{Path(sys.executable).resolve()}"'
    return f'"{Path(sys.executable).resolve()}" "{Path(__file__).resolve()}"'


def is_autostart_enabled() -> bool:
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            AUTOSTART_REGISTRY_PATH,
            0,
            winreg.KEY_READ,
        ) as key:
            for value_name in (
                AUTOSTART_VALUE_NAME,
                LEGACY_AUTOSTART_VALUE_NAME,
            ):
                try:
                    value, _ = winreg.QueryValueEx(key, value_name)
                    if str(value).strip():
                        return True
                except FileNotFoundError:
                    continue
            return False
    except FileNotFoundError:
        return False


def set_autostart(enabled: bool) -> None:
    with winreg.CreateKeyEx(
        winreg.HKEY_CURRENT_USER,
        AUTOSTART_REGISTRY_PATH,
        0,
        winreg.KEY_SET_VALUE,
    ) as key:
        if enabled:
            winreg.SetValueEx(
                key,
                AUTOSTART_VALUE_NAME,
                0,
                winreg.REG_SZ,
                autostart_command(),
            )
        for value_name in (
            LEGACY_AUTOSTART_VALUE_NAME,
            *(() if enabled else (AUTOSTART_VALUE_NAME,)),
        ):
            try:
                winreg.DeleteValue(key, value_name)
            except FileNotFoundError:
                pass

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
winmm = ctypes.windll.winmm

WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105
WM_QUIT = 0x0012
KEYEVENTF_KEYUP = 0x0002
VK_CONTROL = 0x11
VK_V = 0x56
INPUT_KEYBOARD = 1
SW_RESTORE = 9


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class DISPLAY_DEVICEW(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("DeviceName", wintypes.WCHAR * 32),
        ("DeviceString", wintypes.WCHAR * 128),
        ("StateFlags", wintypes.DWORD),
        ("DeviceID", wintypes.WCHAR * 128),
        ("DeviceKey", wintypes.WCHAR * 128),
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT),
    ]


class INPUT(ctypes.Structure):
    _anonymous_ = ("union",)
    _fields_ = [("type", wintypes.DWORD), ("union", INPUT_UNION)]


HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)

user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC, wintypes.HINSTANCE, wintypes.DWORD]
user32.SetWindowsHookExW.restype = wintypes.HANDLE
user32.CallNextHookEx.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
user32.CallNextHookEx.restype = ctypes.c_ssize_t
user32.UnhookWindowsHookEx.argtypes = [wintypes.HANDLE]
user32.UnhookWindowsHookEx.restype = wintypes.BOOL
user32.GetForegroundWindow.restype = wintypes.HWND
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.GetAsyncKeyState.restype = ctypes.c_short
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.SetForegroundWindow.restype = wintypes.BOOL
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.ShowWindow.restype = wintypes.BOOL
user32.BringWindowToTop.argtypes = [wintypes.HWND]
user32.BringWindowToTop.restype = wintypes.BOOL
user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
user32.SendInput.restype = wintypes.UINT
user32.EnumDisplayDevicesW.argtypes = [
    wintypes.LPCWSTR,
    wintypes.DWORD,
    ctypes.POINTER(DISPLAY_DEVICEW),
    wintypes.DWORD,
]
user32.EnumDisplayDevicesW.restype = wintypes.BOOL
kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
kernel32.CreateMutexW.restype = wintypes.HANDLE
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL
kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.GetModuleHandleW.restype = wintypes.HMODULE
winmm.PlaySoundW.argtypes = [wintypes.LPCWSTR, wintypes.HMODULE, wintypes.DWORD]
winmm.PlaySoundW.restype = wintypes.BOOL


def display_adapters() -> list[str]:
    adapters: list[str] = []
    index = 0
    while True:
        device = DISPLAY_DEVICEW()
        device.cb = ctypes.sizeof(DISPLAY_DEVICEW)
        if not user32.EnumDisplayDevicesW(
            None,
            index,
            ctypes.byref(device),
            0,
        ):
            break
        name = device.DeviceString.strip()
        if name and name not in adapters:
            adapters.append(name)
        index += 1
    return adapters


def has_nvidia_gpu() -> bool:
    return any("nvidia" in adapter.lower() for adapter in display_adapters())


def normalized_model_id(model_id: Any) -> str:
    value = str(model_id or DEFAULT_MODEL_ID).lower()
    return value if value in WHISPER_MODELS else DEFAULT_MODEL_ID


def installed_model_path(model_id: Any) -> Path:
    selected = normalized_model_id(model_id)
    return MODELS_DIR / f"faster-whisper-{selected}"


def model_files(model_id: Any) -> dict[str, tuple[int, str]]:
    selected = normalized_model_id(model_id)
    return dict(WHISPER_MODELS[selected]["files"])


def model_download_size(model_id: Any) -> int:
    return sum(size for size, _sha256 in model_files(model_id).values())


def model_label(model_id: Any) -> str:
    selected = normalized_model_id(model_id)
    labels = WHISPER_MODELS[selected]["labels"]
    size_gb = model_download_size(selected) / (1024 ** 3)
    if size_gb >= 1:
        size = f"{size_gb:.1f} {tr('ГБ', 'GB')}"
    else:
        size = f"{model_download_size(selected) / (1024 ** 2):.0f} {tr('МБ', 'MB')}"
    return f"{localized_label(labels)} · {size}"


def whisper_model_available(path: Path, model_id: Any = None) -> bool:
    files = model_files(model_id) if model_id is not None else None
    if files is None:
        for candidate_id in WHISPER_MODELS:
            if whisper_model_available(path, candidate_id):
                return True
        return False
    return all(
        (path / file_name).is_file()
        and (path / file_name).stat().st_size == expected_size
        for file_name, (expected_size, _sha256) in files.items()
    )


def load_config() -> dict[str, Any]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    config = DEFAULT_CONFIG.copy()
    if not CONFIG_PATH.exists():
        for legacy_path in (
            LEGACY_ROAMING_CONFIG_PATH,
            LEGACY_CONFIG_PATH,
        ):
            if not legacy_path.exists():
                continue
            try:
                config.update(json.loads(legacy_path.read_text(encoding="utf-8")))
                save_config(config)
                return config
            except (OSError, json.JSONDecodeError):
                continue
    if CONFIG_PATH.exists():
        try:
            config.update(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError) as exc:
            print(
                tr(
                    f"Не удалось прочитать config.json: {exc}",
                    f"Could not read config.json: {exc}",
                ),
                file=sys.stderr,
            )
    else:
        save_config(config)
    return config


def save_config(config: dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(
        json.dumps(config, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def log_message(message: str) -> None:
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        with LOG_PATH.open("a", encoding="utf-8") as log_file:
            log_file.write(f"[{timestamp}] {message.rstrip()}\n")
    except OSError:
        pass


def _create_chime(
    path: Path,
    notes: list[tuple[float, float]],
    wake_output: bool = False,
    volume: float = 0.45,
) -> None:
    sample_rate = 44100
    pcm = array.array("h")
    if wake_output:
        # A non-zero pilot wakes digital outputs; pure silence may be discarded.
        pilot_frames = int(sample_rate * 0.38)
        for index in range(pilot_frames):
            fade = min(1.0, index / (sample_rate * 0.03))
            pilot = 0.018 * fade * math.sin(
                2.0 * math.pi * 1000.0 * index / sample_rate
            )
            pcm.append(int(32767 * pilot))
        pcm.extend([0] * int(sample_rate * 0.04))
    for frequency, duration in notes:
        frame_count = int(sample_rate * duration)
        attack = max(1, int(sample_rate * 0.012))
        release = max(1, int(sample_rate * min(0.055, duration * 0.45)))
        for index in range(frame_count):
            if index < attack:
                envelope = index / attack
            elif index >= frame_count - release:
                envelope = max(0.0, (frame_count - index - 1) / release)
            else:
                envelope = 1.0
            phase = 2.0 * math.pi * frequency * index / sample_rate
            tone = math.sin(phase) + 0.16 * math.sin(phase * 2.0)
            pcm.append(int(32767 * volume * envelope * tone))
        pcm.extend([0] * int(sample_rate * 0.018))

    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        output.writeframes(pcm.tobytes())


def ensure_notification_sounds() -> dict[str, Path]:
    SOUND_DIR.mkdir(parents=True, exist_ok=True)
    paths = {
        "start": SOUND_DIR / "start-v7.wav",
        "success": SOUND_DIR / "success-v4.wav",
    }
    if not paths["start"].exists():
        _create_chime(
            paths["start"],
            [(520.0, 0.075), (780.0, 0.11)],
            wake_output=True,
            volume=0.45,
        )
    if not paths["success"].exists():
        _create_chime(
            paths["success"],
            [(590.0, 0.10), (740.0, 0.12), (990.0, 0.22)],
        )
    return paths


def windows_sound_mapper_device() -> int | None:
    """Return the WMME mapper that follows the current Windows default output."""
    try:
        for index, device in enumerate(sd.query_devices()):
            if (
                int(device["max_output_channels"]) > 0
                and int(device["hostapi"]) == 0
            ):
                return index
    except Exception as exc:
        log_message(f"Could not resolve Windows sound mapper: {exc!r}")
    return None


def play_notification_sound(
    kind: str,
    output_device: Any = None,
    blocking: bool = False,
) -> None:
    try:
        path = ensure_notification_sounds()[kind]
        log_message(
            f"Notification sound queued: {kind}, device={output_device!r}"
        )

        def play() -> None:
            try:
                with _sound_lock:
                    if output_device is None:
                        flags = 0x00020000 | 0x00000002 | 0x00200000
                        played = bool(winmm.PlaySoundW(str(path), None, flags))
                        log_message(
                            "Notification system playback finished: "
                            f"kind={kind}, result={played}, path={str(path)!r}"
                        )
                        if not played:
                            raise OSError("Windows PlaySoundW returned FALSE")
                        return

                    resolved_device = (
                        int(output_device)
                    )
                    device_info = sd.query_devices(resolved_device, "output")
                    host_info = sd.query_hostapis(int(device_info["hostapi"]))
                    with wave.open(str(path), "rb") as source:
                        source_sample_rate = source.getframerate()
                        channels = source.getnchannels()
                        pcm = np.frombuffer(
                            source.readframes(source.getnframes()),
                            dtype=np.int16,
                        ).astype(np.float32) / 32768.0
                    audio = pcm.reshape(-1, channels)
                    sample_rate = int(device_info["default_samplerate"])
                    if sample_rate != source_sample_rate and audio.size:
                        target_length = max(
                            1,
                            round(
                                audio.shape[0]
                                * sample_rate
                                / source_sample_rate
                            ),
                        )
                        source_positions = np.arange(
                            audio.shape[0],
                            dtype=np.float64,
                        )
                        target_positions = np.linspace(
                            0,
                            audio.shape[0] - 1,
                            target_length,
                        )
                        audio = np.column_stack(
                            [
                                np.interp(
                                    target_positions,
                                    source_positions,
                                    audio[:, channel],
                                )
                                for channel in range(channels)
                            ]
                        ).astype(np.float32)
                    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
                    log_message(
                        "Notification output opened: "
                        f"kind={kind}, requested={output_device!r}, "
                        f"resolved={resolved_device!r}, "
                        f"name={device_info['name']!r}, "
                        f"hostapi={host_info['name']!r}, "
                        f"source_rate={source_sample_rate}, "
                        f"output_rate={sample_rate}, peak={peak:.3f}"
                    )
                    with sd.OutputStream(
                        samplerate=sample_rate,
                        channels=channels,
                        dtype="float32",
                        device=resolved_device,
                    ) as stream:
                        underflowed = stream.write(audio)
                log_message(
                    f"Notification sound played: {kind}, "
                    f"device={resolved_device!r}, underflow={underflowed}"
                )
            except Exception as exc:
                log_message(f"Notification sound failed: {kind}: {exc!r}")

        if blocking:
            play()
        else:
            threading.Thread(
                target=play,
                name=f"notification-sound-{kind}",
                daemon=True,
            ).start()
    except Exception as exc:
        log_message(f"Notification sound failed: {exc!r}")


def cuda_runtime_available() -> bool:
    """CTranslate2 can see a GPU even when the CUDA inference DLLs are missing."""
    try:
        ctypes.WinDLL("cublas64_12.dll")
        ctypes.WinDLL("cudnn64_9.dll")
    except OSError:
        return False
    return True


def configure_cuda_runtime() -> Path | None:
    candidates = [
        INSTALL_DIR / "cuda-runtime",
        APP_DIR / "cuda-runtime",
    ]
    if (
        getattr(sys, "frozen", False)
        and INSTALL_DIR.parent.name.lower() == "dist"
    ):
        candidates.append(INSTALL_DIR.parent.parent / "cuda-runtime")

    for candidate in candidates:
        if not (
            (candidate / "cublas64_12.dll").is_file()
            and (candidate / "cudnn64_9.dll").is_file()
        ):
            continue
        resolved = candidate.resolve()
        path_entries = os.environ.get("PATH", "").split(os.pathsep)
        if str(resolved).lower() not in {
            entry.lower() for entry in path_entries if entry
        }:
            os.environ["PATH"] = (
                str(resolved)
                + os.pathsep
                + os.environ.get("PATH", "")
            )
        if hasattr(os, "add_dll_directory"):
            _dll_directory_handles.append(
                os.add_dll_directory(str(resolved))
            )
        ctypes.WinDLL(str(resolved / "cublas64_12.dll"))
        ctypes.WinDLL(str(resolved / "cudnn64_9.dll"))
        log_message(f"CUDA runtime configured: {resolved}")
        return resolved

    log_message("CUDA runtime directory was not found")
    return None


def make_tray_icon(color: QColor) -> QIcon:
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)
    painter.drawRoundedRect(QRectF(21, 9, 22, 34), 11, 11)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(color, 5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.drawArc(QRectF(15, 20, 34, 31), 180 * 16, 180 * 16)
    painter.drawLine(QPoint(32, 51), QPoint(32, 58))
    painter.drawLine(QPoint(23, 58), QPoint(41, 58))
    painter.end()
    return QIcon(pixmap)


class SettingsDialog(QDialog):
    settings_saved = Signal(object)

    def __init__(self, config: dict[str, Any], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.config = config.copy()
        self.setWindowTitle(
            tr(f"Настройки {APP_NAME}", f"{APP_NAME} Settings")
        )
        self.setWindowIcon(make_tray_icon(QColor(57, 208, 132)))
        self.setMinimumWidth(480)

        layout = QVBoxLayout(self)
        intro = QLabel(
            tr(
                "Изменения клавиши, микрофона и интерфейса применяются сразу.",
                "Hotkey, microphone, and interface changes apply immediately.",
            )
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

        self.hotkey_combo = QComboBox()
        for key, labels in HOTKEY_LABELS.items():
            self.hotkey_combo.addItem(localized_label(labels), key)
        self._select_data(self.hotkey_combo, config.get("hotkey", "right_alt"))
        self.hotkey_combo.currentIndexChanged.connect(self._update_hotkey_warning)
        form.addRow(
            tr("Клавиша диктовки:", "Dictation hotkey:"),
            self.hotkey_combo,
        )

        self.hotkey_warning = QLabel()
        self.hotkey_warning.setWordWrap(True)
        self.hotkey_warning.setStyleSheet("color: #b26a00;")
        form.addRow("", self.hotkey_warning)

        self.translation_hotkey_combo = QComboBox()
        for key, labels in HOTKEY_LABELS.items():
            self.translation_hotkey_combo.addItem(
                localized_label(labels),
                key,
            )
        self._select_data(
            self.translation_hotkey_combo,
            config.get("translation_hotkey", "right_ctrl"),
        )
        self.translation_hotkey_combo.currentIndexChanged.connect(
            self._update_hotkey_warning
        )
        form.addRow(
            tr("Перевод на английский:", "Translate to English:"),
            self.translation_hotkey_combo,
        )

        self.microphone_combo = QComboBox()
        self.microphone_combo.addItem(
            tr(
                "Системный микрофон по умолчанию",
                "Default system microphone",
            ),
            None,
        )
        try:
            for index, device in enumerate(sd.query_devices()):
                if int(device["max_input_channels"]) > 0:
                    self.microphone_combo.addItem(str(device["name"]), index)
        except Exception as exc:
            self.microphone_combo.addItem(
                tr(
                    f"Не удалось получить список: {exc}",
                    f"Could not get device list: {exc}",
                ),
                None,
            )
        self._select_data(self.microphone_combo, config.get("microphone"))
        form.addRow(tr("Микрофон:", "Microphone:"), self.microphone_combo)

        self.language_combo = QComboBox()
        for label, value in (
            (tr("Русский", "Russian"), "ru"),
            (tr("Автоопределение", "Auto-detect"), None),
            (tr("Английский", "English"), "en"),
            (tr("Немецкий", "German"), "de"),
            (tr("Французский", "French"), "fr"),
            (tr("Испанский", "Spanish"), "es"),
        ):
            self.language_combo.addItem(label, value)
        self._select_data(self.language_combo, config.get("language", "ru"))
        form.addRow(
            tr("Язык распознавания:", "Recognition language:"),
            self.language_combo,
        )

        self.animation_combo = QComboBox()
        for key, labels in ANIMATION_LABELS.items():
            self.animation_combo.addItem(localized_label(labels), key)
        self._select_data(
            self.animation_combo,
            config.get("animation_style", "live_ball"),
        )
        form.addRow(tr("Анимация:", "Animation:"), self.animation_combo)

        self.position_combo = QComboBox()
        for label, value in (
            (tr("Снизу по центру", "Bottom center"), "bottom_center"),
            (tr("Сверху по центру", "Top center"), "top_center"),
            (tr("Снизу справа", "Bottom right"), "bottom_right"),
        ):
            self.position_combo.addItem(label, value)
        self._select_data(
            self.position_combo,
            config.get("overlay_position", "bottom_center"),
        )
        form.addRow(
            tr("Положение индикатора:", "Indicator position:"),
            self.position_combo,
        )

        self.max_duration = QSpinBox()
        self.max_duration.setRange(10, 1800)
        self.max_duration.setSuffix(tr(" сек.", " sec."))
        self.max_duration.setValue(int(config.get("max_recording_seconds", 300)))
        form.addRow(
            tr("Максимальная запись:", "Maximum recording:"),
            self.max_duration,
        )

        self.autostart = QCheckBox(
            tr(
                f"Запускать {APP_NAME} при входе в Windows",
                f"Start {APP_NAME} when signing in to Windows",
            )
        )
        self.autostart.setChecked(is_autostart_enabled())
        form.addRow(tr("Автозапуск:", "Startup:"), self.autostart)

        self.model_combo = QComboBox()
        configured_model_id = normalized_model_id(config.get("model_id"))
        configured_model_path = Path(str(config.get("model_path", "")))
        for model_id in WHISPER_MODELS:
            is_current_external = (
                model_id == configured_model_id
                and whisper_model_available(
                    configured_model_path,
                    model_id,
                )
            )
            is_installed = whisper_model_available(
                installed_model_path(model_id),
                model_id,
            )
            prefix = "✓ " if is_current_external or is_installed else ""
            self.model_combo.addItem(
                prefix + model_label(model_id),
                model_id,
            )
        self._select_data(
            self.model_combo,
            normalized_model_id(config.get("model_id")),
        )
        form.addRow(
            tr("Модель Whisper:", "Whisper model:"),
            self.model_combo,
        )

        model_path_label = QLabel(str(config.get("model_path", "")))
        model_path_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        model_path_label.setWordWrap(True)
        form.addRow(tr("Расположение:", "Location:"), model_path_label)

        backend = "GPU CUDA" if cuda_runtime_available() else "CPU int8"
        form.addRow(tr("Обработка:", "Processing:"), QLabel(backend))

        about_button = QPushButton(tr("О программе…", "About…"))
        about_button.clicked.connect(self._show_about)
        form.addRow(f"{APP_NAME}:", about_button)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText(
            tr("Сохранить", "Save")
        )
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(
            tr("Отмена", "Cancel")
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._update_hotkey_warning()

    @staticmethod
    def _select_data(combo: QComboBox, value: Any) -> None:
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    def _update_hotkey_warning(self) -> None:
        key = self.hotkey_combo.currentData()
        label = self.hotkey_combo.currentText()
        translation_key = self.translation_hotkey_combo.currentData()
        if key == translation_key:
            self.hotkey_warning.setStyleSheet("color: #c62828;")
            self.hotkey_warning.setText(
                tr(
                    "Клавиши обычного ввода и перевода должны отличаться.",
                    "The dictation and translation hotkeys must be different.",
                )
            )
        elif key in {"left_alt", "right_alt", "left_ctrl", "right_ctrl", "caps_lock"}:
            self.hotkey_warning.setStyleSheet("color: #b26a00;")
            self.hotkey_warning.setText(
                tr(
                    f"{label} будет занят диктовкой, пока {APP_NAME} запущен.",
                    f"{label} will be reserved for dictation while {APP_NAME} is running.",
                )
            )
        else:
            self.hotkey_warning.setStyleSheet("color: #b26a00;")
            self.hotkey_warning.setText("")

    def _show_about(self) -> None:
        selected_model = normalized_model_id(
            self.config.get("model_id")
        )
        QMessageBox.about(
            self,
            tr(f"О программе {APP_NAME}", f"About {APP_NAME}"),
            (
                f"<h2>{APP_NAME}</h2>"
                f"<p>{tr('Версия', 'Version')} {APP_VERSION}</p>"
                f"<p>{tr('Локальный голосовой ввод для Windows 11 на базе Whisper и faster-whisper.', 'Local voice input for Windows 11 powered by Whisper and faster-whisper.')}</p>"
                f"<p><b>{tr('Возможности', 'Features')}</b></p>"
                f"<ul>"
                f"<li>{tr('Диктовка по удержанию выбранной клавиши', 'Push-to-talk dictation with a configurable hotkey')}</li>"
                f"<li>{tr('Перевод речи на английский язык', 'Speech translation to English')}</li>"
                f"<li>{tr('Пять моделей Whisper: Tiny, Base, Small, Medium и Large-v3', 'Five Whisper models: Tiny, Base, Small, Medium, and Large-v3')}</li>"
                f"<li>{tr('Ускорение NVIDIA CUDA и режим CPU', 'NVIDIA CUDA acceleration and CPU mode')}</li>"
                f"<li>{tr('Русский и английский интерфейс', 'Russian and English interface')}</li>"
                f"</ul>"
                f"<p>{tr('Текущая модель:', 'Current model:')} "
                f"<b>{selected_model}</b></p>"
                f"<p>{tr('Распознавание выполняется локально. Записанный звук обрабатывается в памяти и не сохраняется после вставки текста.', 'Recognition runs locally. Recorded audio is processed in memory and is not retained after the text is inserted.')}</p>"
                "<p><b>© 2026 LexGilden</b></p>"
                "<p>MIT License</p>"
            ),
        )

    def _save(self) -> None:
        if (
            self.hotkey_combo.currentData()
            == self.translation_hotkey_combo.currentData()
        ):
            QMessageBox.warning(
                self,
                tr("Одинаковые клавиши", "Identical hotkeys"),
                tr(
                    "Выберите разные клавиши для обычного ввода и перевода.",
                    "Choose different hotkeys for dictation and translation.",
                ),
            )
            return
        try:
            set_autostart(self.autostart.isChecked())
        except OSError as exc:
            QMessageBox.critical(
                self,
                tr(
                    "Не удалось изменить автозапуск",
                    "Could not change startup settings",
                ),
                tr(
                    f"Windows не разрешила изменить настройку автозапуска:\n{exc}",
                    f"Windows did not allow the startup setting to be changed:\n{exc}",
                ),
            )
            return
        updated = self.config.copy()
        selected_model_id = normalized_model_id(
            self.model_combo.currentData()
        )
        current_model_id = normalized_model_id(
            self.config.get("model_id")
        )
        selected_model_path = (
            Path(str(self.config.get("model_path", "")))
            if selected_model_id == current_model_id
            else installed_model_path(selected_model_id)
        )
        updated.update(
            {
                "model_id": selected_model_id,
                "model_path": str(selected_model_path),
                "hotkey": self.hotkey_combo.currentData(),
                "translation_hotkey": self.translation_hotkey_combo.currentData(),
                "microphone": self.microphone_combo.currentData(),
                "language": self.language_combo.currentData(),
                "animation_style": self.animation_combo.currentData(),
                "overlay_position": self.position_combo.currentData(),
                "max_recording_seconds": self.max_duration.value(),
                "sound_cues": False,
                "autostart": self.autostart.isChecked(),
            }
        )
        save_config(updated)
        self.settings_saved.emit(updated)
        self.accept()


class KeyboardHook(QObject):
    pressed = Signal()
    released = Signal()
    failed = Signal(str)

    def __init__(self, vk_code: int) -> None:
        super().__init__()
        self.vk_code = vk_code
        self._thread: threading.Thread | None = None
        self._thread_id = 0
        self._hook = None
        self._callback = None
        self._is_down = False

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._message_loop, name="keyboard-hook", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._thread_id:
            user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
        if self._thread:
            self._thread.join(timeout=1)

    def _message_loop(self) -> None:
        self._thread_id = kernel32.GetCurrentThreadId()

        @HOOKPROC
        def callback(n_code: int, w_param: int, l_param: int) -> int:
            if n_code >= 0:
                event = ctypes.cast(l_param, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
                if event.vkCode == self.vk_code:
                    if w_param in (WM_KEYDOWN, WM_SYSKEYDOWN):
                        if not self._is_down:
                            self._is_down = True
                            self.pressed.emit()
                    elif w_param in (WM_KEYUP, WM_SYSKEYUP):
                        if self._is_down:
                            self._is_down = False
                            self.released.emit()
                    return 1
            return user32.CallNextHookEx(self._hook, n_code, w_param, l_param)

        self._callback = callback
        module = kernel32.GetModuleHandleW(None)
        self._hook = user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._callback, module, 0)
        if not self._hook:
            error_code = kernel32.GetLastError()
            self.failed.emit(
                tr(
                    "Не удалось установить глобальный перехват клавиатуры "
                    f"(код Windows {error_code})",
                    "Could not install the global keyboard hook "
                    f"(Windows error {error_code})",
                )
            )
            return

        message = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(message), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(message))
            user32.DispatchMessageW(ctypes.byref(message))

        user32.UnhookWindowsHookEx(self._hook)
        self._hook = None


class KeyStatePoller(QObject):
    """Reliable UI-thread fallback for keyboards whose hook events are swallowed."""

    pressed = Signal()
    released = Signal()

    def __init__(self, vk_code: int) -> None:
        super().__init__()
        self.vk_code = vk_code
        self._is_down = False
        self.timer = QTimer(self)
        self.timer.setInterval(15)
        self.timer.timeout.connect(self._poll)

    def start(self) -> None:
        self._is_down = bool(user32.GetAsyncKeyState(self.vk_code) & 0x8000)
        self.timer.start()

    def stop(self) -> None:
        self.timer.stop()

    def _poll(self) -> None:
        is_down = bool(user32.GetAsyncKeyState(self.vk_code) & 0x8000)
        if is_down == self._is_down:
            return
        self._is_down = is_down
        if is_down:
            self.pressed.emit()
        else:
            self.released.emit()


class AudioRecorder(QObject):
    level_changed = Signal(float)
    auto_stopped = Signal()

    def __init__(self, microphone: Any, max_seconds: float) -> None:
        super().__init__()
        self.microphone = microphone
        self.max_seconds = max_seconds
        self.stream: sd.InputStream | None = None
        self.chunks: list[np.ndarray] = []
        self.sample_rate = 16000
        self.started_at = 0.0
        self._lock = threading.Lock()
        self._auto_stop_requested = False

    @property
    def is_recording(self) -> bool:
        return self.stream is not None

    def start(self) -> None:
        if self.stream is not None:
            return
        device_info = sd.query_devices(self.microphone, "input")
        self.sample_rate = int(device_info["default_samplerate"])
        self.chunks = []
        self.started_at = time.monotonic()
        self._auto_stop_requested = False

        def callback(indata: np.ndarray, frames: int, timing: Any, status: Any) -> None:
            del frames, timing
            if status:
                print(
                    tr(f"Аудио: {status}", f"Audio: {status}"),
                    file=sys.stderr,
                )
            mono = indata[:, 0].copy()
            with self._lock:
                self.chunks.append(mono)
            rms = float(np.sqrt(np.mean(np.square(mono), dtype=np.float64)))
            visual_level = min(1.0, max(0.0, math.log10(1.0 + rms * 90.0)))
            self.level_changed.emit(visual_level)
            if (
                not self._auto_stop_requested
                and time.monotonic() - self.started_at >= self.max_seconds
            ):
                self._auto_stop_requested = True
                self.auto_stopped.emit()

        self.stream = sd.InputStream(
            device=self.microphone,
            channels=1,
            samplerate=self.sample_rate,
            dtype="float32",
            callback=callback,
            blocksize=0,
        )
        self.stream.start()

    def stop(self) -> tuple[np.ndarray, int, float]:
        stream = self.stream
        self.stream = None
        duration = max(0.0, time.monotonic() - self.started_at)
        if stream is not None:
            stream.stop()
            stream.close()
        with self._lock:
            chunks = self.chunks
            self.chunks = []
        audio = np.concatenate(chunks) if chunks else np.empty(0, dtype=np.float32)
        return audio, self.sample_rate, duration


class WorkerSignals(QObject):
    succeeded = Signal(object)
    failed = Signal(str)


class FunctionWorker(QRunnable):
    def __init__(self, function: Any, *args: Any) -> None:
        super().__init__()
        self.function = function
        self.args = args
        self.signals = WorkerSignals()

    def run(self) -> None:
        try:
            result = self.function(*self.args)
        except Exception:
            details = traceback.format_exc()
            log_message(details)
            self.signals.failed.emit(details)
        else:
            self.signals.succeeded.emit(result)


class ComponentWorkerSignals(QObject):
    status = Signal(str)
    progress = Signal(str, object, object)
    succeeded = Signal(object)
    failed = Signal(str)


class ComponentInstallWorker(QRunnable):
    def __init__(
        self,
        install_model: bool,
        install_cuda: bool,
        model_id: str,
        current_model_path: Path,
    ) -> None:
        super().__init__()
        self.install_model = install_model
        self.install_cuda = install_cuda
        self.model_id = normalized_model_id(model_id)
        self.target_model_path = installed_model_path(self.model_id)
        self.current_model_path = current_model_path
        self.signals = ComponentWorkerSignals()
        self.cancel_event = threading.Event()

    def cancel(self) -> None:
        self.cancel_event.set()

    def _check_cancelled(self) -> None:
        if self.cancel_event.is_set():
            raise RuntimeError(tr("Загрузка отменена", "Download cancelled"))

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as source:
            while chunk := source.read(4 * 1024 * 1024):
                digest.update(chunk)
        return digest.hexdigest()

    def _download(
        self,
        url: str,
        destination: Path,
        expected_size: int,
        expected_sha256: str,
        label: str,
    ) -> Path:
        destination.parent.mkdir(parents=True, exist_ok=True)
        if (
            destination.is_file()
            and destination.stat().st_size == expected_size
            and self._sha256(destination) == expected_sha256
        ):
            self.signals.progress.emit(label, expected_size, expected_size)
            return destination

        partial = destination.with_suffix(destination.suffix + ".part")
        if (
            partial.is_file()
            and partial.stat().st_size == expected_size
            and self._sha256(partial) == expected_sha256
        ):
            os.replace(partial, destination)
            self.signals.progress.emit(label, expected_size, expected_size)
            return destination
        downloaded = partial.stat().st_size if partial.is_file() else 0
        headers = {"User-Agent": f"{APP_NAME}/{APP_VERSION}"}
        if downloaded:
            headers["Range"] = f"bytes={downloaded}-"
        request = urllib.request.Request(url, headers=headers)
        response = urllib.request.urlopen(request, timeout=60)
        if downloaded and getattr(response, "status", 200) != 206:
            downloaded = 0
        mode = "ab" if downloaded else "wb"
        with response, partial.open(mode) as output:
            self.signals.progress.emit(label, downloaded, expected_size)
            while True:
                self._check_cancelled()
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                output.write(chunk)
                downloaded += len(chunk)
                self.signals.progress.emit(label, downloaded, expected_size)

        if partial.stat().st_size != expected_size:
            raise RuntimeError(
                tr(
                    f"Неверный размер файла {label}: "
                    f"{partial.stat().st_size} вместо {expected_size}",
                    f"Incorrect size for {label}: "
                    f"{partial.stat().st_size} instead of {expected_size}",
                )
            )
        self.signals.status.emit(
            tr(f"Проверка {label}…", f"Verifying {label}…")
        )
        actual_hash = self._sha256(partial)
        if actual_hash != expected_sha256:
            partial.unlink(missing_ok=True)
            raise RuntimeError(
                tr(
                    f"Контрольная сумма {label} не совпала",
                    f"Checksum mismatch for {label}",
                )
            )
        os.replace(partial, destination)
        return destination

    def _install_whisper(self) -> None:
        specification = WHISPER_MODELS[self.model_id]
        repository = str(specification["repository"])
        revision = str(specification["revision"])
        self.target_model_path.mkdir(parents=True, exist_ok=True)
        for file_name, (expected_size, expected_sha256) in model_files(
            self.model_id
        ).items():
            self._check_cancelled()
            url = (
                "https://huggingface.co/"
                f"{repository}/resolve/"
                f"{revision}/{file_name}?download=true"
            )
            self._download(
                url,
                self.target_model_path / file_name,
                expected_size,
                expected_sha256,
                f"Whisper: {file_name}",
            )
        if not whisper_model_available(
            self.target_model_path,
            self.model_id,
        ):
            raise RuntimeError(
                tr(
                    "Модель Whisper установлена не полностью",
                    "The Whisper model was not installed completely",
                )
            )

    def _resolve_pypi_wheel(
        self,
        package_name: str,
        version: str,
    ) -> tuple[str, int, str, str]:
        api_url = f"https://pypi.org/pypi/{package_name}/{version}/json"
        request = urllib.request.Request(
            api_url,
            headers={"User-Agent": f"{APP_NAME}/{APP_VERSION}"},
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            metadata = json.load(response)
        for release_file in metadata.get("urls", []):
            file_name = str(release_file.get("filename", ""))
            if file_name.endswith("-win_amd64.whl"):
                return (
                    str(release_file["url"]),
                    int(release_file["size"]),
                    str(release_file["digests"]["sha256"]),
                    file_name,
                )
        raise RuntimeError(
            tr(
                f"Для {package_name} {version} не найден пакет Windows x64",
                f"No Windows x64 package was found for {package_name} {version}",
            )
        )

    def _install_cuda(self) -> None:
        wheel_paths: list[Path] = []
        for package_name, version in NVIDIA_PACKAGES:
            self._check_cancelled()
            self.signals.status.emit(
                tr(
                    f"Получение сведений о {package_name}…",
                    f"Getting information for {package_name}…",
                )
            )
            url, size, sha256, file_name = self._resolve_pypi_wheel(
                package_name,
                version,
            )
            wheel_paths.append(
                self._download(
                    url,
                    COMPONENT_DOWNLOAD_DIR / file_name,
                    size,
                    sha256,
                    f"NVIDIA: {package_name}",
                )
            )

        temporary = INSTALL_DIR / "cuda-runtime.installing"
        if temporary.exists():
            shutil.rmtree(temporary)
        temporary.mkdir(parents=True)
        try:
            for wheel_path in wheel_paths:
                self._check_cancelled()
                self.signals.status.emit(
                    tr(
                        f"Распаковка {wheel_path.name}…",
                        f"Extracting {wheel_path.name}…",
                    )
                )
                with zipfile.ZipFile(wheel_path) as archive:
                    for member in archive.infolist():
                        normalized = member.filename.replace("\\", "/")
                        if (
                            "/bin/" not in normalized
                            or not normalized.lower().endswith(".dll")
                        ):
                            continue
                        target = temporary / Path(normalized).name
                        with archive.open(member) as source, target.open(
                            "wb"
                        ) as output:
                            shutil.copyfileobj(source, output, 4 * 1024 * 1024)
            required = ("cublas64_12.dll", "cudnn64_9.dll")
            if not all((temporary / name).is_file() for name in required):
                raise RuntimeError(
                    tr(
                        "В пакетах NVIDIA отсутствуют необходимые DLL",
                        "Required DLL files are missing from the NVIDIA packages",
                    )
                )
            if INSTALLED_CUDA_PATH.exists():
                shutil.rmtree(INSTALLED_CUDA_PATH)
            os.replace(temporary, INSTALLED_CUDA_PATH)
            for wheel_path in wheel_paths:
                wheel_path.unlink(missing_ok=True)
        finally:
            if temporary.exists():
                shutil.rmtree(temporary)

    def run(self) -> None:
        try:
            required_free = 0
            if self.install_model:
                required_free += int(
                    model_download_size(self.model_id) * 1.15
                )
            if self.install_cuda:
                required_free += 3 * 1024 * 1024 * 1024
            free_space = shutil.disk_usage(INSTALL_DIR).free
            if free_space < required_free:
                required_gb = required_free / (1024 ** 3)
                raise RuntimeError(
                    tr(
                        "Недостаточно свободного места. Требуется не менее "
                        f"{required_gb:.0f} ГБ.",
                        "Not enough free disk space. At least "
                        f"{required_gb:.0f} GB is required.",
                    )
                )
            if self.install_model:
                self.signals.status.emit(
                    tr(
                        "Установка модели Whisper…",
                        "Installing the Whisper model…",
                    )
                )
                self._install_whisper()
            if self.install_cuda:
                self.signals.status.emit(
                    tr(
                        "Установка ускорения NVIDIA CUDA…",
                        "Installing NVIDIA CUDA acceleration…",
                    )
                )
                self._install_cuda()
        except Exception as exc:
            log_message(f"Component installation failed:\n{traceback.format_exc()}")
            self.signals.failed.emit(str(exc))
        else:
            self.signals.succeeded.emit(
                {
                    "model_path": str(
                        self.target_model_path
                        if self.install_model
                        else self.current_model_path
                    ),
                    "model_id": self.model_id,
                    "cuda_installed": self.install_cuda,
                }
            )


class ComponentSetupDialog(QDialog):
    def __init__(
        self,
        config: dict[str, Any],
        requested_model_id: Any = None,
        force_model: bool = False,
    ) -> None:
        super().__init__()
        self.config = config
        self.worker: ComponentInstallWorker | None = None
        self.installing = False
        self.adapters = display_adapters()
        self.force_model = force_model
        self.configured_model_id = normalized_model_id(
            config.get("model_id")
        )
        self.model_id = normalized_model_id(
            requested_model_id
            if requested_model_id is not None
            else config.get("model_id")
        )
        self.current_model_path = Path(str(config.get("model_path", "")))
        self.install_model = not whisper_model_available(
            self.current_model_path,
            self.model_id,
        )
        self.install_cuda = has_nvidia_gpu() and not cuda_runtime_available()
        self.setWindowTitle(
            tr(
                f"Установка компонентов {APP_NAME}",
                f"{APP_NAME} Component Setup",
            )
        )
        self.setWindowIcon(make_tray_icon(QColor(57, 208, 132)))
        self.setMinimumWidth(560)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)

        layout = QVBoxLayout(self)
        title = QLabel(
            tr(
                "<h2>Нужны дополнительные компоненты</h2>",
                "<h2>Additional components are required</h2>",
            )
        )
        layout.addWidget(title)

        self.model_combo = QComboBox()
        for model_id in WHISPER_MODELS:
            is_current_external = (
                model_id == self.configured_model_id
                and whisper_model_available(
                    self.current_model_path,
                    model_id,
                )
            )
            is_installed = whisper_model_available(
                installed_model_path(model_id),
                model_id,
            )
            prefix = "✓ " if is_current_external or is_installed else ""
            self.model_combo.addItem(
                prefix + model_label(model_id),
                model_id,
            )
        model_index = self.model_combo.findData(self.model_id)
        if model_index >= 0:
            self.model_combo.setCurrentIndex(model_index)
        self.model_combo.currentIndexChanged.connect(
            self._model_selection_changed
        )
        layout.addWidget(
            QLabel(tr("Выберите модель Whisper:", "Choose a Whisper model:"))
        )
        layout.addWidget(self.model_combo)

        self.model_details = QLabel()
        self.model_details.setWordWrap(True)
        layout.addWidget(self.model_details)
        self._update_model_details()

        required_components: list[str] = []
        if self.install_model:
            required_components.append(tr("модель Whisper", "Whisper model"))
        if self.install_cuda:
            required_components.append(
                tr("ускорение NVIDIA CUDA", "NVIDIA CUDA acceleration")
            )
        if required_components:
            description_text = (
                tr(
                    "Будут загружены: ",
                    "The following will be downloaded: ",
                )
                + ", ".join(required_components)
                + "."
            )
        else:
            description_text = tr(
                "Все необходимые компоненты уже установлены.",
                "All required components are already installed.",
            )
        description = QLabel(description_text)
        description.setWordWrap(True)
        layout.addWidget(description)

        adapter_text = ", ".join(self.adapters) or tr(
            "Видеокарта не определена",
            "Graphics adapter not detected",
        )
        self.gpu_label = QLabel(
            f"<b>{tr('Видеокарта:', 'Graphics adapter:')}</b> {adapter_text}"
        )
        self.gpu_label.setWordWrap(True)
        layout.addWidget(self.gpu_label)

        mode = (
            tr(
                "NVIDIA CUDA — будет загружено GPU-ускорение",
                "NVIDIA CUDA — GPU acceleration will be downloaded",
            )
            if self.install_cuda
            else tr(
                "CPU — дополнительные библиотеки CUDA не требуются",
                "CPU — no additional CUDA libraries are required",
            )
        )
        self.mode_label = QLabel(
            f"<b>{tr('Режим:', 'Mode:')}</b> {mode}"
        )
        self.mode_label.setWordWrap(True)
        layout.addWidget(self.mode_label)

        self.status_label = QLabel(
            tr(
                "Нажмите «Скачать и установить». Загрузку можно продолжить "
                "после обрыва соединения.",
                "Click “Download and install”. The download can resume "
                "after a connection interruption.",
            )
        )
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        layout.addWidget(self.progress)
        self.progress_details = QLabel("")
        layout.addWidget(self.progress_details)

        self.install_button = QPushButton(
            tr("Скачать и установить", "Download and install")
        )
        self.install_button.clicked.connect(self._start)
        layout.addWidget(self.install_button)
        self.cancel_button = QPushButton(tr("Отмена", "Cancel"))
        self.cancel_button.clicked.connect(self._cancel)
        layout.addWidget(self.cancel_button)

    def _model_selection_changed(self, _index: int = 0) -> None:
        self.model_id = normalized_model_id(
            self.model_combo.currentData()
        )
        selected_path = installed_model_path(self.model_id)
        current_is_selected = (
            self.model_id == self.configured_model_id
            and whisper_model_available(
                self.current_model_path,
                self.model_id,
            )
        )
        self.install_model = not (
            current_is_selected
            or whisper_model_available(selected_path, self.model_id)
        )
        self._update_model_details()

    def _update_model_details(self) -> None:
        selected_path = installed_model_path(self.model_id)
        current_is_selected = (
            self.model_id == self.configured_model_id
            and whisper_model_available(
                self.current_model_path,
                self.model_id,
            )
        )
        if current_is_selected or whisper_model_available(
            selected_path,
            self.model_id,
        ):
            status = tr("уже установлена", "already installed")
        else:
            status = tr("будет загружена", "will be downloaded")
        self.model_details.setText(
            f"{model_label(self.model_id)} — {status}."
        )

    @staticmethod
    def _format_size(value: int) -> str:
        return f"{value / (1024 * 1024):.1f} {tr('МБ', 'MB')}"

    def _start(self) -> None:
        if self.installing:
            return
        self.installing = True
        self.install_button.setEnabled(False)
        self.cancel_button.setText(
            tr("Остановить загрузку", "Stop download")
        )
        selected_path = installed_model_path(self.model_id)
        selected_model_path = (
            selected_path
            if whisper_model_available(selected_path, self.model_id)
            else self.current_model_path
        )
        self.worker = ComponentInstallWorker(
            self.install_model,
            self.install_cuda,
            self.model_id,
            selected_model_path,
        )
        self.worker.signals.status.connect(self.status_label.setText)
        self.worker.signals.progress.connect(self._progress)
        self.worker.signals.succeeded.connect(self._completed)
        self.worker.signals.failed.connect(self._failed)
        QThreadPool.globalInstance().start(self.worker)

    def _progress(self, label: str, current: object, total: object) -> None:
        current_bytes = int(current)
        total_bytes = max(1, int(total))
        self.status_label.setText(label)
        self.progress.setValue(
            min(100, round(current_bytes * 100 / total_bytes))
        )
        self.progress_details.setText(
            f"{self._format_size(current_bytes)} {tr('из', 'of')} "
            f"{self._format_size(total_bytes)}"
        )

    def _completed(self, result: object) -> None:
        installed = dict(result)  # type: ignore[arg-type]
        self.config["model_id"] = installed["model_id"]
        self.config["model_path"] = installed["model_path"]
        self.config["device"] = "auto"
        self.config["compute_type"] = "auto"
        save_config(self.config)
        self.installing = False
        self.progress.setValue(100)
        self.status_label.setText(
            tr("Компоненты установлены", "Components installed")
        )
        log_message(
            "Components installed: "
            f"model={installed['model_path']}, "
            f"cuda={installed['cuda_installed']}"
        )
        self.accept()

    def _failed(self, message: str) -> None:
        self.installing = False
        self.install_button.setEnabled(True)
        self.install_button.setText(tr("Повторить", "Retry"))
        self.cancel_button.setText(tr("Закрыть", "Close"))
        self.status_label.setText(
            tr(
                f"Не удалось установить компоненты: {message}",
                f"Could not install components: {message}",
            )
        )

    def _cancel(self) -> None:
        if self.installing and self.worker is not None:
            self.worker.cancel()
            self.cancel_button.setEnabled(False)
            self.status_label.setText(
                tr("Остановка загрузки…", "Stopping download…")
            )
            return
        self.reject()

    def closeEvent(self, event: Any) -> None:
        if self.installing and self.worker is not None:
            self.worker.cancel()
            self.status_label.setText(
                tr("Остановка загрузки…", "Stopping download…")
            )
            event.ignore()
            return
        super().closeEvent(event)


class VoiceOverlay(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
            | Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedSize(170, 150)
        self.state = "listening"
        self.level = 0.0
        self.smoothed_level = 0.0
        self.display_level = 0.0
        self.appear_progress = 1.0
        self.record_transition = 1.0
        self.processing_transition = 1.0
        self.completion_transition = 1.0
        self.voice_started = False
        self.voice_activity_frames = 0
        self.phase = 0.0
        self.message = tr("Слушаю", "Listening")
        self.hotkey_label = "Scroll Lock"
        self.position = "bottom_center"
        self.animation_style = "live_ball"
        self.timer = QTimer(self)
        self.timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.timer.timeout.connect(self._tick)
        self.timer.start(16)

    def show_for_state(self, state: str, message: str | None = None) -> None:
        previous_state = self.state
        self.state = state
        if state == "listening" and (previous_state != "listening" or not self.isVisible()):
            self.appear_progress = 0.0
            self.record_transition = 0.0
            self.voice_started = False
            self.voice_activity_frames = 0
            self.smoothed_level = 0.0
            self.display_level = 0.0
        elif state == "transcribing" and previous_state == "listening":
            self.processing_transition = 0.0
        elif state == "success" and previous_state == "transcribing":
            self.completion_transition = 0.0
        self.message = message or {
            "listening": tr("Слушаю", "Listening"),
            "transcribing": tr("Распознаю…", "Transcribing…"),
            "success": tr("Готово", "Done"),
            "error": tr("Ошибка", "Error"),
        }.get(state, "")
        screen = QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
        if screen:
            area = screen.availableGeometry()
            if self.position == "top_center":
                x = area.center().x() - self.width() // 2
                y = area.top() + 48
            elif self.position == "bottom_right":
                x = area.right() - self.width() - 32
                y = area.bottom() - self.height() - 48
            else:
                x = area.center().x() - self.width() // 2
                y = area.bottom() - self.height() - 48
            self.move(x, y)
        self.show()
        self.raise_()
        self.update()

    def set_level(self, value: float) -> None:
        self.level = min(1.0, max(0.0, value))
        if self.state == "listening" and not self.voice_started:
            if self.level >= 0.27:
                self.voice_activity_frames += 1
            else:
                self.voice_activity_frames = max(0, self.voice_activity_frames - 1)
            if self.voice_activity_frames >= 3:
                self.voice_started = True
                self.record_transition = 0.0

    def _tick(self) -> None:
        self.phase += 0.067
        if self.appear_progress < 1.0:
            self.appear_progress = min(1.0, self.appear_progress + 0.105)
        elif self.voice_started:
            self.record_transition = min(1.0, self.record_transition + 0.05)
        if self.state == "transcribing":
            self.processing_transition = min(1.0, self.processing_transition + 0.035)
        if self.state == "success":
            self.completion_transition = min(1.0, self.completion_transition + 0.08)
        level_factor = 0.14 if self.level > self.smoothed_level else 0.065
        self.smoothed_level += (self.level - self.smoothed_level) * level_factor
        target = (
            min(1.0, 0.18 + self.smoothed_level * 1.55)
            if self.state == "listening"
            else 0.3
        )
        display_factor = 0.13 if target > self.display_level else 0.075
        self.display_level += (target - self.display_level) * display_factor
        self.update()

    def _draw_appearance(self, painter: QPainter, progress: float = 1.0) -> None:
        eased = 1.0 - (1.0 - progress) ** 3
        scale = 0.45 + 0.55 * eased
        center = QPoint(85, 75)
        painter.save()
        painter.setOpacity(eased)

        if self.animation_style == "light_ring":
            radius = int(24 * scale)
            gradient = QConicalGradient(center, -35)
            gradient.setColorAt(0.0, QColor(104, 83, 255))
            gradient.setColorAt(0.5, QColor(215, 126, 255))
            gradient.setColorAt(1.0, QColor(69, 126, 255))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QBrush(gradient), 3))
            painter.drawEllipse(center, radius, radius)
        elif self.animation_style == "mini_eq":
            painter.setPen(Qt.PenStyle.NoPen)
            for index in range(3):
                painter.setBrush(QColor(169, 103, 255))
                painter.drawEllipse(QPoint(61 + index * 24, 75), int(5 * scale), int(5 * scale))
        elif self.animation_style == "liquid":
            painter.setPen(Qt.PenStyle.NoPen)
            fill = QLinearGradient(70, 62, 101, 86)
            fill.setColorAt(0.0, QColor(112, 255, 248))
            fill.setColorAt(1.0, QColor(0, 164, 188))
            painter.setBrush(QBrush(fill))
            painter.drawEllipse(center, int(14 * scale), int(11 * scale))
        elif self.animation_style == "wave_dot":
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(158, 255, 111))
            painter.drawEllipse(center, int(8 * scale), int(8 * scale))
        elif self.animation_style == "morph":
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(255, 142, 32))
            painter.drawEllipse(center, int(8 * scale), int(8 * scale))
        else:
            base = QColor(53, 139, 255) if self.animation_style == "live_ball" else QColor(67, 161, 255)
            glow = QRadialGradient(center, 25 * scale)
            glow.setColorAt(0.0, QColor(base.red(), base.green(), base.blue(), 160))
            glow.setColorAt(1.0, QColor(base.red(), base.green(), base.blue(), 0))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(glow))
            painter.drawEllipse(center, int(25 * scale), int(25 * scale))
            sphere = QRadialGradient(QPoint(80, 69), 20 * scale)
            sphere.setColorAt(0.0, QColor(125, 230, 255))
            sphere.setColorAt(0.42, QColor(55, 145, 255))
            sphere.setColorAt(1.0, QColor(25, 63, 176))
            painter.setBrush(QBrush(sphere))
            painter.drawEllipse(center, int(13 * scale), int(13 * scale))
        painter.restore()

    @staticmethod
    def _accent(index: int, alpha: int = 255) -> QColor:
        palette = (
            (70, 232, 255),
            (64, 139, 255),
            (137, 92, 255),
            (255, 91, 191),
        )
        red, green, blue = palette[index % len(palette)]
        return QColor(red, green, blue, alpha)

    def _linear_brush(self, alpha: int = 255) -> QBrush:
        gradient = QLinearGradient(18, 28, self.width() - 18, self.height() - 24)
        gradient.setColorAt(0.0, self._accent(0, alpha))
        gradient.setColorAt(0.34, self._accent(1, alpha))
        gradient.setColorAt(0.68, self._accent(2, alpha))
        gradient.setColorAt(1.0, self._accent(3, alpha))
        return QBrush(gradient)

    def _blob_path(
        self,
        center_x: float,
        center_y: float,
        radius: float,
        stretch_x: float = 1.0,
        motion: float = 1.0,
    ) -> QPainterPath:
        path = QPainterPath()
        for index in range(97):
            angle = math.tau * index / 96
            wobble = motion * (
                math.sin(angle * 3 + self.phase * 1.3) * 0.10
                + math.sin(angle * 5 - self.phase * 0.8) * 0.055
            )
            reactive = motion * self.display_level * (
                0.08 + 0.07 * math.sin(angle * 2 - self.phase)
            )
            local_radius = radius * (1.0 + wobble + reactive)
            x = center_x + math.cos(angle) * local_radius * stretch_x
            y = center_y + math.sin(angle) * local_radius
            if index == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)
        path.closeSubpath()
        return path

    def _draw_live_ball(self, painter: QPainter, color: QColor) -> None:
        if self.state == "transcribing":
            ring = QConicalGradient(QPoint(85, 75), -self.phase * 30)
            ring.setColorAt(0.0, QColor(48, 144, 255))
            ring.setColorAt(0.48, QColor(68, 220, 255))
            ring.setColorAt(0.7, QColor(48, 144, 255, 45))
            ring.setColorAt(1.0, QColor(48, 144, 255))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QBrush(ring), 6))
            painter.drawEllipse(QPoint(85, 75), 34, 34)
            dashed = QPen(QColor(45, 155, 255, 170), 2, Qt.PenStyle.DashLine)
            dashed.setDashOffset(self.phase * 5)
            painter.setPen(dashed)
            painter.drawEllipse(QPoint(85, 75), 48, 48)
            return

        radius = 25 + 14 * self.display_level
        path = self._blob_path(85, 75, radius)
        glow = QRadialGradient(QPoint(85, 75), radius + 26)
        glow.setColorAt(0.2, QColor(46, 132, 255, 100))
        glow.setColorAt(0.7, QColor(37, 115, 255, 30))
        glow.setColorAt(1.0, QColor(37, 115, 255, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(glow))
        painter.drawEllipse(QPoint(85, 75), int(radius + 26), int(radius + 26))
        fill = QRadialGradient(QPoint(74, 61), radius * 1.8)
        fill.setColorAt(0.0, QColor(111, 229, 255))
        fill.setColorAt(0.3, QColor(56, 151, 255))
        fill.setColorAt(0.72, QColor(36, 92, 232))
        fill.setColorAt(1.0, QColor(21, 43, 131))
        painter.setBrush(QBrush(fill))
        painter.drawPath(path)
        painter.setBrush(QColor(255, 255, 255, 115))
        painter.drawEllipse(QPoint(73, 58), 5, 3)

    def _draw_live_ball_transition(self, painter: QPainter, transition: float) -> None:
        eased = transition * transition * (3.0 - 2.0 * transition)
        active_radius = 25 + 14 * self.display_level
        radius = 13 + (active_radius - 13) * eased
        path = self._blob_path(85, 75, radius, motion=eased)
        glow_radius = radius + 22 * eased
        glow = QRadialGradient(QPoint(85, 75), max(14.0, glow_radius))
        glow.setColorAt(0.0, QColor(46, 132, 255, int(100 * eased)))
        glow.setColorAt(0.7, QColor(37, 115, 255, int(30 * eased)))
        glow.setColorAt(1.0, QColor(37, 115, 255, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(glow))
        painter.drawEllipse(QPoint(85, 75), int(glow_radius), int(glow_radius))
        fill = QRadialGradient(QPoint(78, 66), radius * 1.8)
        fill.setColorAt(0.0, QColor(111, 229, 255))
        fill.setColorAt(0.3, QColor(56, 151, 255))
        fill.setColorAt(0.72, QColor(36, 92, 232))
        fill.setColorAt(1.0, QColor(21, 43, 131))
        painter.setBrush(QBrush(fill))
        painter.drawPath(path)
        painter.setBrush(QColor(255, 255, 255, 115))
        highlight = 3 + int(2 * eased)
        painter.drawEllipse(
            QPoint(int(85 - radius * 0.38), int(75 - radius * 0.46)),
            highlight,
            max(2, highlight - 2),
        )

    def _draw_light_ring(self, painter: QPainter, color: QColor) -> None:
        strength = max(0.2, self.display_level)
        radius = 35 + 5 * math.sin(self.phase) * strength
        thickness = 4 + 8 * strength
        gradient = QConicalGradient(QPoint(85, 75), -self.phase * 24)
        gradient.setColorAt(0.0, QColor(113, 82, 255))
        gradient.setColorAt(0.28, QColor(216, 116, 255))
        gradient.setColorAt(0.52, QColor(255, 255, 255))
        gradient.setColorAt(0.66, QColor(126, 89, 255))
        gradient.setColorAt(1.0, QColor(72, 108, 255))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(129, 82, 255, 35), thickness + 17))
        painter.drawEllipse(QPoint(85, 75), int(radius), int(radius))
        painter.setPen(QPen(QBrush(gradient), thickness))
        painter.drawEllipse(QPoint(85, 75), int(radius), int(radius))

    def _draw_light_ring_transition(self, painter: QPainter, transition: float) -> None:
        eased = transition * transition * (3.0 - 2.0 * transition)
        strength = max(0.2, self.display_level)
        radius = 24 + (35 + 5 * math.sin(self.phase) * strength - 24) * eased
        thickness = 3 + (4 + 8 * strength - 3) * eased
        gradient = QConicalGradient(QPoint(85, 75), -self.phase * 24 * eased)
        gradient.setColorAt(0.0, QColor(113, 82, 255))
        gradient.setColorAt(0.28, QColor(216, 116, 255))
        gradient.setColorAt(0.52, QColor(255, 255, 255))
        gradient.setColorAt(0.72, QColor(126, 89, 255))
        gradient.setColorAt(1.0, QColor(72, 108, 255))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(129, 82, 255, int(35 * eased)), thickness + 17 * eased))
        painter.drawEllipse(QPoint(85, 75), int(radius), int(radius))
        painter.setPen(QPen(QBrush(gradient), thickness))
        painter.drawEllipse(QPoint(85, 75), int(radius), int(radius))

    def _draw_wave_dot(self, painter: QPainter, color: QColor) -> None:
        lime = QColor(137, 255, 93)
        strength = max(0.2, self.display_level)
        painter.setPen(Qt.PenStyle.NoPen)
        glow = QRadialGradient(QPoint(85, 75), 22)
        glow.setColorAt(0.0, QColor(195, 255, 160, 230))
        glow.setColorAt(0.45, QColor(137, 255, 93, 85))
        glow.setColorAt(1.0, QColor(137, 255, 93, 0))
        painter.setBrush(QBrush(glow))
        painter.drawEllipse(QPoint(85, 75), 22, 22)
        painter.setBrush(QColor(181, 255, 139))
        painter.drawEllipse(QPoint(85, 75), 9, 9)
        for index in range(3):
            radius = 23 + index * 14 + 8 * strength * math.sin(self.phase - index * 0.5)
            pen = QPen(QColor(137, 255, 93, 115 - index * 25), 2)
            if self.state == "transcribing":
                pen.setStyle(Qt.PenStyle.DashLine)
                pen.setDashOffset(self.phase * 5)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(pen)
            painter.drawEllipse(QPoint(85, 75), int(radius), int(radius))

    def _draw_wave_dot_transition(self, painter: QPainter, transition: float) -> None:
        eased = transition * transition * (3.0 - 2.0 * transition)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(181, 255, 139))
        painter.drawEllipse(QPoint(85, 75), 9, 9)
        for index in range(3):
            target_radius = 23 + index * 14
            radius = 10 + (target_radius - 10) * eased
            alpha = int((115 - index * 25) * eased)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(137, 255, 93, alpha), 2))
            painter.drawEllipse(QPoint(85, 75), int(radius), int(radius))

    def _draw_morph(self, painter: QPainter, color: QColor) -> None:
        orange = QColor(255, 142, 32)
        if self.state == "transcribing":
            path = QPainterPath()
            for index in range(61):
                x = 30 + index * 1.85
                y = 75 + math.sin(index * 0.28 + self.phase * 1.8) * 11
                if index == 0:
                    path.moveTo(x, y)
                else:
                    path.lineTo(x, y)
            painter.setPen(QPen(QColor(255, 142, 32, 45), 13))
            painter.drawPath(path)
            painter.setPen(QPen(orange, 4))
            painter.drawPath(path)
            return
        for index, factor in enumerate((0.38, 0.68, 1.0, 0.68, 0.38)):
            wave = 0.72 + 0.28 * math.sin(self.phase + index * 0.8)
            height = (22 + 55 * self.display_level) * factor * wave
            x = 53 + index * 16
            painter.setPen(QPen(QColor(255, 142, 32, 48), 17))
            painter.drawLine(QPoint(x, int(75 - height / 2)), QPoint(x, int(75 + height / 2)))
            pen = QPen(orange, 7)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.drawLine(QPoint(x, int(75 - height / 2)), QPoint(x, int(75 + height / 2)))

    def _draw_morph_transition(self, painter: QPainter, transition: float) -> None:
        eased = transition * transition * (3.0 - 2.0 * transition)
        orange = QColor(255, 142, 32)
        factors = (0.38, 0.68, 1.0, 0.68, 0.38)
        target_positions = (53, 69, 85, 101, 117)
        for index, factor in enumerate(factors):
            wave = 0.72 + 0.28 * math.sin(self.phase + index * 0.8)
            target_height = (22 + 55 * self.display_level) * factor * wave
            height = 10 + (target_height - 10) * eased
            x = 85 + (target_positions[index] - 85) * eased
            painter.setPen(QPen(QColor(255, 142, 32, int(48 * eased)), 10 + 7 * eased))
            painter.drawLine(QPoint(int(x), int(75 - height / 2)), QPoint(int(x), int(75 + height / 2)))
            pen = QPen(orange, 7)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.drawLine(QPoint(int(x), int(75 - height / 2)), QPoint(int(x), int(75 + height / 2)))

    def _draw_mini_eq(self, painter: QPainter, color: QColor) -> None:
        if self.state == "transcribing":
            for index, x in enumerate((61, 85, 109)):
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(145, 87, 255, 50))
                glow_radius = 14 if index == 1 else 12
                painter.drawEllipse(QPoint(x, 75), glow_radius, glow_radius)
                gradient = QLinearGradient(x, 59, x, 91)
                gradient.setColorAt(0.0, QColor(216, 135, 255))
                gradient.setColorAt(1.0, QColor(104, 60, 255))
                painter.setBrush(QBrush(gradient))
                if index == 1:
                    painter.drawRoundedRect(QRectF(x - 5, 61, 10, 28), 5, 5)
                else:
                    painter.drawEllipse(QPoint(x, 75), 7, 7)
            return

        factors = (0.52, 1.0, 0.62)
        for index, factor in enumerate(factors):
            pulse = 0.82 + 0.18 * math.sin(self.phase + index * 0.9)
            height = (25 + 49 * self.display_level) * factor * pulse
            x = 61 + index * 24
            painter.setPen(QPen(QColor(151, 92, 255, 52), 19))
            painter.drawLine(
                QPoint(x, int(75 - height / 2)),
                QPoint(x, int(75 + height / 2)),
            )
            gradient = QLinearGradient(x, 43, x, 107)
            gradient.setColorAt(0.0, QColor(218, 139, 255))
            gradient.setColorAt(1.0, QColor(105, 61, 255))
            pen = QPen(QBrush(gradient), 10)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.drawLine(
                QPoint(x, int(75 - height / 2)),
                QPoint(x, int(75 + height / 2)),
            )

    def _draw_mini_eq_transition(self, painter: QPainter, transition: float) -> None:
        eased = transition * transition * (3.0 - 2.0 * transition)
        factors = (0.52, 1.0, 0.62)
        for index, factor in enumerate(factors):
            pulse = 0.82 + 0.18 * math.sin(self.phase + index * 0.9)
            target_height = (25 + 49 * self.display_level) * factor * pulse
            height = 10 + (target_height - 10) * eased
            x = 61 + index * 24
            glow_alpha = int(18 + 34 * eased)
            painter.setPen(QPen(QColor(151, 92, 255, glow_alpha), 11 + 8 * eased))
            painter.drawLine(
                QPoint(x, int(75 - height / 2)),
                QPoint(x, int(75 + height / 2)),
            )
            gradient = QLinearGradient(x, 43, x, 107)
            gradient.setColorAt(0.0, QColor(218, 139, 255))
            gradient.setColorAt(1.0, QColor(105, 61, 255))
            pen = QPen(QBrush(gradient), 10)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.drawLine(
                QPoint(x, int(75 - height / 2)),
                QPoint(x, int(75 + height / 2)),
            )

    def _draw_liquid(self, painter: QPainter, color: QColor) -> None:
        self._draw_liquid_shape(painter, 1.0)
        if self.state == "transcribing":
            center_x = 74 + math.sin(self.phase * 0.7) * 4
            satellite_x = int(min(152, center_x + 48 + 5 * math.sin(self.phase)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(11, 225, 226))
            painter.drawEllipse(QPoint(satellite_x, 67), 7, 7)

    def _draw_liquid_shape(self, painter: QPainter, transition: float) -> None:
        eased = transition * transition * (3.0 - 2.0 * transition)
        active_stretch = 1.15 + self.display_level * 0.75
        stretch = 1.0 + (active_stretch - 1.0) * eased
        active_center_x = 74 + math.sin(self.phase * 0.7) * 4
        center_x = 85 + (active_center_x - 85) * eased
        active_radius = 24 + 7 * self.display_level
        radius = 12 + (active_radius - 12) * eased
        path = self._blob_path(
            center_x,
            75,
            radius,
            stretch,
            motion=eased,
        )
        glow = QRadialGradient(QPoint(int(center_x), 75), 64)
        glow.setColorAt(0.0, QColor(29, 241, 239, int(100 * eased)))
        glow.setColorAt(0.58, QColor(0, 204, 215, int(28 * eased)))
        glow.setColorAt(1.0, QColor(0, 204, 215, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(glow))
        painter.drawEllipse(QPoint(int(center_x), 75), 64, 52)
        fill = QLinearGradient(38, 44, 132, 104)
        fill.setColorAt(0.0, QColor(113, 255, 248))
        fill.setColorAt(0.35, QColor(11, 225, 226))
        fill.setColorAt(1.0, QColor(0, 126, 159))
        painter.setBrush(QBrush(fill))
        painter.drawPath(path)
        painter.setBrush(QColor(255, 255, 255, 160))
        highlight_x = center_x - radius * 0.42
        highlight_y = 75 - radius * 0.5
        painter.drawEllipse(
            QPoint(int(highlight_x), int(highlight_y)),
            max(2, int(2 + 2 * eased)),
            max(2, int(2 + eased)),
        )

    def _draw_bars(self, painter: QPainter, color: QColor) -> None:
        for index in range(7):
            wave = 0.55 + 0.45 * math.sin(self.phase + index * 0.72)
            if self.state == "listening":
                height = 15 + 72 * self.display_level * wave
            else:
                height = 18 + 32 * wave
            x = 49 + index * 12
            bar_color = self._accent(index, 245)
            glow_pen = QPen(QColor(bar_color.red(), bar_color.green(), bar_color.blue(), 42), 15)
            glow_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(glow_pen)
            painter.drawLine(
                QPoint(x, int(75 - height / 2)),
                QPoint(x, int(75 + height / 2)),
            )
            pen = QPen(bar_color, 6)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.drawLine(
                QPoint(x, int(75 - height / 2)),
                QPoint(x, int(75 + height / 2)),
            )

    def _draw_orb(self, painter: QPainter, color: QColor) -> None:
        pulse = 0.5 + 0.5 * math.sin(self.phase)
        strength = max(0.22, self.display_level)
        center = QPoint(85, 75)
        radius = 17 + 15 * strength + 4 * pulse
        glow_radius = radius + 24 + 12 * strength * pulse
        glow = QRadialGradient(center, glow_radius)
        glow.setColorAt(0.0, self._accent(2, 120))
        glow.setColorAt(0.38, self._accent(1, 95))
        glow.setColorAt(0.7, self._accent(0, 34))
        glow.setColorAt(1.0, self._accent(0, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(glow))
        painter.drawEllipse(center, int(glow_radius), int(glow_radius))

        orb = QConicalGradient(center, -self.phase * 22)
        orb.setColorAt(0.0, self._accent(0))
        orb.setColorAt(0.28, self._accent(1))
        orb.setColorAt(0.55, self._accent(2))
        orb.setColorAt(0.8, self._accent(3))
        orb.setColorAt(1.0, self._accent(0))
        painter.setBrush(QBrush(orb))
        painter.drawEllipse(center, int(radius), int(radius))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(self._linear_brush(170), 2))
        painter.drawEllipse(center, int(radius), int(radius))
        sheen = QRadialGradient(QPoint(76, 64), 18)
        sheen.setColorAt(0.0, QColor(255, 255, 255, 205))
        sheen.setColorAt(0.35, QColor(255, 255, 255, 50))
        sheen.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setBrush(QBrush(sheen))
        painter.drawEllipse(center, int(radius), int(radius))

    def _draw_orb_transition(self, painter: QPainter, transition: float) -> None:
        eased = transition * transition * (3.0 - 2.0 * transition)
        painter.save()
        scale = 0.43 + 0.57 * eased
        painter.translate(85, 75)
        painter.scale(scale, scale)
        painter.translate(-85, -75)
        painter.setOpacity(0.82 + 0.18 * eased)
        self._draw_orb(painter, QColor(68, 174, 255))
        painter.restore()

    def _draw_waveform(self, painter: QPainter, color: QColor) -> None:
        amplitude = 10 + 48 * max(0.2, self.display_level)
        path = QPainterPath()
        for index in range(65):
            x = 20 + index * 2.0
            envelope = math.sin(math.pi * index / 64) ** 0.7
            y = 75 + math.sin(self.phase * 1.6 + index * 0.43) * amplitude * envelope
            if index == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)
        glow_pen = QPen(self._linear_brush(62), 16)
        glow_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(glow_pen)
        painter.drawPath(path)
        pen = QPen(self._linear_brush(245), 4)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawPath(path)

    def _draw_mic_ring(self, painter: QPainter, color: QColor) -> None:
        pulse = 0.5 + 0.5 * math.sin(self.phase)
        radius = 40 + 14 * max(0.22, self.display_level) * pulse
        ring_gradient = QConicalGradient(QPoint(85, 75), -self.phase * 18)
        ring_gradient.setColorAt(0.0, self._accent(0))
        ring_gradient.setColorAt(0.35, self._accent(1))
        ring_gradient.setColorAt(0.7, self._accent(3))
        ring_gradient.setColorAt(1.0, self._accent(0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QBrush(ring_gradient), 4))
        painter.drawEllipse(QPoint(85, 75), int(radius), int(radius))
        painter.setBrush(self._linear_brush())
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(76, 47, 18, 42), 9, 9)
        pen = QPen(self._linear_brush(), 4)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawArc(QRectF(67, 58, 36, 40), 180 * 16, 180 * 16)
        painter.drawLine(QPoint(85, 98), QPoint(85, 108))
        painter.drawLine(QPoint(74, 108), QPoint(96, 108))

    def _draw_capsule(self, painter: QPainter, color: QColor) -> None:
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._linear_brush(30))
        painter.drawRoundedRect(QRectF(15, 45, 140, 60), 30, 30)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(self._linear_brush(150), 2))
        painter.drawRoundedRect(QRectF(15, 45, 140, 60), 30, 30)
        pulse = 0.5 + 0.5 * math.sin(self.phase)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._linear_brush(55 + int(75 * pulse)))
        painter.drawEllipse(QPoint(50, 75), 22, 22)
        painter.setBrush(self._linear_brush())
        painter.drawEllipse(QPoint(50, 75), 11, 11)
        for index in range(3):
            dot_color = self._accent(index + 1)
            dot_color.setAlpha(100 + int(130 * (0.5 + 0.5 * math.sin(self.phase + index))))
            painter.setBrush(dot_color)
            painter.drawEllipse(QPoint(94 + index * 16, 75), 4, 4)

    def _draw_edge_bar(self, painter: QPainter, color: QColor) -> None:
        strength = max(0.12, self.display_level)
        pulse = 0.5 + 0.5 * math.sin(self.phase * 1.2)
        y = self.height() - 22
        for width, alpha in ((26, 28), (15, 55), (7, 235)):
            pen = QPen(
                self._linear_brush(min(255, alpha + int(40 * strength))),
                width + int(3 * strength * pulse),
            )
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            margin = 28 - int(15 * strength)
            painter.drawLine(QPoint(margin, y), QPoint(self.width() - margin, y))

    def _draw_cursor_dots(self, painter: QPainter, color: QColor) -> None:
        for index in range(4):
            pulse = 0.5 + 0.5 * math.sin(self.phase * 1.4 - index * 0.8)
            radius = 8 + 14 * max(0.2, self.display_level) * pulse
            dot = self._accent(index)
            dot.setAlpha(130 + int(125 * pulse))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(dot)
            painter.drawEllipse(QPoint(25 + index * 38, 32), int(radius), int(radius))

    def _draw_particles(self, painter: QPainter, color: QColor) -> None:
        strength = max(0.16, self.display_level)
        center_x, center_y = 85, 75
        painter.setPen(Qt.PenStyle.NoPen)
        for index in range(14):
            angle = self.phase * (0.35 + (index % 3) * 0.12) + index * 2.399
            orbit = 18 + (index % 5) * 7 + 18 * strength
            x = center_x + math.cos(angle) * orbit
            y = center_y + math.sin(angle * 1.17) * orbit * 0.75
            radius = 4 + (index % 3) * 2 + 4 * strength
            particle = self._accent(index)
            particle.setAlpha(80 + (index * 29) % 155)
            painter.setBrush(particle)
            painter.drawEllipse(QPoint(int(x), int(y)), int(radius), int(radius))

    def paintEvent(self, event: Any) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        colors = {
            "listening": QColor(57, 208, 132),
            "transcribing": QColor(91, 156, 255),
            "success": QColor(57, 208, 132),
            "error": QColor(245, 91, 91),
        }
        color = colors.get(self.state, QColor(180, 180, 180))
        drawers = {
            "live_ball": self._draw_live_ball,
            "light_ring": self._draw_light_ring,
            "wave_dot": self._draw_wave_dot,
            "morph": self._draw_morph,
            "orb": self._draw_orb,
            "mini_eq": self._draw_mini_eq,
            "liquid": self._draw_liquid,
        }
        active_drawer = drawers.get(self.animation_style, self._draw_live_ball)
        if self.state == "success" and self.completion_transition < 1.0:
            raw_completion = self.completion_transition
            completion = raw_completion * raw_completion * (
                3.0 - 2.0 * raw_completion
            )
            painter.save()
            painter.setOpacity(1.0 - completion)
            previous_state = self.state
            self.state = "transcribing"
            active_drawer(painter, color)
            self.state = previous_state
            painter.restore()
            painter.setOpacity(completion)

        if self.state == "success" and self.animation_style == "mini_eq":
            painter.setPen(Qt.PenStyle.NoPen)
            for index, x in enumerate((63, 85, 107)):
                glow = QRadialGradient(QPoint(x, 75), 13)
                glow.setColorAt(0.0, QColor(176, 111, 255, 150))
                glow.setColorAt(1.0, QColor(126, 70, 255, 0))
                painter.setBrush(QBrush(glow))
                painter.drawEllipse(QPoint(x, 75), 13, 13)
                painter.setBrush(QColor(173, 106, 255))
                painter.drawEllipse(QPoint(x, 75), 5, 5)
        elif self.state == "success":
            done_colors = {
                "live_ball": QColor(63, 160, 255),
                "light_ring": QColor(160, 101, 255),
                "wave_dot": QColor(137, 255, 93),
                "morph": QColor(255, 142, 32),
                "orb": QColor(68, 174, 255),
                "mini_eq": QColor(164, 100, 255),
                "liquid": QColor(12, 225, 226),
            }
            done = done_colors.get(self.animation_style, color)
            glow = QRadialGradient(QPoint(85, 75), 34)
            glow.setColorAt(0.0, QColor(done.red(), done.green(), done.blue(), 120))
            glow.setColorAt(1.0, QColor(done.red(), done.green(), done.blue(), 0))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(glow))
            painter.drawEllipse(QPoint(85, 75), 34, 34)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(done, 3))
            painter.drawEllipse(QPoint(85, 75), 19, 19)
            pen = QPen(done, 4)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            path = QPainterPath()
            path.moveTo(76, 75)
            path.lineTo(83, 82)
            path.lineTo(95, 67)
            painter.drawPath(path)
        elif self.state == "error":
            pen = QPen(color, 5)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.drawLine(74, 64, 96, 86)
            painter.drawLine(96, 64, 74, 86)
        else:
            if self.state == "listening" and not self.voice_started:
                self._draw_appearance(painter, self.appear_progress)
            elif self.state == "listening" and self.record_transition < 1.0:
                raw_transition = self.record_transition
                transition_drawers = {
                    "live_ball": self._draw_live_ball_transition,
                    "light_ring": self._draw_light_ring_transition,
                    "wave_dot": self._draw_wave_dot_transition,
                    "morph": self._draw_morph_transition,
                    "orb": self._draw_orb_transition,
                    "mini_eq": self._draw_mini_eq_transition,
                    "liquid": self._draw_liquid_shape,
                }
                transition_drawers.get(
                    self.animation_style,
                    self._draw_live_ball_transition,
                )(painter, raw_transition)
            elif self.state == "transcribing" and self.processing_transition < 1.0:
                raw_processing = self.processing_transition
                processing = raw_processing * raw_processing * (
                    3.0 - 2.0 * raw_processing
                )
                painter.save()
                painter.setOpacity(1.0 - processing)
                previous_state = self.state
                self.state = "listening"
                if self.voice_started:
                    active_drawer(painter, color)
                else:
                    self._draw_appearance(painter, 1.0)
                self.state = previous_state
                painter.restore()
                painter.save()
                painter.setOpacity(processing)
                active_drawer(painter, color)
                painter.restore()
            else:
                active_drawer(painter, color)
        painter.end()


class VoiceApp(QObject):
    def __init__(self, qt_app: QApplication) -> None:
        super().__init__()
        self.qt_app = qt_app
        self.config = load_config()
        self.thread_pool = QThreadPool.globalInstance()
        self.model = None
        self.active_device = ""
        self.active_compute_type = ""
        self.model_error = ""
        self.state = "loading"
        self.foreground_window = 0
        self.overlay = VoiceOverlay()
        self.overlay.position = str(
            self.config.get("overlay_position", "bottom_center")
        )
        self.overlay.animation_style = str(
            self.config.get("animation_style", "live_ball")
        )
        self.recorder = AudioRecorder(
            self.config.get("microphone"),
            float(self.config["max_recording_seconds"]),
        )
        self.recorder.level_changed.connect(self.overlay.set_level)
        self.recorder.auto_stopped.connect(self.finish_recording)

        self.keyboard_hooks: list[KeyboardHook] = []
        self.key_pollers: list[KeyStatePoller] = []
        self.hotkey_label = ""
        self.translation_hotkey_label = ""
        self.recording_mode = "transcribe"
        self.settings_dialog: SettingsDialog | None = None
        self._configure_hotkey()

        self.tray = QSystemTrayIcon(make_tray_icon(QColor(145, 151, 164)), self)
        self.tray.setToolTip(
            tr(
                f"{APP_NAME} — загрузка модели",
                f"{APP_NAME} — loading model",
            )
        )
        self.tray_menu = QMenu()
        self.status_action = QAction(
            tr("Загрузка модели…", "Loading model…"),
            self.tray_menu,
        )
        self.status_action.setEnabled(False)
        self.tray_menu.addAction(self.status_action)
        self.tray_menu.addSeparator()
        self.settings_action = QAction(
            tr("Настройки…", "Settings…"),
            self.tray_menu,
        )
        self.settings_action.triggered.connect(self._queue_settings)
        self.tray_menu.addAction(self.settings_action)
        self.tray_menu.addSeparator()
        self.quit_action = QAction(tr("Выход", "Exit"), self.tray_menu)
        self.quit_action.triggered.connect(self.quit)
        self.tray_menu.addAction(self.quit_action)
        self.tray.setContextMenu(self.tray_menu)
        self.tray.show()

        self._load_model_async()

    def _configure_hotkey(self) -> None:
        for key_poller in self.key_pollers:
            key_poller.stop()
        for keyboard_hook in self.keyboard_hooks:
            keyboard_hook.stop()
        self.key_pollers.clear()
        self.keyboard_hooks.clear()

        hotkey_name = str(self.config.get("hotkey", "right_alt")).lower()
        if hotkey_name not in VK_CODES:
            hotkey_name = "right_alt"
            self.config["hotkey"] = hotkey_name
        translation_hotkey_name = str(
            self.config.get("translation_hotkey", "right_ctrl")
        ).lower()
        if (
            translation_hotkey_name not in VK_CODES
            or translation_hotkey_name == hotkey_name
        ):
            translation_hotkey_name = (
                "right_ctrl" if hotkey_name != "right_ctrl" else "f12"
            )
            self.config["translation_hotkey"] = translation_hotkey_name

        hotkey_labels = HOTKEY_LABELS.get(hotkey_name)
        translation_hotkey_labels = HOTKEY_LABELS.get(
            translation_hotkey_name
        )
        self.hotkey_label = (
            localized_label(hotkey_labels)
            if hotkey_labels is not None
            else hotkey_name.upper()
        )
        self.translation_hotkey_label = (
            localized_label(translation_hotkey_labels)
            if translation_hotkey_labels is not None
            else translation_hotkey_name.upper()
        )
        self.overlay.hotkey_label = self.hotkey_label

        for key_name, mode in (
            (hotkey_name, "transcribe"),
            (translation_hotkey_name, "translate"),
        ):
            vk_code = VK_CODES[key_name]
            keyboard_hook = KeyboardHook(vk_code)
            keyboard_hook.pressed.connect(
                lambda active_mode=mode: self.begin_recording(active_mode)
            )
            keyboard_hook.released.connect(
                lambda active_mode=mode: self.finish_recording(active_mode)
            )
            keyboard_hook.failed.connect(self.show_error)
            key_poller = KeyStatePoller(vk_code)
            key_poller.pressed.connect(
                lambda active_mode=mode: self.begin_recording(active_mode)
            )
            key_poller.released.connect(
                lambda active_mode=mode: self.finish_recording(active_mode)
            )
            self.keyboard_hooks.append(keyboard_hook)
            self.key_pollers.append(key_poller)
            keyboard_hook.start()
            key_poller.start()

        log_message(
            "Hotkeys configured: "
            f"transcribe={hotkey_name}, translate={translation_hotkey_name}"
        )

    def _queue_settings(self) -> None:
        log_message("Settings requested from tray")
        # Native Windows tray menus can still own the foreground window for a
        # short moment after QAction.triggered. Opening the dialog immediately
        # can therefore put it behind the user's current application.
        QTimer.singleShot(150, self.show_settings)

    def show_settings(self) -> None:
        if self.state in {"recording", "transcribing"}:
            self.tray.showMessage(
                APP_NAME,
                tr(
                    "Дождитесь завершения текущей диктовки.",
                    "Wait for the current dictation to finish.",
                ),
                QSystemTrayIcon.MessageIcon.Information,
                1800,
            )
            return
        if self.settings_dialog is not None:
            self._activate_settings_dialog()
            return
        log_message("Opening settings dialog")
        self.settings_dialog = SettingsDialog(self.config)
        self.settings_dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.settings_dialog.settings_saved.connect(self._apply_settings)
        self.settings_dialog.finished.connect(self._settings_dialog_finished)
        self.settings_dialog.show()
        self._activate_settings_dialog()
        QTimer.singleShot(250, self._activate_settings_dialog)

    def _activate_settings_dialog(self) -> None:
        dialog = self.settings_dialog
        if dialog is None:
            return
        dialog.showNormal()
        dialog.raise_()
        dialog.activateWindow()
        window_handle = int(dialog.winId())
        user32.ShowWindow(window_handle, SW_RESTORE)
        user32.BringWindowToTop(window_handle)
        focused = bool(user32.SetForegroundWindow(window_handle))
        log_message(
            f"Settings activation requested: hwnd={window_handle}, "
            f"foreground={focused}"
        )

    def _settings_dialog_finished(self, _result: int) -> None:
        if self.settings_dialog is not None:
            self.settings_dialog.deleteLater()
            self.settings_dialog = None
        log_message("Settings dialog closed")

    def _apply_settings(self, updated: object) -> None:
        new_config = dict(updated)  # type: ignore[arg-type]
        previous_model_id = normalized_model_id(
            self.config.get("model_id")
        )
        previous_model_path = str(self.config.get("model_path", ""))
        model_changed = normalized_model_id(
            new_config.get("model_id")
        ) != previous_model_id
        hotkey_changed = any(
            new_config.get(key) != self.config.get(key)
            for key in ("hotkey", "translation_hotkey")
        )
        self.config = new_config
        self.recorder.microphone = self.config.get("microphone")
        self.recorder.max_seconds = float(
            self.config.get("max_recording_seconds", 300)
        )
        self.overlay.position = str(
            self.config.get("overlay_position", "bottom_center")
        )
        self.overlay.animation_style = str(
            self.config.get("animation_style", "live_ball")
        )
        if hotkey_changed:
            self._configure_hotkey()
        self.tray.setToolTip(
            tr(
                f"{APP_NAME} — текст: {self.hotkey_label}; перевод: "
                f"{self.translation_hotkey_label}",
                f"{APP_NAME} — dictation: {self.hotkey_label}; translation: "
                f"{self.translation_hotkey_label}",
            )
        )
        self.tray.showMessage(
            tr("Настройки сохранены", "Settings saved"),
            tr(
                f"Текст: {self.hotkey_label}. Перевод: "
                f"{self.translation_hotkey_label}.",
                f"Dictation: {self.hotkey_label}. Translation: "
                f"{self.translation_hotkey_label}.",
            ),
            QSystemTrayIcon.MessageIcon.Information,
            1800,
        )
        if model_changed:
            QTimer.singleShot(
                250,
                lambda: self._change_whisper_model(
                    previous_model_id,
                    previous_model_path,
                ),
            )

    def _change_whisper_model(
        self,
        previous_model_id: str,
        previous_model_path: str,
    ) -> None:
        selected_model_id = normalized_model_id(
            self.config.get("model_id")
        )
        selected_path = Path(str(self.config.get("model_path", "")))
        self.state = "loading"
        self.status_action.setText(
            tr("Подготовка модели…", "Preparing model…")
        )

        if not whisper_model_available(
            selected_path,
            selected_model_id,
        ):
            component_dialog = ComponentSetupDialog(
                self.config,
                requested_model_id=selected_model_id,
                force_model=True,
            )
            if component_dialog.exec() != QDialog.DialogCode.Accepted:
                self.config["model_id"] = previous_model_id
                self.config["model_path"] = previous_model_path
                save_config(self.config)
                self.state = "ready"
                self.status_action.setText(
                    f"{tr('Готово', 'Ready')} · "
                    f"{self.active_device}/{self.active_compute_type}"
                )
                return
            self.config = load_config()

        old_model = self.model
        self.model = None
        del old_model
        gc.collect()
        self.tray.setIcon(make_tray_icon(QColor(145, 151, 164)))
        self.status_action.setText(
            tr("Загрузка выбранной модели…", "Loading selected model…")
        )
        self._load_model_async()

    def _load_model_async(self) -> None:
        worker = FunctionWorker(self._load_model)
        worker.signals.succeeded.connect(self._model_loaded)
        worker.signals.failed.connect(self._model_failed)
        self.thread_pool.start(worker)

    def _load_model(self) -> tuple[Any, str, str]:
        from faster_whisper import WhisperModel
        import ctranslate2

        model_path = Path(str(self.config["model_path"]))
        if not model_path.is_dir():
            raise FileNotFoundError(
                tr(
                    f"Модель не найдена: {model_path}",
                    f"Model not found: {model_path}",
                )
            )

        configured_device = str(self.config.get("device", "auto")).lower()
        if configured_device == "auto":
            has_usable_cuda = ctranslate2.get_cuda_device_count() > 0 and cuda_runtime_available()
            device = "cuda" if has_usable_cuda else "cpu"
        else:
            device = configured_device

        configured_compute = str(self.config.get("compute_type", "auto")).lower()
        if configured_compute == "auto":
            compute_type = "float16" if device == "cuda" else "int8"
        else:
            compute_type = configured_compute

        model = WhisperModel(str(model_path), device=device, compute_type=compute_type)
        return model, device, compute_type

    def _model_loaded(self, result: object) -> None:
        self.model, device, compute_type = result  # type: ignore[misc]
        self.active_device = device
        self.active_compute_type = compute_type
        log_message(f"Model loaded: device={device}, compute_type={compute_type}")
        self.state = "ready"
        self.status_action.setText(
            f"{tr('Готово', 'Ready')} · {device}/{compute_type}"
        )
        self.tray.setToolTip(
            tr(
                f"{APP_NAME} — текст: {self.hotkey_label}; перевод: "
                f"{self.translation_hotkey_label}",
                f"{APP_NAME} — dictation: {self.hotkey_label}; translation: "
                f"{self.translation_hotkey_label}",
            )
        )
        self.tray.setIcon(make_tray_icon(QColor(57, 208, 132)))
        self.tray.showMessage(
            tr(f"{APP_NAME} готов", f"{APP_NAME} is ready"),
            tr(
                f"Текст: {self.hotkey_label}. Перевод: "
                f"{self.translation_hotkey_label}.",
                f"Dictation: {self.hotkey_label}. Translation: "
                f"{self.translation_hotkey_label}.",
            ),
            QSystemTrayIcon.MessageIcon.Information,
            2500,
        )

    def _model_failed(self, details: str) -> None:
        log_message(f"Model loading failed:\n{details}")
        self.model_error = details
        self.state = "error"
        self.status_action.setText(
            tr("Ошибка загрузки модели", "Model loading error")
        )
        self.tray.setIcon(make_tray_icon(QColor(245, 91, 91)))
        self.show_error(
            tr(
                "Не удалось загрузить Whisper. Подробности выведены в консоль.",
                "Could not load Whisper. Details were written to the console.",
            )
        )
        print(details, file=sys.stderr)

    def begin_recording(self, mode: str = "transcribe") -> None:
        if self.state != "ready":
            if self.state == "loading":
                self.tray.showMessage(
                    APP_NAME,
                    tr("Модель ещё загружается", "The model is still loading"),
                    QSystemTrayIcon.MessageIcon.Information,
                    1200,
                )
            return
        try:
            self.recording_mode = mode
            self.overlay.hotkey_label = (
                self.translation_hotkey_label
                if mode == "translate"
                else self.hotkey_label
            )
            self.foreground_window = user32.GetForegroundWindow()
            self.recorder.start()
        except Exception as exc:
            self.show_error(
                tr(
                    f"Не удалось включить микрофон: {exc}",
                    f"Could not enable the microphone: {exc}",
                )
            )
            return
        print(f"recording-started sample_rate={self.recorder.sample_rate}", flush=True)
        log_message(
            f"Recording started: mode={mode}, "
            f"sample_rate={self.recorder.sample_rate}"
        )
        self.state = "recording"
        self.overlay.set_level(0.0)
        self.overlay.show_for_state("listening")
        self.tray.setIcon(make_tray_icon(QColor(57, 208, 132)))

    def finish_recording(self, mode: str | None = None) -> None:
        if self.state != "recording":
            return
        if mode is not None and mode != self.recording_mode:
            return
        try:
            audio, sample_rate, duration = self.recorder.stop()
        except Exception as exc:
            self.state = "ready"
            self.show_error(
                tr(
                    f"Не удалось завершить запись: {exc}",
                    f"Could not finish recording: {exc}",
                )
            )
            return
        print(f"recording-stopped duration={duration:.2f}s samples={audio.size}", flush=True)
        log_message(
            f"Recording stopped: mode={self.recording_mode}, "
            f"duration={duration:.2f}s, samples={audio.size}"
        )

        if duration < float(self.config["min_recording_seconds"]) or audio.size == 0:
            self.state = "ready"
            self.overlay.hide()
            return

        self.state = "transcribing"
        self.overlay.show_for_state("transcribing")
        worker = FunctionWorker(
            self._process_audio,
            audio,
            sample_rate,
            self.recording_mode,
        )
        worker.signals.succeeded.connect(self._transcription_ready)
        worker.signals.failed.connect(self._transcription_failed)
        self.thread_pool.start(worker)

    @staticmethod
    def _resample(audio: np.ndarray, source_rate: int, target_rate: int = 16000) -> np.ndarray:
        if source_rate == target_rate or audio.size == 0:
            return np.asarray(audio, dtype=np.float32)
        target_length = max(1, round(audio.size * target_rate / source_rate))
        source_positions = np.arange(audio.size, dtype=np.float64)
        target_positions = np.linspace(0, audio.size - 1, target_length)
        return np.interp(target_positions, source_positions, audio).astype(np.float32)

    def _transcribe(
        self,
        audio: np.ndarray,
        sample_rate: int,
        task: str = "transcribe",
    ) -> tuple[str, str]:
        if self.model is None:
            raise RuntimeError(tr("Модель не загружена", "Model is not loaded"))
        audio_16k = self._resample(audio, sample_rate)
        language = self.config.get("language") or None

        def transcribe_with(model: Any) -> tuple[str, str]:
            segments, info = model.transcribe(
                audio_16k,
                language=language,
                task=task,
                beam_size=3,
                vad_filter=True,
                condition_on_previous_text=False,
            )
            text = " ".join(
                segment.text.strip() for segment in segments if segment.text.strip()
            ).strip()
            detected_language = str(
                language or getattr(info, "language", "") or "ru"
            ).lower()
            return text, detected_language

        try:
            return transcribe_with(self.model)
        except RuntimeError as exc:
            error_text = str(exc).lower()
            if self.active_device != "cuda" or not any(
                marker in error_text for marker in ("cublas", "cudnn", "cuda")
            ):
                raise
            print("CUDA runtime is incomplete; falling back to CPU/int8", flush=True)
            from faster_whisper import WhisperModel

            self.model = WhisperModel(
                str(self.config["model_path"]),
                device="cpu",
                compute_type="int8",
            )
            self.active_device = "cpu"
            self.active_compute_type = "int8"
            return transcribe_with(self.model)

    def _process_audio(
        self,
        audio: np.ndarray,
        sample_rate: int,
        mode: str,
    ) -> dict[str, Any]:
        task = "translate" if mode == "translate" else "transcribe"
        text, source_language = self._transcribe(
            audio,
            sample_rate,
            task=task,
        )
        return {
            "text": text,
            "source_text": text,
            "source_language": source_language,
            "translated": mode == "translate" and bool(text),
            "target_language": "en" if mode == "translate" else "",
        }

    def _transcription_ready(self, result: object) -> None:
        self.status_action.setText(
            f"{tr('Готово', 'Ready')} · "
            f"{self.active_device}/{self.active_compute_type}"
        )
        processed = dict(result)  # type: ignore[arg-type]
        text = str(processed.get("text", "")).strip()
        print(f"transcription-ready characters={len(text)}", flush=True)
        log_message(
            f"Processing ready: characters={len(text)}, "
            f"translated={processed.get('translated', False)}, "
            f"source={processed.get('source_language', '')}, "
            f"target={processed.get('target_language', '')}"
        )
        if not text:
            self.state = "ready"
            self.overlay.show_for_state(
                "error",
                tr("Речь не распознана", "Speech was not recognized"),
            )
            QTimer.singleShot(1200, self.overlay.hide)
            return
        try:
            self._paste_text(text)
        except Exception as exc:
            print(f"paste-failed: {exc!r}", file=sys.stderr, flush=True)
            log_message(f"Paste failed: {exc!r}")
            self.show_error(
                tr(
                    f"Не удалось вставить текст: {exc}",
                    f"Could not paste text: {exc}",
                )
            )
            return
        self.state = "ready"
        self.overlay.show_for_state("success")
        QTimer.singleShot(650, self.overlay.hide)

    def _transcription_failed(self, details: str) -> None:
        log_message(f"Transcription failed:\n{details}")
        print(details, file=sys.stderr)
        self.state = "ready"
        self.show_error(
            tr(
                "Ошибка распознавания. Подробности выведены в консоль.",
                "Recognition error. Details were written to the console.",
            )
        )

    @staticmethod
    def _clone_mime_data(source: QMimeData) -> QMimeData:
        clone = QMimeData()
        for mime_format in source.formats():
            clone.setData(mime_format, QByteArray(source.data(mime_format)))
        return clone

    def _paste_text(self, text: str) -> None:
        clipboard = QApplication.clipboard()
        previous = self._clone_mime_data(clipboard.mimeData())
        clipboard.setText(text)
        if self.foreground_window:
            user32.SetForegroundWindow(self.foreground_window)

        inputs = (INPUT * 4)(
            INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(VK_CONTROL, 0, 0, 0, 0)),
            INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(VK_V, 0, 0, 0, 0)),
            INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(VK_V, 0, KEYEVENTF_KEYUP, 0, 0)),
            INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0, 0)),
        )
        sent = user32.SendInput(4, inputs, ctypes.sizeof(INPUT))
        if sent != 4:
            raise OSError(
                tr(
                    "Windows не разрешила отправить Ctrl+V",
                    "Windows did not allow Ctrl+V to be sent",
                )
            )

        delay = int(self.config.get("paste_restore_delay_ms", 700))
        QTimer.singleShot(delay, lambda: clipboard.setMimeData(previous))

    def show_error(self, message: str) -> None:
        log_message(f"Application error: {message}")
        if self.recorder.is_recording:
            try:
                self.recorder.stop()
            except Exception:
                pass
        if self.state != "loading":
            self.state = "ready" if self.model is not None else "error"
        self.overlay.show_for_state("error")
        QTimer.singleShot(1800, self.overlay.hide)
        self.tray.showMessage(
            tr(f"{APP_NAME} — ошибка", f"{APP_NAME} — error"),
            message,
            QSystemTrayIcon.MessageIcon.Critical,
            3500,
        )

    def quit(self) -> None:
        for key_poller in self.key_pollers:
            key_poller.stop()
        for keyboard_hook in self.keyboard_hooks:
            keyboard_hook.stop()
        if self.recorder.is_recording:
            self.recorder.stop()
        self.tray.hide()
        self.qt_app.quit()


def main() -> int:
    if sys.platform != "win32":
        print(
            tr(
                "Это приложение предназначено для Windows.",
                "This application is intended for Windows.",
            ),
            file=sys.stderr,
        )
        return 1
    configure_cuda_runtime()
    qt_app = QApplication(sys.argv)
    qt_app.setApplicationName(APP_NAME)
    qt_app.setQuitOnLastWindowClosed(False)
    qt_app.setWindowIcon(qt_app.style().standardIcon(QStyle.StandardPixmap.SP_MediaVolume))

    mutexes: list[int] = []
    for mutex_name in (
        "Local\\KeyUpVoiceInput",
        "Local\\GolosVoiceInput",
    ):
        mutex = kernel32.CreateMutexW(None, False, mutex_name)
        already_running = kernel32.GetLastError() == 183
        if mutex:
            mutexes.append(mutex)
        if already_running:
            for handle in mutexes:
                kernel32.CloseHandle(handle)
            return 0

    config = load_config()
    interface_language = installed_interface_language()
    set_interface_language(interface_language)
    config["interface_language"] = interface_language
    configured_model_id = normalized_model_id(config.get("model_id"))
    config["model_id"] = configured_model_id
    configured_model_path = Path(str(config.get("model_path", "")))
    selected_installed_path = installed_model_path(configured_model_id)
    if whisper_model_available(
        selected_installed_path,
        configured_model_id,
    ):
        config["model_path"] = str(selected_installed_path)
        configured_model_path = selected_installed_path
    save_config(config)
    force_component_setup = "--setup-components" in sys.argv
    needs_model = not whisper_model_available(
        configured_model_path,
        configured_model_id,
    )
    needs_cuda = has_nvidia_gpu() and not cuda_runtime_available()
    if force_component_setup or needs_model or needs_cuda:
        component_dialog = ComponentSetupDialog(
            config,
            requested_model_id=configured_model_id,
            force_model=force_component_setup,
        )
        if component_dialog.exec() != QDialog.DialogCode.Accepted:
            for handle in mutexes:
                kernel32.CloseHandle(handle)
            return 0
        configure_cuda_runtime()

    voice_app = VoiceApp(qt_app)
    result = qt_app.exec()
    for handle in mutexes:
        kernel32.CloseHandle(handle)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
