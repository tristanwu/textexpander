from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from expandr.defaults import default_library
from expandr.identity import APP_NAME, LEGACY_APP_NAME
from expandr.models import Library


def _appdata() -> Path:
    root = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    return Path(root)


def data_dir() -> Path:
    root = _appdata()
    current = root / APP_NAME
    legacy = root / LEGACY_APP_NAME
    if not current.exists() and legacy.exists():
        legacy.rename(current)
    current.mkdir(parents=True, exist_ok=True)
    return current


def library_path() -> Path:
    return data_dir() / "library.json"


@dataclass(frozen=True)
class LoadResult:
    library: Library
    quarantined: Path | None = None


def _quarantine_library(path: Path) -> Path:
    dest = path.with_name("library.json.corrupt")
    if dest.exists():
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        dest = path.with_name(f"library.json.corrupt.{stamp}")
    path.replace(dest)
    return dest


def load_library() -> LoadResult:
    path = library_path()
    if not path.exists():
        library = default_library()
        save_library(library)
        return LoadResult(library)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("library is not an object")
        library = Library.from_dict(data)
    except (OSError, json.JSONDecodeError, TypeError, ValueError, AttributeError, KeyError):
        try:
            quarantined = _quarantine_library(path)
        except OSError:
            return LoadResult(default_library())
        library = default_library()
        save_library(library)
        return LoadResult(library, quarantined=quarantined)
    return LoadResult(library)


def save_library(library: Library) -> None:
    path = library_path()
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(library.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)
