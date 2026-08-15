from __future__ import annotations

from expandr.models import Library, Snippet, TriggerMode, shortcut_is_armed

WORD_BREAKS = set(" \t\r\n.,;:!?()[]{}\"'<>|")


def _before_ok(prefix: str, mode: TriggerMode) -> bool:
    if mode == TriggerMode.ANYWHERE:
        return True
    return (not prefix) or prefix[-1] in WORD_BREAKS


def find_matches(buffer: str, library: Library) -> list[tuple[Snippet, int, str]]:
    """Return (snippet, delete_count, suffix_to_retype) for expansions that are ready now."""
    ready: list[tuple[Snippet, int, str]] = []
    folded = buffer.casefold()
    for folder, snippet in library.all_snippets():
        shortcut = snippet.shortcut
        if not snippet.enabled or not shortcut_is_armed(shortcut):
            continue
        sc = shortcut.casefold()
        if folder.trigger == TriggerMode.WORD_BOUNDED:
            if len(buffer) < len(shortcut) + 1:
                continue
            if buffer[-1] not in WORD_BREAKS:
                continue
            if not folded[:-1].endswith(sc):
                continue
            prefix = buffer[: -(len(shortcut) + 1)]
            if not _before_ok(prefix, TriggerMode.WORD_START):
                continue
            ready.append((snippet, len(shortcut) + 1, buffer[-1]))
            continue
        if not folded.endswith(sc):
            continue
        prefix = buffer[: -len(shortcut)]
        if not _before_ok(prefix, folder.trigger):
            continue
        ready.append((snippet, len(shortcut), ""))
    ready.sort(key=lambda item: len(item[0].shortcut), reverse=True)
    return ready


def has_longer_prefix(buffer: str, library: Library) -> bool:
    folded = buffer.casefold()
    for folder, snippet in library.all_snippets():
        if not snippet.enabled or not shortcut_is_armed(snippet.shortcut):
            continue
        sc = snippet.shortcut.casefold()
        for i in range(len(folded)):
            tail = folded[i:]
            if sc.startswith(tail) and len(sc) > len(tail):
                prefix = buffer[:i]
                if _before_ok(prefix, folder.trigger):
                    return True
    return False
