from __future__ import annotations

import os
import time

import ctypes
from ctypes import wintypes

from expandr.store import data_dir


def _load_kernel32():
    loader = getattr(ctypes, "WinDLL", None)
    if loader is None:
        return None
    try:
        return loader("kernel32", use_last_error=True)
    except OSError:
        return None


kernel32 = _load_kernel32()
TH32CS_SNAPPROCESS = 0x00000002
PROCESS_TERMINATE = 0x0001
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
STILL_ACTIVE = 259


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = (
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", wintypes.WCHAR * 260),
    )


def _bind_kernel32() -> None:
    kernel32.CreateToolhelp32Snapshot.argtypes = (wintypes.DWORD, wintypes.DWORD)
    kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel32.Process32FirstW.argtypes = (wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W))
    kernel32.Process32NextW.argtypes = (wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W))
    kernel32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.TerminateProcess.argtypes = (wintypes.HANDLE, wintypes.UINT)
    kernel32.GetExitCodeProcess.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
    kernel32.CreateMutexW.argtypes = (wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR)
    kernel32.CreateMutexW.restype = wintypes.HANDLE
    kernel32.SetLastError.argtypes = (wintypes.DWORD,)
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)


if kernel32 is not None:
    _bind_kernel32()

ERROR_ALREADY_EXISTS = 183
_mutex_handle = None


def iter_processes() -> list[tuple[int, str]]:
    snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if not snap or snap == wintypes.HANDLE(-1).value:
        return []
    try:
        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
        found: list[tuple[int, str]] = []
        if not kernel32.Process32FirstW(snap, ctypes.byref(entry)):
            return []
        while True:
            found.append((int(entry.th32ProcessID), entry.szExeFile))
            if not kernel32.Process32NextW(snap, ctypes.byref(entry)):
                break
        return found
    finally:
        kernel32.CloseHandle(snap)


def text_blaze_running() -> bool:
    return any(name.casefold() == "text blaze.exe" for _, name in iter_processes())


def _pid_alive(pid: int) -> bool:
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return False
    try:
        code = wintypes.DWORD()
        if kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
            return code.value == STILL_ACTIVE
        return True
    finally:
        kernel32.CloseHandle(handle)


def _terminate(pid: int) -> bool:
    handle = kernel32.OpenProcess(PROCESS_TERMINATE, False, pid)
    if not handle:
        return False
    try:
        return bool(kernel32.TerminateProcess(handle, 0))
    finally:
        kernel32.CloseHandle(handle)


def pid_path():
    return data_dir() / "expandr.pid"


def stop_other_expandr_instances() -> int:
    mine = os.getpid()
    parent = os.getppid()
    killed = 0
    path = pid_path()
    if path.exists():
        try:
            old = int(path.read_text(encoding="utf-8").strip())
        except ValueError:
            old = 0
        if old and old not in {mine, parent} and _pid_alive(old):
            if _terminate(old):
                killed += 1
            for _ in range(50):
                if not _pid_alive(old):
                    break
                time.sleep(0.02)
    path.write_text(str(mine), encoding="utf-8")
    return killed


def claim_singleton() -> bool:
    global _mutex_handle
    if _mutex_handle:
        return True
    kernel32.SetLastError(0)
    handle = kernel32.CreateMutexW(None, True, "Local\\TextExpanderSingleton")
    if ctypes.get_last_error() == ERROR_ALREADY_EXISTS:
        if handle:
            kernel32.CloseHandle(handle)
        return False
    _mutex_handle = handle
    return True


def become_only_instance() -> bool:
    stop_other_expandr_instances()
    for _ in range(25):
        if claim_singleton():
            return True
        time.sleep(0.04)
    return False
