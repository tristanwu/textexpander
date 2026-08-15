from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from expandr.models import Library

BUNDLE_FORMAT = "expandr-library"
BUNDLE_VERSION = 1


class TransferError(ValueError):
    pass


@dataclass(frozen=True)
class ImportResult:
    snippets: int
    folders: int
    replaced: bool


def export_bundle(library: Library, path: Path) -> None:
    payload = {
        "format": BUNDLE_FORMAT,
        "version": BUNDLE_VERSION,
        "library": library.to_dict(),
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def read_bundle(path: Path) -> Library:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TransferError("Could not read a TextExpander library file.") from exc
    if not isinstance(data, dict):
        raise TransferError("Could not read a TextExpander library file.")
    if data.get("format") == BUNDLE_FORMAT:
        inner = data.get("library")
        if not isinstance(inner, dict) or "folders" not in inner:
            raise TransferError("This file is not a complete TextExpander library.")
        return Library.from_dict(inner)
    if "folders" in data:
        return Library.from_dict(data)
    raise TransferError("This file is not a TextExpander library.")


def import_bundle(dest: Library, path: Path, *, merge: bool) -> ImportResult:
    incoming = read_bundle(path)
    if merge:
        dest.merge_from(incoming)
    else:
        dest.replace_from(incoming)
    return ImportResult(
        snippets=dest.snippet_count(),
        folders=len(dest.folders),
        replaced=not merge,
    )
