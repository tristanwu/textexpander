from __future__ import annotations

import ctypes
import time
from ctypes import wintypes
from pathlib import Path

def _load_dll(name: str):
    loader = getattr(ctypes, "WinDLL", None)
    if loader is None:
        return None
    try:
        return loader(name, use_last_error=True)
    except OSError:
        return None


user32 = _load_dll("user32")
kernel32 = _load_dll("kernel32")

KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_SCANCODE = 0x0008
INPUT_KEYBOARD = 1
EXPANDR_EXTRA = 0xE8A1D01
MAPVK_VK_TO_VSC = 0
VK_BACK = 0x08
VK_TAB = 0x09
VK_RETURN = 0x0D
VK_CONTROL = 0x11
VK_SHIFT = 0x10
VK_MENU = 0x12
VK_LEFT = 0x25
VK_V = 0x56
CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


class MOUSEINPUT(ctypes.Structure):
    _fields_ = (
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    )


class KEYBDINPUT(ctypes.Structure):
    _fields_ = (
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    )


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = (
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    )


class _INPUTUNION(ctypes.Union):
    _fields_ = (("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT))


class INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = (("type", wintypes.DWORD), ("u", _INPUTUNION))


def _bind_win32() -> None:
    user32.SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
    user32.SendInput.restype = wintypes.UINT
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.SetForegroundWindow.argtypes = (wintypes.HWND,)
    user32.SetForegroundWindow.restype = wintypes.BOOL
    user32.GetWindowThreadProcessId.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.DWORD))
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    user32.AttachThreadInput.argtypes = (wintypes.DWORD, wintypes.DWORD, wintypes.BOOL)
    user32.MapVirtualKeyW.argtypes = (wintypes.UINT, wintypes.UINT)
    user32.MapVirtualKeyW.restype = wintypes.UINT
    user32.GetAsyncKeyState.argtypes = (ctypes.c_int,)
    user32.GetAsyncKeyState.restype = wintypes.SHORT
    user32.OpenClipboard.argtypes = (wintypes.HWND,)
    user32.OpenClipboard.restype = wintypes.BOOL
    user32.CloseClipboard.restype = wintypes.BOOL
    user32.EmptyClipboard.restype = wintypes.BOOL
    user32.SetClipboardData.argtypes = (wintypes.UINT, wintypes.HANDLE)
    user32.SetClipboardData.restype = wintypes.HANDLE
    user32.GetClipboardData.argtypes = (wintypes.UINT,)
    user32.GetClipboardData.restype = wintypes.HANDLE
    user32.IsClipboardFormatAvailable.argtypes = (wintypes.UINT,)
    user32.IsClipboardFormatAvailable.restype = wintypes.BOOL

    kernel32.GlobalAlloc.argtypes = (wintypes.UINT, ctypes.c_size_t)
    kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
    kernel32.GlobalLock.argtypes = (wintypes.HGLOBAL,)
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalUnlock.argtypes = (wintypes.HGLOBAL,)
    kernel32.GlobalSize.argtypes = (wintypes.HGLOBAL,)
    kernel32.GlobalSize.restype = ctypes.c_size_t
    kernel32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel32.QueryFullProcessImageNameW.argtypes = (
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.LPWSTR,
        ctypes.POINTER(wintypes.DWORD),
    )
    kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
    kernel32.GetCurrentThreadId.restype = wintypes.DWORD
    kernel32.GetClipboardSequenceNumber.restype = wintypes.DWORD


if user32 is not None and kernel32 is not None:
    _bind_win32()


def _key(vk: int, flags: int = 0, scan: int = 0) -> INPUT:
    if not scan and vk:
        scan = user32.MapVirtualKeyW(vk, MAPVK_VK_TO_VSC)
    event = INPUT()
    event.type = INPUT_KEYBOARD
    event.ki = KEYBDINPUT(vk, scan, flags, 0, EXPANDR_EXTRA)
    return event


def _unicode(code: int, flags: int = 0) -> INPUT:
    return _key(0, KEYEVENTF_UNICODE | flags, code)


def send_keys(events: list[INPUT]) -> bool:
    if not events:
        return True
    array = (INPUT * len(events))(*events)
    sent = user32.SendInput(len(events), array, ctypes.sizeof(INPUT))
    return sent == len(events)


def tap(vk: int) -> bool:
    return send_keys([_key(vk, 0), _key(vk, KEYEVENTF_KEYUP)])


def send_backspaces(count: int) -> bool:
    events: list[INPUT] = []
    for _ in range(max(0, count)):
        events.extend([_key(VK_BACK, 0), _key(VK_BACK, KEYEVENTF_KEYUP)])
    return send_keys(events)


