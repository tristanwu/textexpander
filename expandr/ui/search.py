from __future__ import annotations

import customtkinter as ctk

from expandr.models import Library, Snippet


class SearchDialog(ctk.CTkToplevel):
    def __init__(self, master, library: Library):
        super().__init__(master)
        self.title("Insert snippet")
        self.attributes("-topmost", True)
        self.geometry("520x380")
        self.result: Snippet | None = None
        self._items = [(folder, snippet) for folder, snippet in library.all_snippets() if snippet.enabled]

        self.entry = ctk.CTkEntry(self, placeholder_text="Search shortcut, label, or folder")
        self.entry.pack(fill="x", padx=16, pady=(16, 8))
        self.entry.bind("<KeyRelease>", lambda _e: self._refresh())
        self.entry.bind("<Return>", lambda _e: self._accept())
        self.entry.bind("<Escape>", lambda _e: self._cancel())
        self.entry.bind("<Down>", lambda _e: self._move(1))
        self.entry.bind("<Up>", lambda _e: self._move(-1))

        self.listbox = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.listbox.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        self._buttons: list[ctk.CTkButton] = []
        self._visible: list[Snippet] = []
        self._index = 0
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.after(50, self._ready)
        self._refresh()

    def _ready(self) -> None:
        self.lift()
        self.entry.focus_force()

    def _refresh(self) -> None:
        query = self.entry.get().strip().casefold()
        for child in self.listbox.winfo_children():
            child.destroy()
        self._buttons = []
        self._visible = []
        for folder, snippet in self._items:
            hay = f"{snippet.label} {snippet.shortcut} {folder.name}".casefold()
            if query and query not in hay:
                continue
            self._visible.append(snippet)
            cue = snippet.shortcut or "(no shortcut)"
            btn = ctk.CTkButton(
                self.listbox,
                text=f"{cue}   {snippet.label}   · {folder.name}",
                anchor="w",
                fg_color="transparent",
                text_color=("gray10", "gray90"),
                hover_color=("gray80", "gray25"),
                command=lambda s=snippet: self._choose(s),
            )
            btn.pack(fill="x", pady=2)
            self._buttons.append(btn)
        self._index = 0
        self._highlight()

    def _highlight(self) -> None:
        for i, btn in enumerate(self._buttons):
            btn.configure(fg_color=("gray75", "gray30") if i == self._index else "transparent")

    def _move(self, delta: int) -> None:
        if not self._visible:
            return
        self._index = max(0, min(len(self._visible) - 1, self._index + delta))
        self._highlight()

    def _accept(self) -> None:
        if self._visible:
            self._choose(self._visible[self._index])

    def _choose(self, snippet: Snippet) -> None:
        self.result = snippet
        self.destroy()

    def _cancel(self) -> None:
        self.result = None
        self.destroy()


def ask_snippet(master, library: Library) -> Snippet | None:
    dialog = SearchDialog(master, library)
    master.wait_window(dialog)
    return dialog.result
