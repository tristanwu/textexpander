from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from expandr.session.store import (
    delete_session,
    list_sessions,
    load_chunks,
    load_session,
    sessions_dir,
    write_transcript,
)
from expandr.store import save_library


class SessionsWindow(ctk.CTkToplevel):
    def __init__(self, master, library, recorder, on_start, on_stop, on_change):
        super().__init__(master)
        self.title("Sessions")
        self.geometry("960x700")
        self.minsize(800, 560)
        self.library = library
        self.recorder = recorder
        self.on_start = on_start
        self.on_stop = on_stop
        self.on_change = on_change
        self._selected_id: str | None = None
        self._filter_app = ""

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.banner = ctk.CTkLabel(self, text="", text_color="#b45309", anchor="w")
        self.banner.grid(row=0, column=0, columnspan=2, sticky="ew", padx=16, pady=(10, 0))
        self.banner.grid_remove()

        sidebar = ctk.CTkFrame(self, width=300, corner_radius=0)
        sidebar.grid(row=1, column=0, sticky="nsew")
        sidebar.grid_rowconfigure(2, weight=1)

        header = ctk.CTkFrame(sidebar, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=12, pady=(14, 8))
        ctk.CTkLabel(header, text="Sessions", font=ctk.CTkFont(size=18, weight="bold")).pack(side="left")
        self.start_btn = ctk.CTkButton(header, text="Start session", width=110, command=self._toggle)
        self.start_btn.pack(side="right")

        self.filter_entry = ctk.CTkEntry(sidebar, placeholder_text="Filter by name or app")
        self.filter_entry.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 8))
        self.filter_entry.bind("<KeyRelease>", lambda _e: self.refresh())

        self.session_list = ctk.CTkScrollableFrame(sidebar)
        self.session_list.grid(row=2, column=0, sticky="nsew", padx=12, pady=4)

        main = ctk.CTkFrame(self, fg_color="transparent")
        main.grid(row=1, column=1, sticky="nsew", padx=16, pady=12)
        main.grid_rowconfigure(3, weight=1)
        main.grid_columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(main, text="No sessions yet", font=ctk.CTkFont(size=18, weight="bold"))
        self.title_label.grid(row=0, column=0, sticky="w")
        self.meta_label = ctk.CTkLabel(main, text="", text_color="gray", anchor="w", justify="left")
        self.meta_label.grid(row=1, column=0, sticky="w", pady=(0, 8))

        actions = ctk.CTkFrame(main, fg_color="transparent")
        actions.grid(row=2, column=0, sticky="w", pady=(0, 8))
        ctk.CTkButton(actions, text="Export transcript", width=140, command=self._export).pack(side="left")
        ctk.CTkButton(actions, text="Show in folder", width=120, fg_color="gray", command=self._show_folder).pack(
            side="left", padx=8
        )
        ctk.CTkButton(actions, text="Delete", width=80, fg_color="gray", command=self._delete).pack(side="left")

        self.transcript = ctk.CTkTextbox(main)
        self.transcript.grid(row=3, column=0, sticky="nsew")

        skip = ctk.CTkFrame(main, fg_color="transparent")
        skip.grid(row=4, column=0, sticky="ew", pady=(10, 0))
        ctk.CTkLabel(skip, text="Skip these apps while a session is on (one exe name per line)").pack(anchor="w")
        ctk.CTkLabel(
            skip,
            text='Different from “Do not expand.” Expansion can still run in an app you skip here.',
            text_color="gray",
        ).pack(anchor="w")
        self.skip_box = ctk.CTkTextbox(skip, height=70)
        self.skip_box.pack(fill="x", pady=(4, 0))
        self.skip_box.insert("1.0", "\n".join(library.settings.session_skip_apps))
        self.skip_box.bind("<KeyRelease>", lambda _e: self._save_skip())

        self.protocol("WM_DELETE_WINDOW", self.withdraw)
        self.refresh()

    def show(self) -> None:
        self.deiconify()
        self.lift()
        self.refresh()

    def refresh(self) -> None:
        live = self.recorder.live
        self.start_btn.configure(text="Stop session" if live else "Start session")
        if live:
            self.banner.configure(text="SESSION ON · saving what you type")
            self.banner.grid()
        else:
            self.banner.configure(text="")
            self.banner.grid_remove()

        for child in self.session_list.winfo_children():
            child.destroy()
        needle = (self.filter_entry.get() or "").casefold()
        sessions = list_sessions()
        if not sessions:
            ctk.CTkLabel(self.session_list, text="No sessions yet").pack(anchor="w")
            self.title_label.configure(text="No sessions yet")
            self.meta_label.configure(
                text="Start a session from the tray when you want to save what you type.\n"
                "It stays on this PC and is not included in Export library."
            )
            self.transcript.delete("1.0", "end")
            return
        for meta in sessions:
            apps = " · ".join(meta.apps.keys())
            hay = f"{meta.title} {apps}".casefold()
            if needle and needle not in hay:
                continue
            label = meta.title
            if meta.status == "live":
                label = "● " + label
            btn = ctk.CTkButton(
                self.session_list,
                text=f"{label}\n{_span(meta)}",
                anchor="w",
                fg_color="#1d4ed8" if meta.id == self._selected_id else "transparent",
                text_color=("white" if meta.id == self._selected_id else None),
                command=lambda ident=meta.id: self._select(ident),
            )
            btn.pack(fill="x", pady=2)
        if self._selected_id:
            self._select(self._selected_id)
        elif sessions:
            self._select(sessions[0].id)

    def _toggle(self) -> None:
        if self.recorder.live:
            self.on_stop()
        else:
            self.on_start()
        self.refresh()

    def _select(self, session_id: str) -> None:
        self._selected_id = session_id
        try:
            meta = load_session(session_id)
        except FileNotFoundError:
            return
        self.title_label.configure(text=meta.title)
        apps = " · ".join(meta.apps.keys()) or "No apps yet"
        self.meta_label.configure(text=f"{_span(meta)}\n{apps}")
        chunks = load_chunks(meta)
        if self._filter_app:
            chunks = [chunk for chunk in chunks if chunk.get("app") == self._filter_app]
        lines = []
        for chunk in chunks:
            lines.append(f"{chunk.get('app')} · {chunk.get('t_start')}")
            lines.append(chunk.get("text") or "")
            lines.append("")
        self.transcript.delete("1.0", "end")
        self.transcript.insert("1.0", "\n".join(lines) or "Nothing was saved in this session.")

    def _save_skip(self) -> None:
        lines = [line.strip() for line in self.skip_box.get("1.0", "end-1c").splitlines() if line.strip()]
        self.library.settings.session_skip_apps = lines
        save_library(self.library)
        self.on_change()

    def _export(self) -> None:
        if not self._selected_id:
            return
        meta = load_session(self._selected_id)
        source = write_transcript(meta)
        dest = filedialog.asksaveasfilename(
            defaultextension=".md",
            initialfile=f"{meta.title}.md",
            filetypes=[("Markdown", "*.md"), ("All", "*.*")],
        )
        if dest:
            Path(dest).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    def _show_folder(self) -> None:
        if self._selected_id:
            meta = load_session(self._selected_id)
            os.startfile(sessions_dir() / meta.folder)
        else:
            os.startfile(sessions_dir())

    def _delete(self) -> None:
        if not self._selected_id:
            return
        meta = load_session(self._selected_id)
        if not messagebox.askyesno(
            "Delete session",
            f'Delete “{meta.title}”?\n\nThis removes the file from {sessions_dir()}.\nYour snippet library is not affected.',
        ):
            return
        delete_session(meta.id)
        self._selected_id = None
        self.refresh()


def _span(meta) -> str:
    start = _short(meta.started_at)
    end = _short(meta.ended_at) if meta.ended_at else "live"
    return f"{start} – {end} · {meta.status}"


def _short(stamp: str) -> str:
    try:
        moment = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        return moment.astimezone().strftime("%I:%M %p").lstrip("0")
    except ValueError:
        return stamp