def send_left(count: int) -> bool:
    events: list[INPUT] = []
    for _ in range(max(0, count)):
        events.extend([_key(VK_LEFT, 0), _key(VK_LEFT, KEYEVENTF_KEYUP)])
    return send_keys(events)


def send_ctrl_v() -> bool:
    return send_keys(
        [
            _key(VK_CONTROL, 0),
            _key(VK_V, 0),
            _key(VK_V, KEYEVENTF_KEYUP),
            _key(VK_CONTROL, KEYEVENTF_KEYUP),
        ]
    )


def send_text(text: str) -> bool:
    events: list[INPUT] = []
    ok = True
    for char in text:
        if char == "\n":
            events.extend([_key(VK_RETURN, 0), _key(VK_RETURN, KEYEVENTF_KEYUP)])
        elif char == "\t":
            events.extend([_key(VK_TAB, 0), _key(VK_TAB, KEYEVENTF_KEYUP)])
        else:
            code = ord(char)
            events.extend([_unicode(code, 0), _unicode(code, KEYEVENTF_KEYUP)])
        if len(events) >= 64:
            ok = send_keys(events) and ok
            events.clear()
    return send_keys(events) and ok


def wait_keys_up(timeout: float = 0.25) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not (ctrl_down() or shift_down() or alt_down()):
            return
        time.sleep(0.01)


def modifier_down() -> bool:
    return bool(
        user32.GetAsyncKeyState(VK_CONTROL) & 0x8000
        or user32.GetAsyncKeyState(VK_MENU) & 0x8000
        or user32.GetAsyncKeyState(VK_SHIFT) & 0x8000
        and False
    )


def ctrl_down() -> bool:
    return bool(user32.GetAsyncKeyState(VK_CONTROL) & 0x8000)


def shift_down() -> bool:
    return bool(user32.GetAsyncKeyState(VK_SHIFT) & 0x8000)


def alt_down() -> bool:
    return bool(user32.GetAsyncKeyState(VK_MENU) & 0x8000)


def foreground_hwnd() -> int:
    if user32 is None:
        raise OSError("user32 is unavailable")
    return int(user32.GetForegroundWindow() or 0)


def focus_hwnd(hwnd: int) -> None:
    if not hwnd:
        return
    current = user32.GetForegroundWindow()
    if current == hwnd:
        return
    pid = wintypes.DWORD()
    target_tid = user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    current_tid = kernel32.GetCurrentThreadId()
    attached = False
    if target_tid and target_tid != current_tid:
        attached = bool(user32.AttachThreadInput(current_tid, target_tid, True))
    try:
        user32.SetForegroundWindow(hwnd)
        time.sleep(0.03)
    finally:
        if attached:
            user32.AttachThreadInput(current_tid, target_tid, False)


def process_name(hwnd: int) -> str:
    if not hwnd:
        return ""
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
    if not handle:
        return ""
    try:
        size = wintypes.DWORD(32768)
        buf = ctypes.create_unicode_buffer(size.value)
        if kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
            return Path(buf.value).name.casefold()
    finally:
        kernel32.CloseHandle(handle)
    return ""


def foreground_process_name() -> str:
    return process_name(int(user32.GetForegroundWindow() or 0))


def _open_clipboard(retries: int = 8) -> bool:
    for _ in range(retries):
        if user32.OpenClipboard(None):
            return True
        time.sleep(0.02)
    return False


def clipboard_sequence() -> int:
    if kernel32 is None:
        raise OSError("kernel32 is unavailable")
    return int(kernel32.GetClipboardSequenceNumber())


def get_clipboard_text() -> str | None:
    if not user32.IsClipboardFormatAvailable(CF_UNICODETEXT):
        return None
    if not _open_clipboard():
        return None
    try:
        handle = user32.GetClipboardData(CF_UNICODETEXT)
        if not handle:
            return None
        ptr = kernel32.GlobalLock(handle)
        if not ptr:
            return None
        try:
            return ctypes.wstring_at(ptr)
        finally:
            kernel32.GlobalUnlock(handle)
    finally:
        user32.CloseClipboard()


def set_clipboard_text(text: str) -> bool:
    data = text.encode("utf-16-le") + b"\x00\x00"
    handle = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
    if not handle:
        return False
    ptr = kernel32.GlobalLock(handle)
    if not ptr:
        return False
    ctypes.memmove(ptr, data, len(data))
    kernel32.GlobalUnlock(handle)
    if not _open_clipboard():
        return False
    try:
        user32.EmptyClipboard()
        if not user32.SetClipboardData(CF_UNICODETEXT, handle):
            return False
        handle = None
        return True
    finally:
        user32.CloseClipboard()
