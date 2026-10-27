"""Read-only stable-release checks; never downloads or executes installers."""
import json
import re
import urllib.error

from model_sources import read_url

RELEASES_URL = "https://github.com/LexGilden/KeyUp-Voice/releases"
LATEST_API = "https://api.github.com/repos/LexGilden/KeyUp-Voice/releases/latest"


def version_tuple(value: str) -> tuple[int, int, int]:
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", value)
    if not match:
        raise ValueError("Expected a stable major.minor.patch version")
    return tuple(int(part) for part in match.groups())


def newer_release(payload: dict, current: str) -> dict | None:
    if payload.get("draft") or payload.get("prerelease"):
        return None
    tag = str(payload.get("tag_name", ""))
    try:
        newer = version_tuple(tag) > version_tuple(current)
    except ValueError:
        return None
    if not newer:
        return None
    return {"version": tag.lstrip("v"), "notes": str(payload.get("body") or "")[:16000],
            "url": RELEASES_URL}


def check_release(current: str) -> dict | None:
    try:
        data = read_url(LATEST_API, headers={"Accept": "application/vnd.github+json"})
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise
    return newer_release(json.loads(data), current)
