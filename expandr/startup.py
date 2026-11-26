from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
try:
    import winreg
except ImportError:  # non-Windows test runs
    winreg = None  # type: ignore[assignment]

from expandr.icon import write_ico
from expandr.identity import APP_NAME, LEGACY_APP_NAME
from expandr.shortcut import ShortcutSpec, create_shortcut
from expandr.store import data_dir

APPROVED_KEY = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\StartupFolder"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_APPROVED_KEY = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run"
ENABLED_VALUE = bytes([0x02, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
DISABLED_VALUE = bytes([0x03, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
DISABLED_FLAGS = (0x01, 0x03, 0x07, 0x09)


def startup_dir() -> Path:
    return Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


def startup_shortcut() -> Path:
    return startup_dir() / f"{APP_NAME}.lnk"


def obsolete_launchers() -> tuple[Path, ...]:
    roaming = os.environ.get("APPDATA")
    appdata = Path(roaming) if roaming else Path.home() / "AppData" / "Roaming"
    return (
        startup_dir() / f"{APP_NAME}.bat",
        startup_dir() / f"{LEGACY_APP_NAME}.bat",
        startup_dir() / f"{LEGACY_APP_NAME}.lnk",
        appdata / APP_NAME / f"{APP_NAME}-startup.bat",
    )


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def project_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def interpreter() -> Path:
    exe = Path(sys.executable)
    windowless = exe.with_name("pythonw.exe")
    return windowless if windowless.exists() else exe


def launcher_exe() -> Path:
    return interpreter().with_name(f"{APP_NAME}.exe")


def ensure_launcher_exe() -> Path:
    """Windows lists a startup entry under the name of the file it runs, not the shortcut.

    Running the app through a copy of the interpreter named TextExpander.exe makes Windows
    show the app's own name. The copy sits beside the interpreter so it keeps that
    environment's packages.
    """
    source = interpreter()
    launcher = launcher_exe()
    if launcher == source:
        return source
    try:
        if not launcher.exists() or launcher.stat().st_mtime < source.stat().st_mtime:
            shutil.copy2(source, launcher)
    except OSError:
        return source
    return launcher


def launch_target() -> tuple[str, str, str]:
    """Returns the executable, arguments, and working directory that start the app."""
    if is_frozen():
        exe = Path(sys.executable)
        return str(exe), "", str(exe.parent)
    return str(ensure_launcher_exe()), "-m expandr", str(project_dir())


def startup_shortcut_spec() -> ShortcutSpec:
    target, arguments, working = launch_target()
    return ShortcutSpec(
        path=startup_shortcut(),
        target=target,
        arguments=arguments,
        working_directory=working,
        icon=str(write_ico(data_dir() / "textexpander.ico")),
        description=f"Start {APP_NAME} when you sign in",
    )


def _target_record() -> Path:
    return data_dir() / "startup-target.txt"


def _read_target_record() -> str | None:
    try:
        return _target_record().read_text(encoding="utf-8").strip()
    except OSError:
        return None


def _write_target_record(signature: str) -> None:
    record = _target_record()
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text(signature, encoding="utf-8")


def _delete_value(key_path: str, name: str) -> None:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, name)
    except FileNotFoundError:
        pass


def _read_value(key_path: str, name: str):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ) as key:
            return winreg.QueryValueEx(key, name)[0]
    except FileNotFoundError:
        return None


def _remove_obsolete_launchers() -> None:
    for path in obsolete_launchers():
        if path.exists():
            path.unlink()
    for name in (APP_NAME, LEGACY_APP_NAME):
        _delete_value(RUN_KEY, name)
        _delete_value(RUN_APPROVED_KEY, name)


def _set_approved(enabled: bool) -> None:
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, APPROVED_KEY) as key:
        value = ENABLED_VALUE if enabled else DISABLED_VALUE
        winreg.SetValueEx(key, startup_shortcut().name, 0, winreg.REG_BINARY, value)


def _write_shortcut() -> None:
    spec = startup_shortcut_spec()
    create_shortcut(spec)
    _write_target_record(f"{spec.target}|{spec.arguments}|{spec.working_directory}")


def is_start_with_windows() -> bool:
    if not startup_shortcut().exists():
        return False
    approved = _read_value(APPROVED_KEY, startup_shortcut().name)
    if not isinstance(approved, bytes) or not approved:
        return True
    return approved[0] not in DISABLED_FLAGS


def ensure_startup_registration(default_enabled: bool) -> bool:
    """Keeps the app listed in Windows startup apps and reports whether Windows will start it."""
    _remove_obsolete_launchers()
    if not startup_shortcut().exists():
        _write_shortcut()
        _set_approved(default_enabled)
        return default_enabled
    target, arguments, working = launch_target()
    if _read_target_record() != f"{target}|{arguments}|{working}":
        _write_shortcut()
    return is_start_with_windows()


def set_start_with_windows(enabled: bool) -> None:
    _remove_obsolete_launchers()
    _write_shortcut()
    _set_approved(enabled)
