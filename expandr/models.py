from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal
from uuid import uuid4


class TriggerMode(str, Enum):
    WORD_START = "word_start"
    WORD_BOUNDED = "word_bounded"
    ANYWHERE = "anywhere"


def new_id() -> str:
    return uuid4().hex


@dataclass
class Snippet:
    id: str
    label: str
    shortcut: str
    content: str
    enabled: bool = True

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "shortcut": self.shortcut,
            "content": self.content,
            "enabled": self.enabled,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Snippet:
        return cls(
            id=data.get("id") or new_id(),
            label=data.get("label") or "Untitled",
            shortcut=data.get("shortcut") or "",
            content=data.get("content") or "",
            enabled=data.get("enabled", True),
        )


@dataclass
class Folder:
    id: str
    name: str
    trigger: TriggerMode = TriggerMode.WORD_START
    snippets: list[Snippet] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "trigger": self.trigger.value,
            "snippets": [s.to_dict() for s in self.snippets],
        }

    @classmethod
    def from_dict(cls, data: dict) -> Folder:
        trigger_raw = data.get("trigger") or TriggerMode.WORD_START.value
        try:
            trigger = TriggerMode(trigger_raw)
        except ValueError:
            trigger = TriggerMode.WORD_START
        return cls(
            id=data.get("id") or new_id(),
            name=data.get("name") or "Folder",
            trigger=trigger,
            snippets=[Snippet.from_dict(s) for s in data.get("snippets") or []],
        )


def shortcut_is_armed(shortcut: str) -> bool:
    """A shortcut must be 2+ characters so `/` alone cannot fire globally."""
    return len((shortcut or "").strip()) >= 2


@dataclass
class Settings:
    search_hotkey: str = "ctrl+shift+/"
    pause_hotkey: str = "ctrl+shift+p"
    paused: bool = False
    start_with_windows: bool = False
    seen_coach: bool = False
    disabled_apps: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "search_hotkey": self.search_hotkey,
            "pause_hotkey": self.pause_hotkey,
            "paused": self.paused,
            "start_with_windows": self.start_with_windows,
            "seen_coach": self.seen_coach,
            "disabled_apps": list(self.disabled_apps),
        }

    @classmethod
    def from_dict(cls, data: dict) -> Settings:
        return cls(
            search_hotkey=data.get("search_hotkey") or "ctrl+shift+/",
            pause_hotkey=data.get("pause_hotkey") or "ctrl+shift+p",
            paused=bool(data.get("paused", False)),
            start_with_windows=bool(data.get("start_with_windows", False)),
            seen_coach=bool(data.get("seen_coach", False)),
            disabled_apps=list(data.get("disabled_apps") or []),
        )


@dataclass
class Library:
    folders: list[Folder] = field(default_factory=list)
    settings: Settings = field(default_factory=Settings)

    def all_snippets(self) -> list[tuple[Folder, Snippet]]:
        items: list[tuple[Folder, Snippet]] = []
        for folder in self.folders:
            for snippet in folder.snippets:
                items.append((folder, snippet))
        return items

    def snippet_count(self) -> int:
        return sum(len(folder.snippets) for folder in self.folders)

    def find_snippet(self, snippet_id: str) -> tuple[Folder, Snippet] | None:
        for folder in self.folders:
            for snippet in folder.snippets:
                if snippet.id == snippet_id:
                    return folder, snippet
        return None

    def find_by_shortcut(self, shortcut: str) -> tuple[Folder, Snippet] | None:
        needle = shortcut.casefold()
        for folder, snippet in self.all_snippets():
            if snippet.enabled and snippet.shortcut.casefold() == needle:
                return folder, snippet
        return None

    def ensure_folder(self, name: str) -> Folder:
        cleaned = (name or "").strip() or "Personal"
        for folder in self.folders:
            if folder.name.casefold() == cleaned.casefold():
                return folder
        folder = Folder(id=new_id(), name=cleaned)
        self.folders.append(folder)
        return folder

    def move_snippet(self, snippet: Snippet, dest: Folder) -> None:
        for folder in self.folders:
            if snippet in folder.snippets:
                if folder is dest:
                    return
                folder.snippets.remove(snippet)
                break
        if snippet not in dest.snippets:
            dest.snippets.append(snippet)

    def delete_snippet(self, snippet_id: str) -> None:
        for folder in self.folders:
            folder.snippets = [item for item in folder.snippets if item.id != snippet_id]

    def replace_from(self, incoming: Library) -> None:
        self.folders[:] = incoming.folders
        self.settings.disabled_apps = list(incoming.settings.disabled_apps)
        self.settings.search_hotkey = incoming.settings.search_hotkey
        self.settings.pause_hotkey = incoming.settings.pause_hotkey
        self.settings.paused = False

    def merge_from(self, incoming: Library) -> None:
        for folder in incoming.folders:
            dest = self.ensure_folder(folder.name)
            dest.trigger = folder.trigger
            for snippet in folder.snippets:
                existing = self.find_snippet(snippet.id)
                if existing is None:
                    match = next(
                        (
                            item
                            for item in dest.snippets
                            if item.shortcut and item.shortcut.casefold() == snippet.shortcut.casefold()
                        ),
                        None,
                    )
                    if match is None:
                        dest.snippets.append(snippet)
                        continue
                    existing = dest, match
                current_folder, current = existing
                current.label = snippet.label
                current.shortcut = snippet.shortcut
                current.content = snippet.content
                current.enabled = snippet.enabled
                if current_folder is not dest:
                    self.move_snippet(current, dest)

    def prefix_conflicts(self, shortcut: str, ignore_id: str | None = None) -> list[Snippet]:
        if not shortcut:
            return []
        needle = shortcut.casefold()
        hits: list[Snippet] = []
        for _, snippet in self.all_snippets():
            if ignore_id and snippet.id == ignore_id:
                continue
            other = snippet.shortcut.casefold()
            if not other:
                continue
            if needle.startswith(other) or other.startswith(needle):
                hits.append(snippet)
        return hits

    def to_dict(self) -> dict:
        return {
            "version": 1,
            "folders": [f.to_dict() for f in self.folders],
            "settings": self.settings.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> Library:
        return cls(
            folders=[Folder.from_dict(f) for f in data.get("folders") or []],
            settings=Settings.from_dict(data.get("settings") or {}),
        )


MatchKind = Literal["exact", "prefix"]
