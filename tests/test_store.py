import json

import pytest

from expandr.defaults import default_library
from expandr.store import data_dir, library_path, load_library, save_library


def test_data_dir_uses_textexpander_and_migrates_legacy(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    legacy = tmp_path / "Expandr"
    legacy.mkdir()
    (legacy / "library.json").write_text("{}", encoding="utf-8")
    path = data_dir()
    assert path.name == "TextExpander"
    assert (path / "library.json").exists()
    assert not legacy.exists()
    assert library_path() == path / "library.json"


def test_missing_library_writes_defaults(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    loaded = load_library()
    assert loaded.quarantined is None
    assert loaded.library.snippet_count() >= 1
    data = json.loads(library_path().read_text(encoding="utf-8"))
    assert "folders" in data


def test_corrupt_library_is_quarantined_not_overwritten(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    path = library_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "{not json"
    path.write_text(payload, encoding="utf-8")
    loaded = load_library()
    assert loaded.quarantined is not None
    assert loaded.quarantined.name.startswith("library.json.corrupt")
    assert loaded.quarantined.read_text(encoding="utf-8") == payload
    live = json.loads(library_path().read_text(encoding="utf-8"))
    assert live != payload
    assert "folders" in live
    assert loaded.library.snippet_count() >= 1


def test_unreadable_schema_is_quarantined(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    path = library_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{"folders": 1}', encoding="utf-8")
    loaded = load_library()
    assert loaded.quarantined is not None
    assert loaded.quarantined.read_text(encoding="utf-8") == '{"folders": 1}'
    assert "folders" in json.loads(library_path().read_text(encoding="utf-8"))


def test_second_corrupt_keeps_the_first_quarantine(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    path = library_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("first-bad", encoding="utf-8")
    first = load_library()
    path.write_text("second-bad", encoding="utf-8")
    second = load_library()
    assert first.quarantined is not None
    assert second.quarantined is not None
    assert first.quarantined != second.quarantined
    assert first.quarantined.read_text(encoding="utf-8") == "first-bad"
    assert second.quarantined.read_text(encoding="utf-8") == "second-bad"


def test_load_clears_a_persisted_pause_and_keeps_snippets(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    library = default_library()
    library.settings.paused = True
    save_library(library)
    before = [(snippet.shortcut, snippet.content) for _folder, snippet in library.all_snippets()]
    text_while_paused = library_path().read_text(encoding="utf-8")

    loaded = load_library()

    assert loaded.cleared_pause is True
    assert loaded.library.settings.paused is False
    after = [(snippet.shortcut, snippet.content) for _folder, snippet in loaded.library.all_snippets()]
    assert after == before
    saved = json.loads(library_path().read_text(encoding="utf-8"))
    assert saved["settings"]["paused"] is False
    assert "paused" in text_while_paused


def test_load_clears_pause_in_memory_when_the_rewrite_fails(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    library = default_library()
    library.settings.paused = True
    save_library(library)

    def boom(self, *_args, **_kwargs):
        raise OSError("read only")

    monkeypatch.setattr("pathlib.Path.write_text", boom)
    loaded = load_library()
    assert loaded.cleared_pause is True
    assert loaded.library.settings.paused is False


def test_load_does_not_rewrite_a_library_that_was_not_paused(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    library = default_library()
    save_library(library)
    text = library_path().read_text(encoding="utf-8")

    loaded = load_library()

    assert loaded.cleared_pause is False
    assert loaded.library.settings.paused is False
    assert library_path().read_text(encoding="utf-8") == text


def test_save_library_propagates_oserror(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    library = default_library()

    def boom(self, *_args, **_kwargs):
        raise OSError("disk full")

    monkeypatch.setattr("pathlib.Path.write_text", boom)
    with pytest.raises(OSError, match="disk full"):
        save_library(library)
