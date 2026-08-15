from expandr.store import data_dir, library_path


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
