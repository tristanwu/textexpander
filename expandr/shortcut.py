"""Creates Windows .lnk shortcuts. This is the Win32 shell boundary."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ShortcutSpec:
    path: Path
    target: str
    arguments: str = ""
    working_directory: str = ""
    icon: str = ""
    description: str = ""


def _quote(value: str) -> str:
    return value.replace("'", "''")


def create_shortcut(spec: ShortcutSpec) -> Path:
    spec.path.parent.mkdir(parents=True, exist_ok=True)
    script = (
        "$s = (New-Object -ComObject WScript.Shell).CreateShortcut('{path}');"
        "$s.TargetPath = '{target}';"
        "$s.Arguments = '{arguments}';"
        "$s.WorkingDirectory = '{working_directory}';"
        "$s.IconLocation = '{icon}';"
        "$s.Description = '{description}';"
        "$s.Save()"
    ).format(
        path=_quote(str(spec.path)),
        target=_quote(spec.target),
        arguments=_quote(spec.arguments),
        working_directory=_quote(spec.working_directory),
        icon=_quote(spec.icon),
        description=_quote(spec.description),
    )
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        capture_output=True,
        text=True,
        timeout=20,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    if completed.returncode != 0 or not spec.path.exists():
        raise RuntimeError(completed.stderr.strip() or f"Could not create {spec.path.name}.")
    return spec.path
