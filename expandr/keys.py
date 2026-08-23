from __future__ import annotations

VK_BACK = 0x08
VK_TAB = 0x09
VK_RETURN = 0x0D
VK_ESCAPE = 0x1B
VK_SPACE = 0x20
VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_MENU = 0x12
VK_CAPITAL = 0x14
VK_A = 0x41
VK_Z = 0x5A
VK_OEM_2 = 0xBF
VK_P = 0x50
VK_V = 0x56
VK_INSERT = 0x2D

MOD_SHIFT = 1
MOD_CTRL = 2
MOD_ALT = 4
MOD_CAPS = 8

US_UNSHIFTED = {
    0x30: "0",
    0x31: "1",
    0x32: "2",
    0x33: "3",
    0x34: "4",
    0x35: "5",
    0x36: "6",
    0x37: "7",
    0x38: "8",
    0x39: "9",
    VK_SPACE: " ",
    0xBA: ";",
    0xBB: "=",
    0xBC: ",",
    0xBD: "-",
    0xBE: ".",
    VK_OEM_2: "/",
    0xC0: "`",
    0xDB: "[",
    0xDC: "\\",
    0xDD: "]",
    0xDE: "'",
}
US_SHIFTED = {
    0x30: ")",
    0x31: "!",
    0x32: "@",
    0x33: "#",
    0x34: "$",
    0x35: "%",
    0x36: "^",
    0x37: "&",
    0x38: "*",
    0x39: "(",
    VK_SPACE: " ",
    0xBA: ":",
    0xBB: "+",
    0xBC: "<",
    0xBD: "_",
    0xBE: ">",
    VK_OEM_2: "?",
    0xC0: "~",
    0xDB: "{",
    0xDC: "|",
    0xDD: "}",
    0xDE: '"',
}


def fallback_char(vk: int, shift: bool, caps: bool = False) -> str | None:
    if VK_A <= vk <= VK_Z:
        upper = bool(shift) ^ bool(caps)
        letter = chr(vk)
        return letter if upper else letter.lower()
    table = US_SHIFTED if shift else US_UNSHIFTED
    return table.get(vk)


def vk_to_char(vk: int, mods: int) -> str | None:
    if vk == VK_RETURN:
        return "\n"
    if vk == VK_TAB:
        return "\t"
    return fallback_char(vk, bool(mods & MOD_SHIFT), bool(mods & MOD_CAPS))
