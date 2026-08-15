from __future__ import annotations

from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from expandr.csv_io import export_csv, import_csv
from expandr.models import Library, TriggerMode
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
        self.geometry("520x620")
        self.library = library
        self.on_change = on_change

        pad = {"padx": 16, "pady": 6}
        ctk.CTkLabel(self, text="Settings", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w", padx=16, pady=(16, 8))

        self.startup_var = ctk.BooleanVar(value=library.settings.start_with_windows)
        ctk.CTkSwitch(self, text="Start with Windows", variable=self.startup_var, command=self._toggle_startup).pack(
            anchor="w", **pad
        )

        ctk.CTkLabel(self, text="Ctrl+Shift+/  search     Ctrl+Shift+P  pause", text_color="gray").pack(
            anchor="w", padx=16
        )

        ctk.CTkLabel(self, text="Do not expand in these apps (one exe name per line)").pack(anchor="w", padx=16, pady=(12, 4))
        self.apps = ctk.CTkTextbox(self, height=90)
        self.apps.pack(fill="x", padx=16)
        self.apps.insert("1.0", "\n".join(library.settings.disabled_apps))
        self.apps.bind("<KeyRelease>", lambda _e: self._save_apps())

        ctk.CTkLabel(self, text="Folder trigger").pack(anchor="w", padx=16, pady=(12, 4))
        self.folder_frame = ctk.CTkScrollableFrame(self, height=140)
        self.folder_frame.pack(fill="both", expand=True, padx=16)
        self._render_folders()

        ctk.CTkLabel(self, text="Move this library to another PC", text_color="gray").pack(anchor="w", padx=16, pady=(8, 4))
        files = ctk.CTkFrame(self, fg_color="transparent")
        files.pack(fill="x", padx=16)
        ctk.CTkButton(files, text="Export library", width=130, command=self._export_bundle).pack(side="left")
        ctk.CTkButton(files, text="Import library", width=130, command=self._import_bundle).pack(side="left", padx=8)

        csv_row = ctk.CTkFrame(self, fg_color="transparent")
        csv_row.pack(fill="x", padx=16, pady=(8, 16))
        ctk.CTkButton(csv_row, text="Import CSV", width=110, fg_color="gray", command=self._import_csv).pack(side="left")
        ctk.CTkButton(csv_row, text="Export CSV", width=110, fg_color="gray", command=self._export_csv).pack(
            side="left", padx=8
        )
        ctk.CTkButton(csv_row, text="Open data folder", width=140, fg_color="gray", command=self._open_data).pack(
            side="left"
        )

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

    def _toggle_startup(self) -> None:
        enabled = bool(self.startup_var.get())
        self.library.settings.start_with_windows = enabled
        set_start_with_windows(enabled)
        save_library(self.library)

    def _save_apps(self) -> None:
        lines = [line.strip() for line in self.apps.get("1.0", "end-1c").splitlines() if line.strip()]
        self.library.settings.disabled_apps = lines
        save_library(self.library)

    def _export_bundle(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("Expandr library", "*.json"), ("All", "*.*")],
            initialfile="expandr-library.json",
        )
        if not path:
            return
        export_bundle(self.library, Path(path))
        messagebox.showinfo("Export", "Library saved. Copy that file to the other PC and use Import library.")

    def _import_bundle(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("Expandr library", "*.json"), ("All", "*.*")])
        if not path:
            return
        choice = messagebox.askyesnocancel(
            "Import library",
            "Replace the snippets on this PC with the file?\n\n"
            "Yes = replace this library\n"
            "No = merge into the current library\n"
            "Cancel = do nothing",
        )
        if choice is None:
            return
        try:
            result = import_bundle(self.library, Path(path), merge=not choice)
        except TransferError as exc:
            messagebox.showerror("Import", str(exc))
            return
        save_library(self.library)
        self.on_change()
        self._render_folders()
        action = "Replaced" if result.replaced else "Merged"
        messagebox.showinfo("Import", f"{action} library · {result.snippets} snippets in {result.folders} folders.")

    def _import_csv(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("CSV", "*.csv"), ("All", "*.*")])
        if not path:
            return
        count = import_csv(self.library, Path(path))
        save_library(self.library)
        self.on_change()
        self._render_folders()
        messagebox.showinfo("Import", f"Imported {count} snippets.")

    def _export_csv(self) -> None:
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not path:
            return
        export_csv(self.library, Path(path))

    def _open_data(self) -> None:
        import os

        os.startfile(data_dir())
