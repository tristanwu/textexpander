import json

from expandr.session.store import (
    append_chunk,
    append_event,
    delete_session,
    list_sessions,
    load_chunks,
    load_events,
    load_session,
    repair_orphans,
    sessions_dir,
    start_session,
    stop_session,
    write_transcript,
)


def test_start_stop_writes_session_outside_library_json(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    meta = start_session(title="Session · Sat 5:55 PM")
    assert meta.status == "live"
    assert meta.schema_version == 1
    folder = sessions_dir() / meta.folder
    assert folder.is_dir()
    assert (folder / "session.json").exists()
    assert not (tmp_path / "TextExpander" / "library.json").exists()
    stop_session(meta, reason="stop")
    loaded = load_session(meta.id)
    assert loaded.status == "stopped"
    assert loaded.ended_reason == "stop"
    assert loaded.ended_at


def test_append_event_and_ignore_partial_last_line(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    meta = start_session()
    append_event(meta, {"schema_version": 1, "session_id": meta.id, "kind": "char", "char": "a", "app": "cursor.exe"})
    path = sessions_dir() / meta.folder / "events.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        handle.write('{"kind": "char", "char": "b"')
    events = load_events(meta)
    assert [item["char"] for item in events] == ["a"]


def test_rotation_closes_live_file_and_keeps_session(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    meta = start_session()
    payload = {"schema_version": 1, "session_id": meta.id, "kind": "char", "char": "x" * 80, "app": "cursor.exe"}
    for _ in range(8):
        append_event(meta, payload, rotate_bytes=200)
    folder = sessions_dir() / meta.folder
    rotated = sorted(folder.glob("events-*.jsonl"))
    assert rotated
    assert (folder / "events.jsonl").exists()
    events = load_events(meta)
    assert len(events) == 8


def test_crash_repair_marks_orphan_quit_and_does_not_resume(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    meta = start_session()
    repaired = repair_orphans()
    assert any(item.id == meta.id for item in repaired)
    loaded = load_session(meta.id)
    assert loaded.status == "stopped"
    assert loaded.ended_reason == "quit"
    assert list_sessions()[0].status == "stopped"


def test_chunks_and_transcript_are_chronological(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    meta = start_session(title="Tuesday")
    append_chunk(
        meta,
        {
            "chunk_id": "c1",
            "app": "cursor.exe",
            "t_start": "2026-08-22T23:00:00Z",
            "t_end": "2026-08-22T23:00:10Z",
            "text": "fix this",
            "flush_reason": "app_switch",
        },
    )
    append_chunk(
        meta,
        {
            "chunk_id": "c2",
            "app": "chrome.exe",
            "t_start": "2026-08-22T23:00:10Z",
            "t_end": "2026-08-22T23:00:20Z",
            "text": "search traceback",
            "flush_reason": "enter",
        },
    )
    chunks = load_chunks(meta)
    assert [item["app"] for item in chunks] == ["cursor.exe", "chrome.exe"]
    path = write_transcript(meta)
    text = path.read_text(encoding="utf-8")
    assert "cursor.exe" in text
    assert text.index("fix this") < text.index("search traceback")


def test_delete_session_removes_folder_not_library(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    library = tmp_path / "TextExpander" / "library.json"
    library.parent.mkdir(parents=True)
    library.write_text("{}", encoding="utf-8")
    meta = start_session()
    delete_session(meta.id)
    assert list_sessions() == []
    assert library.exists()
