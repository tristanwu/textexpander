from expandr.keys import fallback_char, vk_to_char


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
