import re
import sys
from pathlib import Path

import pytest

_WIN32 = pytest.mark.skipif(sys.platform != "win32", reason="Win32 DLL layout is Windows-specific")


@_WIN32
def test_input_struct_matches_win32():
    # 64-bit INPUT is 40 bytes. A too-small struct makes SendInput a no-op.
    import ctypes

    from expandr.win32api import INPUT

    assert ctypes.sizeof(INPUT) == 40


@_WIN32
def test_win32api_imports_on_windows():
    """Import binds every export. The wrong DLL raises AttributeError here."""
    import expandr.win32api as win32api

    assert win32api.user32 is not None
    assert win32api.user32.GetClipboardSequenceNumber


def test_get_clipboard_sequence_number_bound_on_user32():
    """user32 exports GetClipboardSequenceNumber. Import never loads it off Windows."""
    root = Path(__file__).resolve().parents[1] / "expandr"
    hits: list[str] = []
    for path in sorted(root.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        hits.extend(re.findall(r"(\w+)\s*\.\s*GetClipboardSequenceNumber", text))
    assert hits, "GetClipboardSequenceNumber is not bound"
    assert set(hits) == {"user32"}
