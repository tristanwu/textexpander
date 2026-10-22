from __future__ import annotations

from expandr.models import Folder, Library, Snippet


def snippet_row_text(snippet: Snippet) -> str:
    shortcut = (snippet.shortcut or "").strip() or "(no shortcut)"
    label = (snippet.label or "").strip()
    if not label or label.casefold() == "untitled":
        return shortcut
    return f"{shortcut}    {label}"


def folders_for_list(library: Library, query: str) -> list[tuple[Folder, list[Snippet]]]:
    needle = (query or "").strip().casefold()
    groups: list[tuple[Folder, list[Snippet]]] = []
    for folder in library.folders:
        rows = [
            snippet
            for snippet in folder.snippets
            if not needle or needle in f"{snippet.label} {snippet.shortcut} {folder.name}".casefold()
        ]
        if rows:
            groups.append((folder, rows))
    return groups
