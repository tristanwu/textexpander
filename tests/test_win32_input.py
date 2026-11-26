import sys

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="SendInput INPUT layout is Windows-specific")


def test_input_struct_matches_win32():
    # 64-bit INPUT is 40 bytes. A too-small struct makes SendInput a no-op.
    import ctypes

    from expandr.win32api import INPUT

    assert ctypes.sizeof(INPUT) == 40
