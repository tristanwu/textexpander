from __future__ import annotations

import customtkinter as ctk

from expandr.identity import APP_NAME


class CoachDialog(ctk.CTkToplevel):
    def __init__(self, master, on_done):
        super().__init__(master)
        self.title(APP_NAME)
        self.attributes("-topmost", True)
        self.geometry("420x260")
        self.resizable(False, False)
        self._on_done = on_done
        ctk.CTkLabel(self, text=f"{APP_NAME} is running in the tray", font=ctk.CTkFont(size=16, weight="bold")).pack(
            padx=20, pady=(20, 8), anchor="w"
        )
        ctk.CTkLabel(
            self,
            text=(
                "Type /ty in Notepad to try it.\n"
                "If Text Blaze for Windows is running, pause it first.\n"
                "Ctrl+Shift+/ searches snippets.\n"
                "Ctrl+Shift+P pauses expansion.\n"
                "Open the tray icon when you want the library."
            ),
            justify="left",
            anchor="w",
        ).pack(fill="x", padx=20, pady=8)
        ctk.CTkButton(self, text="Got it", width=100, command=self._close).pack(pady=(8, 20))
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.after(50, self._ready)

    def _ready(self) -> None:
        self.lift()
        self.focus_force()

    def _close(self) -> None:
        self._on_done()
        self.destroy()
