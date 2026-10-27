"""Pinned, data-only Hugging Face Whisper model manifests."""
from __future__ import annotations

import hashlib
import json
import re
import struct
import urllib.request
from pathlib import Path

ALLOWED_FILES = {"config.json", "model.bin", "tokenizer.json",
                 "preprocessor_config.json", "vocabulary.json", "vocabulary.txt"}
REQUIRED_FILES = {"config.json", "model.bin", "tokenizer.json"}


def repository_id(value: str) -> str:
    value = value.strip()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*", value):
        raise ValueError("Expected a public Hugging Face repository: owner/model")
    if ".." in value or "--" in value or value.endswith((".", ".git")):
        raise ValueError("Invalid Hugging Face repository ID")
    return value


def read_url(url: str, limit: int = 8 * 1024 * 1024, headers: dict | None = None) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "KeyUp-Voice", **(headers or {})})
    with urllib.request.urlopen(request, timeout=20) as response:
        data = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError("Response is larger than expected")
    return data


def custom_id(spec: dict) -> str:
    identity = ("local:" + str(Path(spec["local_path"])).casefold()
                if spec.get("local_path") else spec["repository"] + "@" + spec["revision"])
    return "custom-" + hashlib.sha256(identity.encode()).hexdigest()[:24]


def model_labels(spec: dict) -> list[str]:
    if spec.get("local_path"):
        name = Path(spec["local_path"]).name
        return [name + " — локальная", name + " — local"]
    return [spec["repository"], spec["repository"]]


def validate_manifest(spec: dict) -> dict:
    if not isinstance(spec, dict):
        raise ValueError("Invalid model manifest")
    if "local_path" in spec:
        if not isinstance(spec["local_path"], str) or not Path(spec["local_path"]).is_absolute():
            raise ValueError("Local model path must be absolute")
    else:
        repository_id(spec["repository"])
        if not re.fullmatch(r"[a-f0-9]{40}", spec["revision"]):
            raise ValueError("Model revision must be a pinned commit")
    files = spec["files"]
    if not isinstance(files, dict):
        raise ValueError("Invalid file manifest")
    if not REQUIRED_FILES <= files.keys() or not files.keys() <= ALLOWED_FILES:
        raise ValueError("Not a supported CTranslate2 Whisper model")
    if not ({"vocabulary.json", "vocabulary.txt"} & files.keys()):
        raise ValueError("Missing vocabulary")
    for name, (size, digest) in files.items():
        if not isinstance(size, int) or size <= 0 or not re.fullmatch(r"[a-f0-9]{64}", digest):
            raise ValueError("Invalid file manifest: " + name)
    if not isinstance(spec.get("translation"), bool):
        raise ValueError("Missing model capabilities")
    return spec


def validate_whisper_header(header: bytes) -> None:
    if len(header) < 10:
        raise ValueError("Invalid CTranslate2 model header")
    version, length = struct.unpack_from("<IH", header)
    if version < 2 or length > 128 or header[6:6 + length].rstrip(b"\0") != b"WhisperSpec":
        raise ValueError("This is not a CTranslate2 Whisper model")


def inspect_local_directory(value: str) -> dict:
    folder = Path(value).resolve(strict=True)
    with (folder / "model.bin").open("rb") as source:
        validate_whisper_header(source.read(256))
    with (folder / "config.json").open("rb") as source:
        data = source.read(16 * 1024 * 1024 + 1)
    if len(data) > 16 * 1024 * 1024:
        raise ValueError("Model configuration is too large")
    config = json.loads(data)
    if not isinstance(config, dict) or "suppress_ids" not in config:
        raise ValueError("Unsupported Whisper configuration")
    files = {}
    for name in sorted(ALLOWED_FILES):
        path = folder / name
        if not path.is_file():
            continue
        digest = hashlib.sha256()
        size = 0
        with path.open("rb") as source:
            while chunk := source.read(4 * 1024 * 1024):
                digest.update(chunk)
                size += len(chunk)
        files[name] = (size, digest.hexdigest())
    spec = {"local_path": str(folder), "files": files, "custom": True,
            "translation": False, "license": "See local model files"}
    spec["labels"] = model_labels(spec)
    return validate_manifest(spec)


def inspect_repository(value: str) -> dict:
    repo = repository_id(value)
    meta = json.loads(read_url(f"https://huggingface.co/api/models/{repo}?blobs=true"))
    if meta.get("private") or meta.get("gated"):
        raise ValueError("Only public models without access approval are supported")
    revision = meta["sha"]
    if not re.fullmatch(r"[a-f0-9]{40}", revision):
        raise ValueError("Invalid repository revision")
    entries = {f["rfilename"]: f for f in meta["siblings"] if f["rfilename"] in ALLOWED_FILES}
    if not REQUIRED_FILES <= entries.keys():
        raise ValueError("Expected CTranslate2 Whisper files: model.bin, config.json, tokenizer.json")
    base = f"https://huggingface.co/{repo}/resolve/{revision}/"
    # Read only the binary header, never download weights during inspection.
    with urllib.request.urlopen(urllib.request.Request(base + "model.bin", headers={"Range": "bytes=0-255"}), timeout=20) as response:
        header = response.read(256)
    validate_whisper_header(header)
    files, documents = {}, {}
    for name, entry in entries.items():
        size = int(entry["size"])
        digest = (entry.get("lfs") or {}).get("sha256")
        if name != "model.bin":
            data = read_url(base + name, limit=16 * 1024 * 1024)
            if len(data) != size:
                raise ValueError("File size mismatch: " + name)
            digest = hashlib.sha256(data).hexdigest()
            if name in {"config.json", "preprocessor_config.json"}:
                documents[name] = json.loads(data)
        if not digest:
            raise ValueError("Missing SHA-256 for " + name)
        files[name] = (size, digest)
    config = documents["config.json"]
    if not isinstance(config, dict) or "suppress_ids" not in config:
        raise ValueError("Unsupported Whisper configuration")
    # Fine-tunes do not reliably declare translation support. Default to dictation.
    card = meta.get("cardData") or {}
    base_model = str(card.get("base_model", ""))
    turbo = "turbo" in (repo + " " + base_model).lower()
    spec = {"repository": repo, "revision": revision, "files": files,
            "labels": [repo, repo], "custom": True, "translation": False,
            "turbo": turbo, "license": str(card.get("license", "unknown"))}
    return validate_manifest(spec)


def load_catalog(path: Path) -> dict:
    if not path.exists():
        return {}
    entries = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(entries, dict):
        raise ValueError("Invalid custom model catalog")
    result = {}
    for key, spec in entries.items():
        validate_manifest(spec)
        if key != custom_id(spec):
            raise ValueError("Invalid custom model ID")
        spec["labels"] = model_labels(spec)
        spec["custom"] = True
        result[key] = spec
    return result


def save_catalog(path: Path, catalog: dict) -> None:
    entries = {key: validate_manifest(spec) for key, spec in catalog.items() if spec.get("custom")}
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)
