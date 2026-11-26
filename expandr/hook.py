from __future__ import annotations

import ctypes
import threading
import time
from ctypes import wintypes
from dataclasses import dataclass

from expandr.keys import (
    MOD_ALT,
    MOD_CTRL,
    MOD_SHIFT,
    VK_BACK,
    VK_CONTROL,
    VK_ESCAPE,
    VK_MENU,
    VK_OEM_2,
    VK_SHIFT,
    vk_to_char,
)
from expandr.matcher import find_matches, has_longer_prefix
from expandr.models import Library, Snippet
from expandr.win32api import EXPANDR_EXTRA

WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_SYSKEYDOWN = 0x0104
WM_QUIT = 0x0012
WM_APP_KEY = 0x8001
HC_ACTION = 0
PM_NOREMOVE = 0
PREFIX_WAIT_S = 0.35
_API = None


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = (
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    )


def _hookproc_type():
    factory = getattr(ctypes, "WINFUNCTYPE", None)
    if factory is None:
        return None
    return factory(ctypes.c_longlong, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)


HOOKPROC = _hookproc_type()


def _hook_api():
    """Bind the low-level hook on first use. Importing this module does not load user32."""
    global _API
    if _API is not None:
        return _API
    loader = getattr(ctypes, "WinDLL", None)
    if loader is None:
        raise OSError("user32 is unavailable")
    from expandr.win32api import user32

    if user32 is None:
        raise OSError("user32 is unavailable")
    user32.SetWindowsHookExW.argtypes = (ctypes.c_int, HOOKPROC, wintypes.HINSTANCE, wintypes.DWORD)
    user32.SetWindowsHookExW.restype = wintypes.HHOOK
    user32.CallNextHookEx.argtypes = (wintypes.HHOOK, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)
    user32.CallNextHookEx.restype = ctypes.c_longlong
    user32.UnhookWindowsHookEx.argtypes = (wintypes.HHOOK,)
    user32.GetMessageW.argtypes = (ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT)
    user32.PeekMessageW.argtypes = (
        ctypes.POINTER(wintypes.MSG),
        wintypes.HWND,
        wintypes.UINT,
        wintypes.UINT,
        wintypes.UINT,
    )
    user32.TranslateMessage.argtypes = (ctypes.POINTER(wintypes.MSG),)
    user32.DispatchMessageW.argtypes = (ctypes.POINTER(wintypes.MSG),)
    user32.PostThreadMessageW.argtypes = (wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
    user32.GetAsyncKeyState.argtypes = (ctypes.c_int,)
    user32.GetAsyncKeyState.restype = wintypes.SHORT
    kernel32 = loader("kernel32", use_last_error=True)
    kernel32.GetModuleHandleW.argtypes = (wintypes.LPCWSTR,)
    kernel32.GetModuleHandleW.restype = wintypes.HMODULE
    kernel32.GetCurrentThreadId.restype = wintypes.DWORD
    _API = (user32, kernel32)
    return _API


def _mods_now(user32) -> int:
    mods = 0
    if user32.GetAsyncKeyState(VK_SHIFT) & 0x8000:
        mods |= MOD_SHIFT
    if user32.GetAsyncKeyState(VK_CONTROL) & 0x8000:
        mods |= MOD_CTRL
    if user32.GetAsyncKeyState(VK_MENU) & 0x8000:
        mods |= MOD_ALT
    return mods


@dataclass
class MatchEvent:
    snippet: Snippet
    delete_count: int
    hwnd: int
    suffix: str = ""


class KeyboardEngine:
    """Matches shortcuts from posted key events.

    Pause is not a hook chord. Ctrl+Shift+P is an ordinary modified key
    (ADR 0010) so a command palette cannot silence expansion.
    """

    def __init__(
        self,
        library_provider,
        on_match,
        on_search,
        on_pause,
        is_paused,
        is_app_disabled,
        on_key=None,
        *,
        foreground=None,
    ):
        self._library_provider = library_provider
        self._on_match = on_match
        self._on_search = on_search
        # Retained so callers can still pass a callback. The hook does not bind a pause chord (ADR 0010).
        self._on_pause = on_pause
        self._is_paused = is_paused
        self._is_app_disabled = is_app_disabled
        self._on_key = on_key
        self._foreground_provider = foreground
        self._buffer = ""
        self._hook = None
        self._thread: threading.Thread | None = None
        self._thread_id = 0
        self._proc = HOOKPROC(self._callback) if HOOKPROC is not None else None
        self._lock = threading.RLock()
        self._pending: tuple[Snippet, int, int, str] | None = None
        self._pending_at = 0.0
        self._timer: threading.Timer | None = None
        self.busy = False
        self.hook_ok = False
        self.hook_error = 0
        self.last_heard = ""
        self.last_expand = ""
        self.last_insert = ""
        self.keys_seen = 0

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, name="expandr-hook", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._timer:
            self._timer.cancel()
            self._timer = None
        hook = self._hook
        self._hook = None
        user32 = None
        if hook or self._thread_id:
            try:
                user32, _kernel32 = _hook_api()
            except OSError:
                user32 = None
        if hook and user32 is not None:
            try:
                user32.UnhookWindowsHookEx(hook)
            except Exception:
                pass
        self.hook_ok = False
        if self._thread_id and user32 is not None:
            user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.4)

    def clear(self) -> None:
        with self._lock:
            self._buffer = ""
            self._pending = None

    def status(self) -> dict:
        with self._lock:
            buffer = self._buffer
        return {
            "hook_ok": self.hook_ok,
            "hook_error": self.hook_error,
            "buffer": buffer,
            "last_heard": self.last_heard,
            "last_expand": self.last_expand,
            "last_insert": self.last_insert,
            "keys_seen": self.keys_seen,
        }

    def _run(self) -> None:
        user32, kernel32 = _hook_api()
        self._thread_id = kernel32.GetCurrentThreadId()
        msg = wintypes.MSG()
        user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, PM_NOREMOVE)
        handle = kernel32.GetModuleHandleW(None)
        self._hook = user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._proc, handle, 0)
        if not self._hook:
            self.hook_ok = False
            self.hook_error = ctypes.get_last_error()
            return
        self.hook_ok = True
        while True:
            result = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if result == 0 or result == -1:
                break
            if msg.message == WM_APP_KEY:
                self._handle_key(int(msg.wParam), int(msg.lParam))
                continue
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
        if self._hook:
            user32.UnhookWindowsHookEx(self._hook)
            self._hook = None
        self.hook_ok = False

    def _callback(self, n_code, w_param, l_param):
        user32, _kernel32 = _hook_api()
        try:
            if n_code == HC_ACTION and w_param in (WM_KEYDOWN, WM_SYSKEYDOWN) and self._thread_id:
                info = ctypes.cast(l_param, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
                if info.dwExtraInfo != EXPANDR_EXTRA:
                    user32.PostThreadMessageW(self._thread_id, WM_APP_KEY, info.vkCode, _mods_now(user32))
        except Exception:
            pass
        return user32.CallNextHookEx(self._hook, n_code, w_param, l_param)

    def _foreground(self) -> int:
        if self._foreground_provider is not None:
            return int(self._foreground_provider() or 0)
        try:
            from expandr.win32api import foreground_hwnd

            return int(foreground_hwnd() or 0)
        except OSError:
            return 0

    def _handle_key(self, vk: int, mods: int) -> None:
        self.keys_seen += 1
        if (mods & MOD_CTRL) and (mods & MOD_SHIFT) and vk == VK_OEM_2:
            self.clear()
            self._on_search()
            return
        if self._on_key:
            try:
                self._on_key(vk, mods, self._foreground())
            except Exception:
                pass
        if self.busy or self._is_paused():
            return
        if mods & (MOD_CTRL | MOD_ALT):
            self.clear()
            return
        if vk == VK_ESCAPE:
            self.clear()
            return
        if vk == VK_BACK:
            with self._lock:
                self._buffer = self._buffer[:-1]
                self.last_heard = self._buffer
                self._pending = None
            return

        char = vk_to_char(vk, mods)
        if char is None or (len(char) != 1 and char not in {"\n", "\t"}):
            return

        with self._lock:
            self._buffer = (self._buffer + char)[-160:]
            self.last_heard = self._buffer
            self._evaluate_locked()

    def _evaluate_locked(self) -> None:
        library: Library = self._library_provider()
        matches = find_matches(self._buffer, library)
        if not matches:
            self._pending = None
            return
        snippet, delete, suffix = matches[0]
        hwnd = self._foreground()
        if has_longer_prefix(self._buffer, library):
            self._pending = (snippet, delete, hwnd, suffix)
            self._pending_at = time.time()
            if self._timer:
                self._timer.cancel()
            self._timer = threading.Timer(PREFIX_WAIT_S, self._flush_pending)
            self._timer.daemon = True
            self._timer.start()
            return
        self._pending = None
        self._fire(snippet, delete, hwnd, suffix)

    def _flush_pending(self) -> None:
        with self._lock:
            if not self._pending:
                return
            if time.time() - self._pending_at < PREFIX_WAIT_S - 0.02:
                return
            snippet, delete, hwnd, suffix = self._pending
            self._pending = None
        self._fire(snippet, delete, hwnd, suffix)

    def _fire(self, snippet: Snippet, delete: int, hwnd: int, suffix: str = "") -> None:
        with self._lock:
            self._buffer = ""
        self.last_expand = snippet.shortcut
        self._on_match(MatchEvent(snippet=snippet, delete_count=delete, hwnd=hwnd, suffix=suffix))
