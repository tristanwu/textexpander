from __future__ import annotations

from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from expandr.backup import BackupError, backups_dir, create_backup, list_backups
from expandr.csv_io import export_csv, import_csv
from expandr.models import Library, TriggerMode
from expandr.install import install_start_menu, is_on_start_menu, uninstall_start_menu
from expandr.session.store import sessions_dir
from expandr.startup import set_start_with_windows
from expandr.store import data_dir, save_library
from expandr.transfer import TransferError, import_bundle, export_bundle


TRIGGER_LABELS = {
    TriggerMode.WORD_START: "Start of word",
    TriggerMode.WORD_BOUNDED: "Whole word",
    TriggerMode.ANYWHERE: "Anywhere",
}
TRIGGER_BY_LABEL = {label: mode for mode, label in TRIGGER_LABELS.items()}


class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, master, library: Library, on_change):
        super().__init__(master)
        self.title("Settings")
        self.geometry("580x740")
        self.minsize(520, 560)
        self.library = library
        self.on_change = on_change

        ctk.CTkLabel(self, text="Settings", font=ctk.CTkFont(size=18, weight="bold")).pack(
            anchor="w", padx=16, pady=(16, 4)
        )

        library_box = ctk.CTkFrame(self, fg_color="transparent")
        library_box.pack(fill="x")
        self._heading(library_box, "Library", self._backup_note(), first=True)
        backup_row = ctk.CTkFrame(library_box, fg_color="transparent")
        backup_row.pack(fill="x", padx=16, pady=(0, 6))
        ctk.CTkButton(backup_row, text="Create backup", width=140, command=self._create_backup).pack(side="left")
        ctk.CTkButton(backup_row, text="Restore from backup", width=160, command=self._restore_backup).pack(
            side="left", padx=(8, 0)
        )
        move_row = ctk.CTkFrame(library_box, fg_color="transparent")
        move_row.pack(fill="x", padx=16, pady=(0, 6))
        ctk.CTkButton(move_row, text="Export library", width=140, fg_color="gray", command=self._export_bundle).pack(
            side="left"
        )
        ctk.CTkButton(move_row, text="Import library", width=140, fg_color="gray", command=self._import_bundle).pack(
            side="left", padx=(8, 0)
        )
        csv_row = ctk.CTkFrame(library_box, fg_color="transparent")
        csv_row.pack(fill="x", padx=16, pady=(0, 8))
        ctk.CTkButton(csv_row, text="Import CSV", width=110, fg_color="gray", command=self._import_csv).pack(side="left")
        ctk.CTkButton(csv_row, text="Export CSV", width=110, fg_color="gray", command=self._export_csv).pack(
            side="left", padx=(8, 0)
        )
        ctk.CTkButton(csv_row, text="Open data folder", width=140, fg_color="gray", command=self._open_data).pack(
            side="left", padx=(8, 0)
        )

        body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, pady=(0, 8))

        self._heading(body, "This PC", first=True)
        self.startup_var = ctk.BooleanVar(value=library.settings.start_with_windows)
        ctk.CTkSwitch(body, text="Start with Windows", variable=self.startup_var, command=self._toggle_startup).pack(
            anchor="w", padx=16, pady=6
        )
        self.start_menu_var = ctk.BooleanVar(value=is_on_start_menu())
        ctk.CTkSwitch(
            body, text="Show in Start menu / search", variable=self.start_menu_var, command=self._toggle_start_menu
        ).pack(anchor="w", padx=16, pady=6)
        ctk.CTkLabel(body, text="Ctrl+Shift+/  search. Pause expansion from the tray icon.", text_color="gray").pack(
            anchor="w", padx=16, pady=(0, 4)
        )

        self._heading(body, "Expansion", "Do not expand in these apps (one exe name per line).")
        self.apps = ctk.CTkTextbox(body, height=90)
        self.apps.pack(fill="x", padx=16)
        self.apps.insert("1.0", "\n".join(library.settings.disabled_apps))
        self.apps.bind("<KeyRelease>", lambda _e: self._save_apps())

        self._heading(
            body,
            "Sessions",
            "Skip these apps while a session is on (one exe name per line). "
            "Different from “Do not expand.” Sessions are optional and are not included in Export library.",
        )
        self.session_apps = ctk.CTkTextbox(body, height=90)
        self.session_apps.pack(fill="x", padx=16)
        self.session_apps.insert("1.0", "\n".join(library.settings.session_skip_apps))
        self.session_apps.bind("<KeyRelease>", lambda _e: self._save_session_apps())
        ctk.CTkButton(body, text="Open sessions folder", width=160, fg_color="gray", command=self._open_sessions).pack(
            anchor="w", padx=16, pady=(8, 4)
        )

        self._heading(body, "Folder trigger", "How a shortcut matches in each folder.")
        self.folder_frame = ctk.CTkFrame(body, fg_color="transparent")
        self.folder_frame.pack(fill="x", padx=16, pady=(0, 16))
        self._render_folders()

    def _heading(self, parent, title: str, note: str | None = None, *, first: bool = False) -> None:
        ctk.CTkLabel(parent, text=title, font=ctk.CTkFont(size=14, weight="bold")).pack(
            anchor="w", padx=16, pady=(8 if first else 16, 2)
        )
        if note:
            ctk.CTkLabel(parent, text=note, text_color="gray", wraplength=520, justify="left", anchor="w").pack(
                anchor="w", padx=16, pady=(0, 8)
            )

    def _backup_note(self) -> str:
        note = (
            "Create backup writes a timestamped file under backups/ and commits only that file. "
            "It does not push. Push the commit when another PC should get these snippets."
        )
        try:
            found = list_backups()
        except BackupError:
            return note + " Git has to be available in this checkout."
        if not found:
            return note + " No backup file in this repo yet."
        return note + f" Latest in the repo: {found[0].name}."

    def _render_folders(self) -> None:
        for child in self.folder_frame.winfo_children():
            child.destroy()
        for folder in self.library.folders:
            row = ctk.CTkFrame(self.folder_frame, fg_color="transparent")
            row.pack(fill="x", pady=4)
            ctk.CTkLabel(row, text=folder.name, width=160, anchor="w").pack(side="left")
            box = ctk.CTkComboBox(
                row,
                values=list(TRIGGER_LABELS.values()),
                width=160,
                command=lambda label, f=folder: self._set_trigger(f, label),
            )
            box.set(TRIGGER_LABELS[folder.trigger])
            box.pack(side="left")

    def _set_trigger(self, folder, label: str) -> None:
        folder.trigger = TRIGGER_BY_LABEL.get(label, TriggerMode.WORD_START)
        save_library(self.library)
        self.on_change()

    def _toggle_start_menu(self) -> None:
        try:
            if self.start_menu_var.get():
                install_start_menu()
            else:
                uninstall_start_menu()
        except Exception as exc:
            self.start_menu_var.set(is_on_start_menu())
            messagebox.showerror("Start menu", str(exc), parent=self)

    def _toggle_startup(self) -> None:
        enabled = bool(self.startup_var.get())
        self.library.settings.start_with_windows = enabled
        set_start_with_windows(enabled)
        save_library(self.library)

    def _save_apps(self) -> None:
        lines = [line.strip() for line in self.apps.get("1.0", "end-1c").splitlines() if line.strip()]
        self.library.settings.disabled_apps = lines
        save_library(self.library)

    def _save_session_apps(self) -> None:
        lines = [line.strip() for line in self.session_apps.get("1.0", "end-1c").splitlines() if line.strip()]
        self.library.settings.session_skip_apps = lines
        save_library(self.library)

    def _open_sessions(self) -> None:
        import os

        os.startfile(sessions_dir())

    def _export_bundle(self) -> None:
        path = filedialog.asksaveasfilename(
            parent=self,
            defaultextension=".json",
            filetypes=[("TextExpander library", "*.json"), ("All", "*.*")],
            initialfile="textexpander-library.json",
        )
        if not path:
            return
        export_bundle(self.library, Path(path))
        messagebox.showinfo(
            "Export", "Library saved. Copy that file to the other PC and use Import library.", parent=self
        )

    def _import_bundle(self) -> None:
        path = filedialog.askopenfilename(
            parent=self, filetypes=[("TextExpander library", "*.json"), ("All", "*.*")]
        )
        if not path:
            return
        choice = messagebox.askyesnocancel(
            "Import library",
            "Replace the snippets on this PC with the file?\n\n"
            "Yes = replace this library\n"
            "No = merge into the current library\n"
            "Cancel = do nothing",
            parent=self,
        )
        if choice is None:
            return
        try:
            result = import_bundle(self.library, Path(path), merge=not choice)
        except TransferError as exc:
            messagebox.showerror("Import", str(exc), parent=self)
            return
        save_library(self.library)
        self.on_change()
        self._render_folders()
        action = "Replaced" if result.replaced else "Merged"
        messagebox.showinfo(
            "Import", f"{action} library · {result.snippets} snippets in {result.folders} folders.", parent=self
        )

    def _create_backup(self) -> None:
        try:
            result = create_backup(self.library)
        except BackupError as exc:
            messagebox.showerror("Create backup", str(exc), parent=self)
            return
        messagebox.showinfo(
            "Create backup",
            f"Saved {result.path.name} and committed it as {result.commit}.",
            parent=self,
        )

    def _restore_backup(self) -> None:
        try:
            folder = backups_dir()
        except BackupError as exc:
            messagebox.showerror("Restore from backup", str(exc), parent=self)
            return
        path = filedialog.askopenfilename(
            parent=self,
            title="Restore from backup",
            initialdir=folder,
            filetypes=[("TextExpander backup", "*.json"), ("All", "*.*")],
        )
        if not path:
            return
        if not messagebox.askyesno(
            "Restore from backup",
            "Replace the snippets on this PC with the selected backup?\n\n"
            "Startup and other machine-only settings will stay unchanged.",
            parent=self,
        ):
            return
        try:
            result = import_bundle(self.library, Path(path), merge=False)
        except TransferError as exc:
            messagebox.showerror("Restore from backup", str(exc), parent=self)
            return
        save_library(self.library)
        self.on_change()
        self._render_folders()
        messagebox.showinfo(
            "Restore from backup",
            f"Restored {result.snippets} snippets in {result.folders} folders.",
            parent=self,
        )

    def _import_csv(self) -> None:
        path = filedialog.askopenfilename(parent=self, filetypes=[("CSV", "*.csv"), ("All", "*.*")])
        if not path:
            return
        count = import_csv(self.library, Path(path))
        save_library(self.library)
        self.on_change()
        self._render_folders()
        messagebox.showinfo("Import", f"Imported {count} snippets.", parent=self)

    def _export_csv(self) -> None:
        path = filedialog.asksaveasfilename(parent=self, defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not path:
            return
        export_csv(self.library, Path(path))

    def _open_data(self) -> None:
        import os

        os.startfile(data_dir())
