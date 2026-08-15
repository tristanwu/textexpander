import json

import pytest

from expandr.models import Folder, Library, Settings, Snippet, TriggerMode, new_id
from expandr.transfer import TransferError, export_bundle, import_bundle, read_bundle


def _library() -> Library:
    work = Folder(id="f1", name="Work", trigger=TriggerMode.ANYWHERE)
    work.snippets.append(
        Snippet(id="s1", label="Thanks", shortcut="/ty", content="Thank you", enabled=True)
    )
    personal = Folder(id="f2", name="Personal", trigger=TriggerMode.WORD_START)
    personal.snippets.append(
        Snippet(id="s2", label="Sig", shortcut="/sig", content="Best,\nAda", enabled=False)
    )
    return Library(
        folders=[work, personal],
        settings=Settings(disabled_apps=["game.exe"], start_with_windows=True, paused=True),
    )


def test_export_bundle_roundtrip_preserves_folders_and_snippets(tmp_path):
    path = tmp_path / "library.expandr.json"
    export_bundle(_library(), path)
    loaded = read_bundle(path)
    assert [folder.name for folder in loaded.folders] == ["Work", "Personal"]
    assert loaded.folders[0].trigger == TriggerMode.ANYWHERE
    assert loaded.folders[1].snippets[0].content == "Best,\nAda"
    assert loaded.folders[1].snippets[0].enabled is False
    assert loaded.settings.disabled_apps == ["game.exe"]


def test_export_bundle_is_tagged_json(tmp_path):
    path = tmp_path / "out.json"
    export_bundle(_library(), path)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["format"] == "expandr-library"
    assert data["version"] == 1
    assert "folders" in data["library"]


def test_read_bundle_accepts_raw_appdata_library_json(tmp_path):
    path = tmp_path / "library.json"
    path.write_text(json.dumps(_library().to_dict()), encoding="utf-8")
    loaded = read_bundle(path)
    assert loaded.snippet_count() == 2
    assert loaded.folders[0].name == "Work"


def test_read_bundle_rejects_garbage(tmp_path):
    path = tmp_path / "nope.json"
    path.write_text('{"hello": 1}', encoding="utf-8")
    with pytest.raises(TransferError):
        read_bundle(path)


def test_import_replace_swaps_snippets_and_unpauses(tmp_path):
    dest = Library(
        folders=[Folder(id="old", name="Old", snippets=[Snippet(id="x", label="X", shortcut="/x", content="x")])],
        settings=Settings(paused=True, start_with_windows=False, seen_coach=True),
    )
    path = tmp_path / "bundle.json"
    export_bundle(_library(), path)
    result = import_bundle(dest, path, merge=False)
    assert result.replaced is True
    assert dest.snippet_count() == 2
    assert dest.find_by_shortcut("/ty") is not None
    assert dest.find_by_shortcut("/x") is None
    assert dest.settings.paused is False
    assert dest.settings.seen_coach is True
    assert dest.settings.disabled_apps == ["game.exe"]


def test_import_merge_adds_new_and_updates_same_id(tmp_path):
    dest = Library(
        folders=[
            Folder(
                id="f1",
                name="Work",
                snippets=[Snippet(id="s1", label="Old thanks", shortcut="/ty", content="old")],
            )
        ]
    )
    dest.folders[0].snippets.append(Snippet(id="keep", label="Keep", shortcut="/keep", content="stay"))
    path = tmp_path / "bundle.json"
    export_bundle(_library(), path)
    result = import_bundle(dest, path, merge=True)
    assert result.replaced is False
    thanks = dest.find_snippet("s1")
    assert thanks is not None
    assert thanks[1].content == "Thank you"
    assert thanks[1].label == "Thanks"
    assert dest.find_snippet("keep") is not None
    assert dest.find_snippet("s2") is not None
    assert dest.snippet_count() == 3
