from __future__ import annotations

import threading
import time
from typing import Callable, Protocol


PRE_PASTE_S = 0.08
AFTER_DELETE_S = 0.02
POST_PASTE_S = 0.08
# Hold the snippet on the clipboard after Ctrl+V so a slow target can read it.
# Restore is skipped when the clipboard changed during this window (ADR 0009).
RESTORE_AFTER_PASTE_S = 1.0


def restore_wait_s() -> float:
    """How long the restore thread waits. The caller already slept POST_PASTE_S."""
    return RESTORE_AFTER_PASTE_S - POST_PASTE_S


def should_restore_clipboard(
    *,
    placed_text: str,
    current_text: str | None,
    placed_sequence: int | None,
    current_sequence: int | None,
) -> bool:
    """True only when the clipboard still holds the snippet we placed.

    A sequence change means another writer, usually a user copy, owns the
    clipboard — including a non-text copy of the same characters. Content is
    checked too, so a missing sequence cannot write the previous clip over
    different text.
    """
    if placed_sequence is not None and current_sequence != placed_sequence:
        return False
    return current_text == placed_text


class InsertPorts(Protocol):
    def get_text(self) -> str | None: ...

    def set_text(self, text: str) -> bool: ...

    def sequence(self) -> int: ...

    def wait_keys_up(self) -> None: ...

    def focus(self, hwnd: int) -> None: ...

    def backspace(self, count: int) -> bool: ...

    def paste(self) -> bool: ...

    def type_text(self, text: str) -> bool: ...

    def move_left(self, count: int) -> bool: ...

    def sleep(self, seconds: float) -> None: ...

    def defer(self, delay: float, action: Callable[[], None]) -> None: ...


class Win32InsertPorts:
    """Win32 clipboard and SendInput. Imported on first use so tests can run elsewhere."""

    def get_text(self) -> str | None:
        from expandr.win32api import get_clipboard_text

        return get_clipboard_text()

    def set_text(self, text: str) -> bool:
        from expandr.win32api import set_clipboard_text

        return set_clipboard_text(text)

    def sequence(self) -> int:
        from expandr.win32api import clipboard_sequence

        return clipboard_sequence()

    def wait_keys_up(self) -> None:
        from expandr.win32api import wait_keys_up

        wait_keys_up()

    def focus(self, hwnd: int) -> None:
        from expandr.win32api import focus_hwnd

        focus_hwnd(hwnd)

    def backspace(self, count: int) -> bool:
        from expandr.win32api import send_backspaces

        return send_backspaces(count)

    def paste(self) -> bool:
        from expandr.win32api import send_ctrl_v

        return send_ctrl_v()

    def type_text(self, text: str) -> bool:
        from expandr.win32api import send_text

        return send_text(text)

    def move_left(self, count: int) -> bool:
        from expandr.win32api import send_left

        return send_left(count)

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)

    def defer(self, delay: float, action: Callable[[], None]) -> None:
        def run() -> None:
            time.sleep(delay)
            action()

        threading.Thread(target=run, name="expandr-clip", daemon=True).start()


def insert_expansion(
    hwnd: int,
    delete_count: int,
    text: str,
    cursor: int | None,
    ports: InsertPorts | None = None,
) -> str:
    """Replace the typed shortcut. Clipboard paste first — Win11 Notepad drops Unicode SendInput."""
    io = ports or Win32InsertPorts()
    io.wait_keys_up()
    io.focus(hwnd)
    previous = io.get_text()
    if not io.set_text(text):
        io.backspace(delete_count)
        if io.type_text(text):
            if cursor is not None:
                io.move_left(max(0, len(text) - cursor))
            return "typed"
        return "failed"
    try:
        placed_sequence: int | None = io.sequence()
    except OSError:
        placed_sequence = None
    io.sleep(PRE_PASTE_S)
    io.backspace(delete_count)
    io.sleep(AFTER_DELETE_S)
    if not io.paste():
        io.type_text(text)
        _schedule_restore(previous, text, placed_sequence, io)
        return "typed"
    io.sleep(POST_PASTE_S)
    _schedule_restore(previous, text, placed_sequence, io)
    if cursor is not None:
        io.move_left(max(0, len(text) - cursor))
    return "pasted"


def _schedule_restore(
    previous: str | None,
    placed: str,
    placed_sequence: int | None,
    io: InsertPorts,
) -> None:
    if previous is None:
        return

    def restore() -> None:
        try:
            current_sequence = io.sequence()
            current_text = io.get_text()
        except OSError:
            return
        if should_restore_clipboard(
            placed_text=placed,
            current_text=current_text,
            placed_sequence=placed_sequence,
            current_sequence=current_sequence,
        ):
            io.set_text(previous)

    io.defer(restore_wait_s(), restore)
