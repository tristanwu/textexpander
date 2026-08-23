from datetime import datetime
import subprocess

import pytest

from expandr.backup import BackupError, create_backup, find_repo_root, list_backups
from expandr.models import Folder, Library, Snippet
from expandr.transfer import read_bundle


def _git(repo, *args):
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.name", "Backup Test")
    _git(repo, "config", "user.email", "backup@example.com")
    return repo


def _library():
    return Library(
        folders=[
            Folder(
                id="folder",
                name="Personal",
                snippets=[Snippet(id="snippet", label="Thanks", shortcut="/ty", content="Thank you")],
            )
        ]
    )


def test_create_backup_exports_to_repo_and_commits_only_backup(tmp_path):
    repo = _repo(tmp_path)
    unrelated = repo / "notes.txt"
    unrelated.write_text("do not commit", encoding="utf-8")
    _git(repo, "add", "notes.txt")

    result = create_backup(
        _library(),
        repo=repo,
        now=datetime(2026, 8, 22, 17, 17, 0),
    )

    assert result.path == repo / "backups" / "textexpander-library-20260822-171700.json"
    assert read_bundle(result.path).find_by_shortcut("/ty") is not None
    assert _git(repo, "log", "-1", "--format=%s") == "backup: TextExpander library 2026-08-22 17:17:00"
    assert _git(repo, "show", "--format=", "--name-only", "HEAD") == (
        "backups/textexpander-library-20260822-171700.json"
    )
    assert _git(repo, "diff", "--cached", "--name-only") == "notes.txt"


def test_list_backups_returns_newest_json_first(tmp_path):
    folder = tmp_path / "backups"
    folder.mkdir()
    older = folder / "textexpander-library-20260821-120000.json"
    newer = folder / "textexpander-library-20260822-120000.json"
    older.write_text("{}", encoding="utf-8")
    newer.write_text("{}", encoding="utf-8")
    (folder / "readme.txt").write_text("ignore", encoding="utf-8")

    assert list_backups(tmp_path) == [newer, older]


def test_find_repo_root_reports_non_repo(tmp_path):
    with pytest.raises(BackupError, match="Git repository"):
        find_repo_root(tmp_path)


def test_create_backup_does_not_walk_appdata_sessions(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path / "app"))
    from expandr.session.store import start_session

    start_session(title="Secret trail")
    repo = _repo(tmp_path)
    result = create_backup(_library(), repo=repo, now=datetime(2026, 8, 22, 18, 0, 0))
    names = _git(repo, "show", "--format=", "--name-only", "HEAD")
    payload = result.path.read_text(encoding="utf-8")
    assert "sessions" not in names
    assert "Secret trail" not in payload
    assert "events.jsonl" not in payload
