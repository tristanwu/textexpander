from __future__ import annotations

import sys
from pathlib import Path


def startup_dir() -> Path:
    return Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


def startup_bat() -> Path:
    return startup_dir() / "Expandr.bat"


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def launch_command() -> str:
    if is_frozen():
        return f'"{sys.executable}"'
    project = Path(__file__).resolve().parent.parent
    return f'"{sys.executable}" -m expandr'


def set_start_with_windows(enabled: bool) -> None:
    path = startup_bat()
    if not enabled:
        if path.exists():
            path.unlink()
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    if is_frozen():
        body = f"@echo off\nstart \"\" {launch_command()}\n"
    else:
        project = Path(__file__).resolve().parent.parent
        body = (
            "@echo off\n"
            f'cd /d "{project}"\n'
            f"start \"\" {launch_command()}\n"
        )
    path.write_text(body, encoding="utf-8")
