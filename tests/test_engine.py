from expandr.hook import KeyboardEngine, MatchEvent
from expandr.models import Folder, Library, Snippet, TriggerMode, new_id


def _library() -> Library:
    folder = Folder(id=new_id(), name="Personal", trigger=TriggerMode.WORD_START)
    folder.snippets.append(Snippet(id=new_id(), label="Thanks", shortcut="/ty", content="Thank you"))
    return Library(folders=[folder])


def test_handle_ty_fires_match():
    hits: list[MatchEvent] = []
    library = _library()
    engine = KeyboardEngine(
        library_provider=lambda: library,
        on_match=hits.append,
        on_search=lambda: None,
        on_pause=lambda: None,
        is_paused=lambda: False,
        is_app_disabled=lambda: False,
    )
    engine._handle_key(0xBF, 0)
    engine._handle_key(0x54, 0)
    engine._handle_key(0x59, 0)
    assert hits and hits[0].snippet.shortcut == "/ty"
    assert hits[0].delete_count == 3


def test_busy_does_not_match():
    hits: list[MatchEvent] = []
    library = _library()
    engine = KeyboardEngine(
        library_provider=lambda: library,
        on_match=hits.append,
        on_search=lambda: None,
        on_pause=lambda: None,
        is_paused=lambda: False,
        is_app_disabled=lambda: False,
    )
    engine.busy = True
    engine._handle_key(0xBF, 0)
    engine._handle_key(0x54, 0)
    engine._handle_key(0x59, 0)
    assert hits == []
