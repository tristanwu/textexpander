import ctypes

from expandr.win32api import INPUT


def test_input_struct_matches_win32():
    # 64-bit INPUT is 40 bytes. A too-small struct makes SendInput a no-op.
    assert ctypes.sizeof(INPUT) == 40
