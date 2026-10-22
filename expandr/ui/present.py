from __future__ import annotations

import tkinter as tk


def present(window) -> None:
    """Put a window in front of the other TextExpander windows.

    CustomTkinter paints the Windows title bar by hiding the window and
    showing it again a few milliseconds later. That second show does not
    raise the window, so Settings and Sessions open behind the library.
    """

    def _raise() -> None:
        try:
            if not window.winfo_exists():
                return
            window.deiconify()
            window.lift()
            window.attributes("-topmost", True)
            window.focus_force()
        except tk.TclError:
            return

    def _release() -> None:
        try:
            if not window.winfo_exists():
                return
            window.attributes("-topmost", False)
            window.lift()
        except tk.TclError:
            return

    _raise()
    window.after(60, _raise)
    window.after(280, _raise)
    window.after(420, _release)
