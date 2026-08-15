from expandr.matcher import find_matches, has_longer_prefix
from expandr.models import Folder, Library, Snippet, TriggerMode, new_id


def _lib(*pairs: tuple[str, TriggerMode]) -> Library:
    folders = []
    for shortcut, mode in pairs:
        folder = Folder(id=new_id(), name=shortcut, trigger=mode)
        folder.snippets.append(Snippet(id=new_id(), label=shortcut, shortcut=shortcut, content="X"))
        folders.append(folder)
    return Library(folders=folders)


def test_word_start_match():
    library = _lib(("/ty", TriggerMode.WORD_START))
    matches = find_matches("say /ty", library)
    assert matches and matches[0][0].shortcut == "/ty"
    assert find_matches("say/ty", library) == []


def test_anywhere_match():
    library = _lib(("\\e", TriggerMode.ANYWHERE))
    assert find_matches("caf\\e", library)


def test_word_bounded_needs_break():
    library = _lib(("/w", TriggerMode.WORD_BOUNDED))
    assert find_matches(" /w", library) == []
    matches = find_matches(" /w ", library)
    assert matches and matches[0][1] == 3
    assert matches[0][2] == " "


def test_longer_prefix_waits():
    library = _lib(("/do", TriggerMode.WORD_START), ("/dothis", TriggerMode.WORD_START))
    assert has_longer_prefix("/do", library)


def test_single_slash_is_not_armed():
    library = _lib(("/", TriggerMode.WORD_START))
    assert find_matches(" /", library) == []
    assert find_matches("/", library) == []
