from __future__ import annotations

import csv
from pathlib import Path

from expandr.models import Folder, Library, Snippet, TriggerMode, new_id


def export_csv(library: Library, path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["folder", "label", "shortcut", "content"])
        for folder, snippet in library.all_snippets():
            writer.writerow([folder.name, snippet.label, snippet.shortcut, snippet.content])


def import_csv(library: Library, path: Path) -> int:
    added = 0
    folders = {folder.name.casefold(): folder for folder in library.folders}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            folder_name = (row.get("folder") or "Imported").strip() or "Imported"
            key = folder_name.casefold()
            folder = folders.get(key)
            if folder is None:
                folder = Folder(id=new_id(), name=folder_name, trigger=TriggerMode.WORD_START)
                library.folders.append(folder)
                folders[key] = folder
            folder.snippets.append(
                Snippet(
                    id=new_id(),
                    label=(row.get("label") or "Untitled").strip() or "Untitled",
                    shortcut=(row.get("shortcut") or "").strip(),
                    content=row.get("content") or "",
                )
            )
            added += 1
    return added
