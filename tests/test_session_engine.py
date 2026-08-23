from expandr.keys import MOD_CTRL, VK_RETURN, VK_V
from expandr.session.engine import SessionRecorder
from expandr.session.store import load_chunks, load_events, load_session


def _recorder(tmp_path, monkeypatch, **kwargs):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    apps = {1: "cursor.exe", 2: "chrome.exe", 3: "keepass.exe"}
    return SessionRecorder(
        skip_provider=lambda: ["keepass.exe", "textexpander.exe"],
        resolve_app=lambda hwnd: apps.get(hwnd, "unknown.exe"),
        **kwargs,
    )


def test_typed_chars_become_a_chunk_on_enter(tmp_path, monkeypatch):
    recorder = _recorder(tmp_path, monkeypatch)
    recorder.start(title="Work", run_writer=False)
    for vk in (0x41, 0x42, 0x43):  # A B C
        recorder.enqueue(vk, 0, 1)
    recorder.enqueue(VK_RETURN, 0, 1)
    recorder.stop()
    events = load_events(recorder.meta)
    assert [item["kind"] for item in events] == ["char", "char", "char", "enter"]
    chunks = load_chunks(recorder.meta)
    assert chunks[0]["text"] == "abc"
    assert chunks[0]["flush_reason"] == "enter"
    assert chunks[0]["app"] == "cursor.exe"


def test_backspace_stays_in_events_and_edits_projected_text(tmp_path, monkeypatch):
    recorder = _recorder(tmp_path, monkeypatch)
    recorder.start(run_writer=False)
    recorder.enqueue(0x41, 0, 1)
    recorder.enqueue(0x42, 0, 1)
    recorder.enqueue(0x08, 0, 1)  # backspace
    recorder.enqueue(0x43, 0, 1)
    recorder.enqueue(VK_RETURN, 0, 1)
    recorder.stop()
    kinds = [item["kind"] for item in load_events(recorder.meta)]
    assert "backspace" in kinds
    assert load_chunks(recorder.meta)[0]["text"] == "ac"
    assert load_chunks(recorder.meta)[0]["backspace_count"] == 1


def test_app_switch_flushes_chunk(tmp_path, monkeypatch):
    recorder = _recorder(tmp_path, monkeypatch)
    recorder.start(run_writer=False)
    recorder.enqueue(0x41, 0, 1)
    recorder.enqueue(0x42, 0, 2)
    recorder.stop()
    chunks = load_chunks(recorder.meta)
    assert [item["app"] for item in chunks] == ["cursor.exe", "chrome.exe"]
    assert chunks[0]["flush_reason"] == "app_switch"


def test_skip_list_writes_skip_not_text(tmp_path, monkeypatch):
    recorder = _recorder(tmp_path, monkeypatch)
    recorder.start(run_writer=False)
    recorder.enqueue(0x41, 0, 3)
    recorder.stop()
    events = load_events(recorder.meta)
    assert events[0]["kind"] == "skip"
    assert events[0]["app"] == "keepass.exe"
    assert "vk" not in events[0]
    assert "mods" not in events[0]
    assert "char" not in events[0]
    assert load_chunks(recorder.meta) == []


def test_ctrl_v_is_paste_marker_without_clipboard_body(tmp_path, monkeypatch):
    recorder = _recorder(tmp_path, monkeypatch)
    recorder.start(run_writer=False)
    recorder.enqueue(VK_V, MOD_CTRL, 1)
    recorder.stop()
    event = load_events(recorder.meta)[0]
    assert event["kind"] == "paste"
    assert "char" not in event or event.get("char") in (None, "")


def test_ctrl_enter_flushes_as_submit(tmp_path, monkeypatch):
    recorder = _recorder(tmp_path, monkeypatch)
    recorder.start(run_writer=False)
    recorder.enqueue(0x41, 0, 1)
    recorder.enqueue(VK_RETURN, MOD_CTRL, 1)
    recorder.stop()
    assert load_events(recorder.meta)[-1]["kind"] == "ctrl_enter"
    assert load_chunks(recorder.meta)[0]["flush_reason"] == "ctrl_enter"


def test_note_expand_stores_shortcut_only(tmp_path, monkeypatch):
    recorder = _recorder(tmp_path, monkeypatch)
    recorder.start(run_writer=False)
    recorder.note_expand("/ty")
    recorder.stop()
    event = load_events(recorder.meta)[0]
    assert event["kind"] == "expand"
    assert event["shortcut"] == "/ty"
    assert "Thank you" not in json_blob(event)


def json_blob(event):
    import json

    return json.dumps(event)


def test_queue_overflow_drops_oldest_and_writes_gap(tmp_path, monkeypatch):
    recorder = _recorder(tmp_path, monkeypatch, queue_size=3)
    recorder.start(run_writer=False)
    for vk in (0x41, 0x42, 0x43, 0x44, 0x45):
        recorder.enqueue(vk, 0, 1)
    recorder.stop()
    kinds = [item["kind"] for item in load_events(recorder.meta)]
    assert "gap" in kinds
    gap = next(item for item in load_events(recorder.meta) if item["kind"] == "gap")
    assert gap["dropped_count"] >= 1


def test_writer_error_stops_session(tmp_path, monkeypatch):
    errors = []
    recorder = _recorder(tmp_path, monkeypatch, on_error=errors.append)
    recorder.start()

    def boom(*_args, **_kwargs):
        raise OSError("disk full")

    recorder._append_event = boom
    recorder.enqueue(0x41, 0, 1)
    recorder.wait_idle()
    assert recorder.live is False
    assert errors
    assert load_session(recorder.meta.id).status == "stopped"
