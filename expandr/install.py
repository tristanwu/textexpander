from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from expandr.icon import write_ico
from expandr.identity import APP_NAME, LEGACY_APP_NAME
from expandr.startup import is_frozen
from expandr.store import data_dir


def start_menu_dir() -> Path:
    return Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs"


def start_menu_shortcut() -> Path:
    return start_menu_dir() / f"{APP_NAME}.lnk"


def is_on_start_menu() -> bool:
    return start_menu_shortcut().exists()


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def shortcut_spec() -> dict[str, str]:
    ico = write_ico(data_dir() / "textexpander.ico")
    if is_frozen():
        target = Path(sys.executable)
        arguments = ""
        working = str(target.parent)
    else:
        target = Path(sys.executable)
        if target.name.casefold() == "python.exe":
            target = target.with_name("pythonw.exe")
            if not target.exists():
                target = Path(sys.executable)
        arguments = "-m expandr"
        working = str(project_root())
    return {
        "name": APP_NAME,
        "path": str(start_menu_shortcut()),
        "target": str(target),
        "arguments": arguments,
        "working_directory": working,
        "icon": str(ico),
        "description": f"{APP_NAME} text expander",
    }


def install_start_menu() -> Path:
    spec = shortcut_spec()
    start_menu_dir().mkdir(parents=True, exist_ok=True)
    _remove_legacy_shortcut()
    script = (
        "$s = (New-Object -ComObject WScript.Shell).CreateShortcut('{path}');"
        "$s.TargetPath = '{target}';"
        "$s.Arguments = '{arguments}';"
        "$s.WorkingDirectory = '{working_directory}';"
        "$s.IconLocation = '{icon}';"
        "$s.Description = '{description}';"
        "$s.Save()"
    ).format(
        path=_ps(spec["path"]),
        target=_ps(spec["target"]),
        arguments=_ps(spec["arguments"]),
        working_directory=_ps(spec["working_directory"]),
        icon=_ps(spec["icon"]),
        description=_ps(spec["description"]),
    )
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        capture_output=True,
        text=True,
        timeout=20,
    )
    path = start_menu_shortcut()
    if completed.returncode != 0 or not path.exists():
        raise RuntimeError(completed.stderr.strip() or "Could not create the Start menu shortcut.")
    return path


def uninstall_start_menu() -> None:
    path = start_menu_shortcut()
    if path.exists():
        path.unlink()
    _remove_legacy_shortcut()


def _remove_legacy_shortcut() -> None:
    legacy = start_menu_dir() / f"{LEGACY_APP_NAME}.lnk"
    if legacy.exists():
        legacy.unlink()


def _ps(value: str) -> str:
    return value.replace("'", "''")


def main() -> None:
    path = install_start_menu()
    print(f"Start menu shortcut: {path}")


if __name__ == "__main__":
    main()
