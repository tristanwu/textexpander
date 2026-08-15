from __future__ import annotations

import threading
import time

from expandr.win32api import (
    focus_hwnd,
    get_clipboard_text,
    send_backspaces,
    send_ctrl_v,
    send_left,
    send_text,
    set_clipboard_text,
    wait_keys_up,
)

PRE_PASTE_S = 0.08
POST_PASTE_S = 0.08
RESTORE_S = 0.25


def insert_expansion(hwnd: int, delete_count: int, text: str, cursor: int | None) -> str:
    """Replace the typed shortcut. Clipboard paste first — Win11 Notepad drops Unicode SendInput."""
    wait_keys_up()
    focus_hwnd(hwnd)
    previous = get_clipboard_text()
    if not set_clipboard_text(text):
        send_backspaces(delete_count)
        if send_text(text):
            if cursor is not None:
                send_left(max(0, len(text) - cursor))
            return "typed"
        return "failed"
    time.sleep(PRE_PASTE_S)
    send_backspaces(delete_count)
    time.sleep(0.02)
    if not send_ctrl_v():
        send_text(text)
        _restore_later(previous)
        return "typed"
    time.sleep(POST_PASTE_S)
    _restore_later(previous)
    if cursor is not None:
        send_left(max(0, len(text) - cursor))
    return "pasted"


def _restore_later(previous: str | None) -> None:
    if previous is None:
        return

    def restore() -> None:
        time.sleep(RESTORE_S)
        set_clipboard_text(previous)

    threading.Thread(target=restore, name="expandr-clip", daemon=True).start()
