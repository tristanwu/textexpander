from __future__ import annotations

import re

DEFAULT_SKIP_APPS = [
    "keepass.exe",
    "keepassxc.exe",
    "1password.exe",
    "bitwarden.exe",
    "dashlane.exe",
    "textexpander.exe",
    "pythonw.exe",
    "python.exe",
]

_TOKEN = re.compile(r"\b(?:sk-[A-Za-z0-9]{10,}|ghp_[A-Za-z0-9]{10,}|AKIA[A-Z0-9]{8,})\b")


def default_skip_apps() -> list[str]:
    return list(DEFAULT_SKIP_APPS)


def should_record(app: str, skip_apps: list[str], *, live: bool, paused: bool) -> bool:
    if not live or paused:
        return False
    name = (app or "").casefold()
    blocked = {item.strip().casefold() for item in skip_apps if item and item.strip()}
    return name not in blocked


def mask_secrets(text: str) -> str:
    return _TOKEN.sub("[hidden]", text or "")
