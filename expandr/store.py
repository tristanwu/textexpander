from __future__ import annotations

import json
import os
from pathlib import Path

from expandr.defaults import default_library
from expandr.models import Library


APP_NAME = "Expandr"


def data_dir() -> Path:
    root = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    path = Path(root) / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def library_path() -> Path:
    return data_dir() / "library.json"


def load_library() -> Library:
    path = library_path()
    if not path.exists():
        library = default_library()
        save_library(library)
        return library
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default_library()
    return Library.from_dict(data)


def save_library(library: Library) -> None:
    path = library_path()
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(library.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)
