from __future__ import annotations

from tkinter import messagebox

import customtkinter as ctk

from expandr.identity import APP_NAME
from expandr.models import Folder, Library, Snippet, new_id, shortcut_is_armed
from expandr.store import save_library


INSERT_FIELDS = [
    ("Text field", "{formtext: name=name; default=}"),
    ("Paragraph", "{formparagraph: name=notes}"),
    ("Menu", "{formmenu: Option A; Option B; name=choice}"),
    ("Date picker", "{formdate: YYYY-MM-DD; name=when}"),
    ("Toggle", "{formtoggle: name=extra; default=no}optional{endformtoggle}"),
    ("Today", "{time: YYYY-MM-DD}"),
    ("Clipboard", "{clipboard}"),
    ("Cursor", "{cursor}"),
    ("If / else", '{if: name = ""}then{else}else{endif}'),
    ("Formula", "{= }"),
]
INSERT_LOOKUP = {label: snippet for label, snippet in INSERT_FIELDS}


class MainWindow(ctk.CTkToplevel):
    def __init__(
        self,
        master,
        library: Library,
        on_change,
        on_settings,
        on_quit=None,
        status_provider=None,
        conflict_provider=None,
    ):
        super().__init__(master)
        self.title(APP_NAME)
        self.geometry("960x700")
        self.minsize(800, 560)
        self.library = library
        self.on_change = on_change
        self.on_settings = on_settings
        self.on_quit = on_quit
        self.status_provider = status_provider
        self.conflict_provider = conflict_provider
        self._selected: Snippet | None = None
        self._folder: Folder | None = None
        self._loading = False
        self._save_job = None
        self._filter = ""

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.banner = ctk.CTkLabel(self, text="", text_color="#b45309", anchor="w", justify="left", wraplength=900)
        self.banner.grid(row=0, column=0, columnspan=2, sticky="ew", padx=16, pady=(10, 0))

        sidebar = ctk.CTkFrame(self, width=300, corner_radius=0)
        sidebar.grid(row=1, column=0, sticky="nsew")
        sidebar.grid_rowconfigure(2, weight=1)

        header = ctk.CTkFrame(sidebar, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=12, pady=(14, 8))
        ctk.CTkLabel(header, text="Snippets", font=ctk.CTkFont(size=18, weight="bold")).pack(side="left")
        if self.on_quit:
            ctk.CTkButton(header, text="Quit", width=64, fg_color="gray", command=self.on_quit).pack(side="right")
        ctk.CTkButton(header, text="Settings", width=80, command=self.on_settings).pack(side="right", padx=6)

        self.filter_entry = ctk.CTkEntry(sidebar, placeholder_text="Filter")
        self.filter_entry.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 8))
        self.filter_entry.bind("<KeyRelease>", lambda _e: self._apply_filter())

        self.snippet_list = ctk.CTkScrollableFrame(sidebar)
        self.snippet_list.grid(row=2, column=0, sticky="nsew", padx=12, pady=4)

        list_btns = ctk.CTkFrame(sidebar, fg_color="transparent")
        list_btns.grid(row=3, column=0, sticky="ew", padx=12, pady=12)
        ctk.CTkButton(list_btns, text="New snippet", command=self._new_snippet).pack(side="left")
        ctk.CTkButton(list_btns, text="Delete", width=80, fg_color="gray", command=self._delete_snippet).pack(
            side="left", padx=8
        )

        editor = ctk.CTkFrame(self, fg_color="transparent")
        editor.grid(row=1, column=1, sticky="nsew", padx=16, pady=16)
        editor.grid_columnconfigure(1, weight=1)
        editor.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(editor, text="Shortcut").grid(row=0, column=0, sticky="w")
        self.shortcut_entry = ctk.CTkEntry(editor)
        self.shortcut_entry.grid(row=0, column=1, sticky="ew", padx=(8, 0), pady=4)

        insert_row = ctk.CTkFrame(editor, fg_color="transparent")
        insert_row.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(4, 0))
        ctk.CTkLabel(insert_row, text="Insert field").pack(side="left")
        self.insert_box = ctk.CTkComboBox(
            insert_row,
            values=[label for label, _ in INSERT_FIELDS],
            width=180,
            command=self._insert_field,
        )
        self.insert_box.set("Text field")
        self.insert_box.pack(side="left", padx=8)

        self.content = ctk.CTkTextbox(editor, wrap="word", font=ctk.CTkFont(family="Consolas", size=14))
        self.content.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=8)

        ctk.CTkLabel(editor, text="Label").grid(row=3, column=0, sticky="w")
        self.label_entry = ctk.CTkEntry(editor)
        self.label_entry.grid(row=3, column=1, sticky="ew", padx=(8, 0), pady=4)

        ctk.CTkLabel(editor, text="Folder").grid(row=4, column=0, sticky="w")
        self.folder_box = ctk.CTkComboBox(editor, values=self._folder_names(), command=self._folder_changed)
        self.folder_box.grid(row=4, column=1, sticky="w", padx=(8, 0), pady=4)

        self.hint = ctk.CTkLabel(editor, text="", text_color="gray", anchor="w")
        self.hint.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(4, 0))

        ctk.CTkLabel(editor, text="Test here").grid(row=6, column=0, sticky="w", pady=(8, 0))
        self.test_entry = ctk.CTkEntry(editor, placeholder_text="Type /ty here — it should expand")
        self.test_entry.grid(row=6, column=1, sticky="ew", padx=(8, 0), pady=(8, 0))

        self.status = ctk.CTkLabel(self, text="", anchor="w", justify="left")
        self.status.grid(row=2, column=0, columnspan=2, sticky="ew", padx=16, pady=(0, 10))

        for widget in (self.shortcut_entry, self.label_entry):
            widget.bind("<KeyRelease>", lambda _e: self._schedule_save())
        self.content.bind("<KeyRelease>", lambda _e: self._schedule_save())

        items = self.library.all_snippets()
        if items:
            self._select(items[0][1], items[0][0])
        self._refresh_list()
        self._update_status()
        self.protocol("WM_DELETE_WINDOW", self._hide)
        self.after(400, self._tick_status)

    def _folder_names(self) -> list[str]:
        names = [folder.name for folder in self.library.folders] or ["Personal"]
        return names + ["New folder…"]

    def _hide(self) -> None:
        self._flush_save()
        self.withdraw()

    def show(self) -> None:
        self.deiconify()
        self.lift()
        self.focus_force()
        self.folder_box.configure(values=self._folder_names())
        self._refresh_list()
        self._update_status()

    def _apply_filter(self) -> None:
        self._filter = self.filter_entry.get().strip().casefold()
        self._refresh_list()

    def _refresh_list(self) -> None:
        for child in self.snippet_list.winfo_children():
            child.destroy()
        for folder, snippet in self.library.all_snippets():
            hay = f"{snippet.label} {snippet.shortcut} {folder.name}".casefold()
            if self._filter and self._filter not in hay:
                continue
            selected = self._selected and snippet.id == self._selected.id
            cue = snippet.shortcut or "(no shortcut)"
            btn = ctk.CTkButton(
                self.snippet_list,
                text=f"{cue}   {snippet.label}",
                anchor="w",
                fg_color=("#1d4ed8", "#1d4ed8") if selected else "transparent",
                text_color=("white", "white") if selected else ("gray10", "gray90"),
                command=lambda s=snippet, f=folder: self._select(s, f),
            )
            btn.pack(fill="x", pady=2)

    def _select(self, snippet: Snippet, folder: Folder) -> None:
        self._flush_save()
        self._selected = snippet
        self._folder = folder
        self._load_editor()
        self._refresh_list()

    def _load_editor(self) -> None:
        self._loading = True
        self.shortcut_entry.delete(0, "end")
        self.label_entry.delete(0, "end")
        self.content.delete("1.0", "end")
        if self._selected:
            self.shortcut_entry.insert(0, self._selected.shortcut)
            self.label_entry.insert(0, self._selected.label)
            self.content.insert("1.0", self._selected.content)
        if self._folder:
            self.folder_box.set(self._folder.name)
        self._update_hint()
        self._loading = False

    def _schedule_save(self) -> None:
        if self._loading:
            return
        if self._save_job is not None:
            self.after_cancel(self._save_job)
        self._save_job = self.after(350, self._flush_save)

    def _flush_save(self) -> None:
        if self._save_job is not None:
            self.after_cancel(self._save_job)
            self._save_job = None
        if self._loading or not self._selected:
            return
        self._selected.shortcut = self.shortcut_entry.get().strip()
        self._selected.label = self.label_entry.get().strip() or "Untitled"
        self._selected.content = self.content.get("1.0", "end-1c")
        save_library(self.library)
        self.on_change()
        self._update_hint()
        self._refresh_list()
        self._update_status()

    def _update_hint(self) -> None:
        shortcut = self.shortcut_entry.get().strip()
        if not shortcut:
            self.hint.configure(text="Add a shortcut of 2+ characters to arm this snippet.")
            return
        if not shortcut_is_armed(shortcut):
            self.hint.configure(text="Shortcut is too short to expand. Use at least two characters.")
            return
        ignore = self._selected.id if self._selected else None
        hits = self.library.prefix_conflicts(shortcut, ignore)
        if hits:
            names = ", ".join(f"{item.shortcut} ({item.label})" for item in hits[:3])
            self.hint.configure(text=f"Possible conflict with {names}")
            return
        count = len(self.content.get("1.0", "end-1c"))
        self.hint.configure(text=f"{count:,} characters")

    def _update_status(self) -> None:
        armed = sum(1 for _, snippet in self.library.all_snippets() if shortcut_is_armed(snippet.shortcut))
        parts = [f"{self.library.snippet_count()} snippets", f"{armed} armed"]
        if self.library.settings.paused:
            parts.append("paused")
        if self.status_provider:
            info = self.status_provider()
            if info.get("hook_ok"):
                parts.append("hook ok")
            else:
                error = info.get("hook_error") or "?"
                parts.append(f"hook failed ({error})")
            heard = info.get("last_heard") or info.get("buffer") or ""
            if heard:
                parts.append(f"heard {heard!r}")
            seen = info.get("keys_seen") or 0
            parts.append(f"{seen} keys")
            last = info.get("last_expand") or ""
            if last:
                parts.append(f"last expand {last}")
            inserted = info.get("last_insert") or ""
            if inserted:
                parts.append(inserted)
        self.status.configure(text=" · ".join(parts))
        if self.conflict_provider and self.conflict_provider():
            self.banner.configure(
                text=(
                    "Text Blaze for Windows is also running. Both apps listen to every key, so they can "
                    f"block each other. Pause or quit the Text Blaze desktop app while you test {APP_NAME}. "
                    "The Chrome extension can stay."
                )
            )
            self.banner.grid()
        else:
            self.banner.configure(text="")
            self.banner.grid_remove()

    def _tick_status(self) -> None:
        if not self.winfo_exists():
            return
        self._update_status()
        self.after(400, self._tick_status)

    def _insert_field(self, label: str) -> None:
        snippet = INSERT_LOOKUP.get(label)
        if not snippet or not self._selected:
            return
        self.content.insert("insert", snippet)
        self._schedule_save()
        self.content.focus_set()

    def _folder_changed(self, name: str) -> None:
        if self._loading or not self._selected:
            return
        if name == "New folder…":
            dialog = ctk.CTkInputDialog(text="Folder name", title="New folder")
            name = (dialog.get_input() or "").strip()
            if not name:
                if self._folder:
                    self.folder_box.set(self._folder.name)
                return
        dest = self.library.ensure_folder(name)
        self.library.move_snippet(self._selected, dest)
        self._folder = dest
        self.folder_box.configure(values=self._folder_names())
        self.folder_box.set(dest.name)
        save_library(self.library)
        self.on_change()
        self._refresh_list()

    def _new_snippet(self) -> None:
        self._flush_save()
        folder = self._folder or self.library.ensure_folder("Personal")
        snippet = Snippet(id=new_id(), label="Untitled", shortcut="", content="")
        folder.snippets.append(snippet)
        save_library(self.library)
        self._select(snippet, folder)
        self.shortcut_entry.focus_set()

    def _delete_snippet(self) -> None:
        if not self._selected:
            return
        label = self._selected.label
        if not messagebox.askyesno("Delete snippet", f"Delete “{label}”?"):
            return
        snippet_id = self._selected.id
        self.library.delete_snippet(snippet_id)
        remaining = self.library.all_snippets()
        self._selected = None
        self._folder = None
        save_library(self.library)
        self.on_change()
        if remaining:
            self._select(remaining[0][1], remaining[0][0])
        else:
            self._load_editor()
            self._refresh_list()
            self._update_status()
