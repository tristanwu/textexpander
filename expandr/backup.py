from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import os
from pathlib import Path
import subprocess
import sys

from expandr.models import Library
from expandr.transfer import export_bundle


class BackupError(RuntimeError):
    pass


@dataclass(frozen=True)
class BackupResult:
    path: Path
    commit: str


def _runtime_dir() -> Path:
    if bool(getattr(sys, "frozen", False)):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def _run_git(repo: Path, *args: str) -> str:
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
            creationflags=flags,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        detail = getattr(exc, "stderr", "") or ""
        detail = detail.strip()
        message = f"Git could not create the backup commit{': ' + detail if detail else '.'}"
        raise BackupError(message) from exc
    return result.stdout.strip()


def find_repo_root(start: Path | None = None) -> Path:
    candidate = (start or _runtime_dir()).resolve()
    try:
        root = _run_git(candidate, "rev-parse", "--show-toplevel")
    except BackupError as exc:
        raise BackupError("TextExpander is not running from a Git repository.") from exc
    return Path(root)


def backups_dir(repo: Path | None = None) -> Path:
    return (repo or find_repo_root()) / "backups"


def list_backups(repo: Path | None = None) -> list[Path]:
    folder = backups_dir(repo)
    if not folder.exists():
        return []
    return sorted(folder.glob("textexpander-library-*.json"), reverse=True)


def _available_path(folder: Path, timestamp: str) -> Path:
    base = folder / f"textexpander-library-{timestamp}.json"
    if not base.exists():
        return base
    number = 2
    while True:
        candidate = folder / f"textexpander-library-{timestamp}-{number}.json"
        if not candidate.exists():
            return candidate
        number += 1


def create_backup(
    library: Library,
    *,
    repo: Path | None = None,
    now: datetime | None = None,
) -> BackupResult:
    root = find_repo_root(repo) if repo is not None else find_repo_root()
    created_at = now or datetime.now()
    folder = backups_dir(root)
    folder.mkdir(parents=True, exist_ok=True)
    path = _available_path(folder, created_at.strftime("%Y%m%d-%H%M%S"))
    export_bundle(library, path)

    relative = path.relative_to(root).as_posix()
    _run_git(root, "add", "--", relative)
    message = f"backup: TextExpander library {created_at:%Y-%m-%d %H:%M:%S}"
    _run_git(root, "commit", "--only", "-m", message, "--", relative)
    commit = _run_git(root, "rev-parse", "--short", "HEAD")
    return BackupResult(path=path, commit=commit)
