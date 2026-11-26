"""US-layout virtual-key mapping used by the hook.

ADR 0003 maps shortcuts with this US table. Non-US layouts are not covered:
OEM keys such as VK_OEM_2 stay slash/question here, and there is no
ToUnicode layout pass. That remains deferred.
"""

from expandr.keys import MOD_CAPS, MOD_SHIFT, fallback_char, vk_to_char


def test_fallback_slash_and_letters():
    assert fallback_char(0xBF, False) == "/"
    assert fallback_char(0xBF, True) == "?"
    assert fallback_char(0x54, False) == "t"
    assert fallback_char(0x59, False) == "y"
    assert fallback_char(0x54, True) == "T"


def test_fallback_ignores_function_keys():
    assert fallback_char(0x70, False) is None


def test_vk_to_char_builds_ty():
    assert vk_to_char(0xBF, 0) == "/"
    assert vk_to_char(0x54, 0) == "t"
    assert vk_to_char(0x59, 0) == "y"


def test_us_layout_digits_shift_and_whitespace():
    assert vk_to_char(0x31, 0) == "1"
    assert vk_to_char(0x31, MOD_SHIFT) == "!"
    assert vk_to_char(0xBF, MOD_SHIFT) == "?"
    assert vk_to_char(0x20, 0) == " "
    assert vk_to_char(0x0D, 0) == "\n"
    assert vk_to_char(0x09, 0) == "\t"
    assert vk_to_char(0x41, MOD_SHIFT) == "A"
    assert vk_to_char(0x41, MOD_CAPS) == "A"
    assert vk_to_char(0x41, MOD_SHIFT | MOD_CAPS) == "a"
