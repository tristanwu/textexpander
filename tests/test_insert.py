"""Clipboard insert decisions, without a Win32 desktop session.

Non-US keyboard layouts are not involved here. The paste path is covered in
`test_hook_chars.py` for the US virtual-key table and in ADR 0009 for restore.
"""

from expandr.insert import (
    AFTER_DELETE_S,
    POST_PASTE_S,
    PRE_PASTE_S,
    RESTORE_AFTER_PASTE_S,
    insert_expansion,
    restore_wait_s,
    should_restore_clipboard,
)


class _Clipboard:
    def __init__(self, text: str | None):
        self.text = text
        self.sequence_no = 0 if text is None else 1
        self.fail_set = False

    def get_text(self) -> str | None:
        return self.text

    def set_text(self, text: str) -> bool:
        if self.fail_set:
            return False
        self.text = text
        self.sequence_no += 1
        return True

    def sequence(self) -> int:
        return self.sequence_no

    def user_copy(self, text: str) -> None:
        self.text = text
        self.sequence_no += 1

    def replace_text_without_sequence_change(self, text: str) -> None:
        self.text = text


class _Ports:
    def __init__(self, clip: _Clipboard):
        self.clip = clip
        self.calls: list = []
        self.deferred: list = []
        self.fail_paste = False
        self.fail_type = False

    def get_text(self):
        return self.clip.get_text()

    def set_text(self, text: str) -> bool:
        self.calls.append(("set", text))
        return self.clip.set_text(text)

    def sequence(self) -> int:
        return self.clip.sequence()

    def wait_keys_up(self) -> None:
        self.calls.append("wait")

    def focus(self, hwnd: int) -> None:
        self.calls.append(("focus", hwnd))

    def backspace(self, count: int) -> bool:
        self.calls.append(("backspace", count))
        return True

    def paste(self) -> bool:
        self.calls.append("paste")
        return not self.fail_paste

    def type_text(self, text: str) -> bool:
        self.calls.append(("type", text))
        return not self.fail_type

    def move_left(self, count: int) -> bool:
        self.calls.append(("left", count))
        return True

    def sleep(self, seconds: float) -> None:
        self.calls.append(("sleep", seconds))

    def defer(self, delay: float, action) -> None:
        self.deferred.append((delay, action))

    def run_restore(self) -> None:
        assert len(self.deferred) == 1
        _delay, action = self.deferred[0]
        action()


def test_restore_requires_the_same_sequence_and_text():
    assert should_restore_clipboard(
        placed_text="snippet",
        current_text="snippet",
        placed_sequence=5,
        current_sequence=5,
    )
    assert not should_restore_clipboard(
        placed_text="snippet",
        current_text="snippet",
        placed_sequence=5,
        current_sequence=6,
    )
    assert not should_restore_clipboard(
        placed_text="snippet",
        current_text="copied",
        placed_sequence=5,
        current_sequence=6,
    )
    assert not should_restore_clipboard(
        placed_text="snippet",
        current_text="copied",
        placed_sequence=5,
        current_sequence=5,
    )
    assert not should_restore_clipboard(
        placed_text="snippet",
        current_text=None,
        placed_sequence=5,
        current_sequence=5,
    )
    assert should_restore_clipboard(
        placed_text="snippet",
        current_text="snippet",
        placed_sequence=None,
        current_sequence=None,
    )


def test_paste_restores_previous_clipboard_only_after_the_slow_target_grace():
    assert RESTORE_AFTER_PASTE_S >= 1.0
    clip = _Clipboard("secret")
    ports = _Ports(clip)
    how = insert_expansion(7, 3, "Hello", None, ports)
    assert how == "pasted"
    assert ports.calls[0] == "wait"
    assert ("focus", 7) in ports.calls
    assert ("backspace", 3) in ports.calls
    assert "paste" in ports.calls
    assert ("sleep", PRE_PASTE_S) in ports.calls
    assert ("sleep", AFTER_DELETE_S) in ports.calls
    assert ("sleep", POST_PASTE_S) in ports.calls
    assert ports.deferred[0][0] == restore_wait_s()
    assert restore_wait_s() + POST_PASTE_S == RESTORE_AFTER_PASTE_S
    # A slow target that reads the clipboard when paste returns still sees the snippet.
    assert clip.text == "Hello"
    ports.run_restore()
    assert clip.text == "secret"


def test_user_copy_during_restore_window_is_kept():
    clip = _Clipboard("secret")
    ports = _Ports(clip)
    insert_expansion(1, 2, "Hello", None, ports)
    clip.user_copy("fresh copy")
    ports.run_restore()
    assert clip.text == "fresh copy"


def test_copy_of_the_same_text_still_blocks_restore():
    clip = _Clipboard("secret")
    ports = _Ports(clip)
    insert_expansion(1, 2, "Hello", None, ports)
    clip.user_copy("Hello")
    ports.run_restore()
    assert clip.text == "Hello"


def test_changed_text_with_the_same_sequence_is_not_overwritten():
    clip = _Clipboard("secret")
    ports = _Ports(clip)
    insert_expansion(1, 2, "Hello", None, ports)
    clip.replace_text_without_sequence_change("other")
    ports.run_restore()
    assert clip.text == "other"


def test_empty_previous_clipboard_is_left_alone():
    clip = _Clipboard(None)
    ports = _Ports(clip)
    assert insert_expansion(1, 2, "Hello", None, ports) == "pasted"
    assert ports.deferred == []
    assert clip.text == "Hello"


def test_clipboard_failure_types_the_snippet():
    clip = _Clipboard("secret")
    clip.fail_set = True
    ports = _Ports(clip)
    assert insert_expansion(1, 4, "Hello", 2, ports) == "typed"
    assert ("type", "Hello") in ports.calls
    assert ("left", 3) in ports.calls
    assert "paste" not in ports.calls
    assert ports.deferred == []
    assert clip.text == "secret"


def test_paste_failure_types_and_still_guards_the_clipboard():
    clip = _Clipboard("secret")
    ports = _Ports(clip)
    ports.fail_paste = True
    assert insert_expansion(1, 4, "Hello", None, ports) == "typed"
    assert ("type", "Hello") in ports.calls
    clip.user_copy("fresh copy")
    ports.run_restore()
    assert clip.text == "fresh copy"


def test_cursor_moves_after_a_paste():
    clip = _Clipboard("secret")
    ports = _Ports(clip)
    assert insert_expansion(1, 1, "Hello", 1, ports) == "pasted"
    assert ("left", 4) in ports.calls


def test_restore_skips_when_the_clipboard_cannot_be_read():
    clip = _Clipboard("secret")
    ports = _Ports(clip)
    insert_expansion(1, 1, "Hello", None, ports)

    def boom():
        raise OSError("clipboard busy")

    ports.sequence = boom
    ports.run_restore()
    assert clip.text == "Hello"


def test_both_paste_and_typing_can_fail():
    clip = _Clipboard("secret")
    clip.fail_set = True
    ports = _Ports(clip)
    ports.fail_type = True
    assert insert_expansion(1, 1, "Hello", None, ports) == "failed"
