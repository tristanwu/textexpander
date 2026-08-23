from __future__ import annotations

import customtkinter as ctk

from expandr.identity import APP_NAME


class SessionConsentDialog(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Start a session?")
        self.attributes("-topmost", True)
        self.geometry("460x320")
        self.resizable(False, False)
        self.accepted = False
        ctk.CTkLabel(self, text="Start a session?", font=ctk.CTkFont(size=16, weight="bold")).pack(
            padx=20, pady=(20, 8), anchor="w"
        )
        ctk.CTkLabel(
            self,
            text=(
                f"{APP_NAME} can save the text you type until you stop the session.\n\n"
                "• It stays in %AppData%\\TextExpander\\sessions on this PC\n"
                "• It is not part of your snippet library or Export library\n"
                "• Apps on the skip list are left out\n"
                "• Stopping or quitting TextExpander ends the session\n"
                "• It will not start again after a restart"
            ),
            justify="left",
            anchor="w",
        ).pack(fill="x", padx=20, pady=8)
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(pady=(8, 20))
        ctk.CTkButton(row, text="Cancel", width=100, fg_color="gray", command=self._cancel).pack(side="left", padx=8)
        ctk.CTkButton(row, text="Start session", width=130, command=self._accept).pack(side="left")
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.after(50, self._ready)

    def _ready(self) -> None:
        self.lift()
        self.focus_force()

    def _cancel(self) -> None:
        self.accepted = False
        self.destroy()

    def _accept(self) -> None:
        self.accepted = True
        self.destroy()


def ask_session_consent(master) -> bool:
    dialog = SessionConsentDialog(master)
    master.wait_window(dialog)
    return bool(dialog.accepted)
