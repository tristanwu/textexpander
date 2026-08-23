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


def test_save_library_propagates_oserror(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    library = default_library()

    def boom(self, *_args, **_kwargs):
        raise OSError("disk full")

    monkeypatch.setattr("pathlib.Path.write_text", boom)
    with pytest.raises(OSError, match="disk full"):
        save_library(library)
