from expandr.app import ExpandrApp
from expandr.hook import KeyboardEngine, MatchEvent
from expandr.models import Folder, Library, Snippet, TriggerMode, new_id


def _library(content: str = "Thank you") -> Library:
    folder = Folder(id=new_id(), name="Personal", trigger=TriggerMode.WORD_START)
    folder.snippets.append(Snippet(id=new_id(), label="Thanks", shortcut="/ty", content=content))
    return Library(folders=[folder])


def _app(library: Library, *, disabled: bool = False):
    app = ExpandrApp.__new__(ExpandrApp)
    app.library = library
    app.root = None
    app.engine = KeyboardEngine(
        library_provider=lambda: library,
        on_match=lambda _event: None,
        on_search=lambda: None,
        on_pause=lambda: None,
        is_paused=lambda: False,
        is_app_disabled=lambda: disabled,
    )
    app.recorder = type("Recorder", (), {"live": False, "note_expand": lambda self, _shortcut: None})()
    app._app_disabled = lambda: disabled
    return app


def _event(library: Library) -> MatchEvent:
    snippet = library.folders[0].snippets[0]
    return MatchEvent(snippet=snippet, delete_count=len(snippet.shortcut), hwnd=1)


def test_expand_skips_disabled_app(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    calls = []
    monkeypatch.setattr("expandr.app.insert_expansion", lambda *_args, **_kwargs: calls.append("insert") or "pasted")
    monkeypatch.setattr("expandr.app.get_clipboard_text", lambda: "")
    app = _app(_library(), disabled=True)
    app._expand(_event(app.library))
    assert calls == []
    assert app.engine.last_insert == ""
    assert app.engine.busy is False


def test_expand_form_cancel_does_not_insert(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    calls = []
    monkeypatch.setattr("expandr.app.insert_expansion", lambda *_args, **_kwargs: calls.append("insert") or "pasted")
    monkeypatch.setattr("expandr.app.ask_fields", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("expandr.app.get_clipboard_text", lambda: "")
    content = "{formtext: name=who; default=Ada}Hi {= who}"
    app = _app(_library(content))
    app._expand(_event(app.library))
    assert calls == []
    assert app.engine.last_insert == ""
    assert app.engine.busy is False


def test_expand_insert_failure_sets_last_insert_and_error_log(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))

    def boom(*_args, **_kwargs):
        raise RuntimeError("send failed")

    monkeypatch.setattr("expandr.app.insert_expansion", boom)
    monkeypatch.setattr("expandr.app.get_clipboard_text", lambda: "")
    app = _app(_library())
    app._expand(_event(app.library))
    assert app.engine.last_insert == "failed"
    assert app.engine.busy is False
    log = tmp_path / "TextExpander" / "error.log"
    assert log.exists()
    assert "RuntimeError" in log.read_text(encoding="utf-8")
    assert "send failed" in log.read_text(encoding="utf-8")
