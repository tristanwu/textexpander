from expandr.models import Folder, Library, Snippet
from expandr.ui.listing import folders_for_list, snippet_row_text


def test_untitled_label_stays_off_the_snippet_row():
    untitled = Snippet(id="1", label="Untitled", shortcut="/harvest", content="")
    named = Snippet(id="2", label="Build note", shortcut="/grline", content="")
    blank = Snippet(id="3", label="", shortcut="", content="")

    assert snippet_row_text(untitled) == "/harvest"
    assert snippet_row_text(named) == "/grline    Build note"
    assert snippet_row_text(blank) == "(no shortcut)"


def test_list_groups_by_folder_and_hides_empty_groups():
    personal = Folder(
        id="p",
        name="Personal",
        snippets=[Snippet(id="1", label="Untitled", shortcut="/harvest", content="a")],
    )
    agentic = Folder(
        id="a",
        name="Agentic",
        snippets=[Snippet(id="2", label="Repo review", shortcut="/agentic_reporeview", content="b")],
    )
    library = Library(folders=[personal, agentic])

    groups = folders_for_list(library, "")
    assert [folder.name for folder, _rows in groups] == ["Personal", "Agentic"]

    matched = folders_for_list(library, "repo")
    assert [folder.name for folder, _rows in matched] == ["Agentic"]
    assert matched[0][1][0].shortcut == "/agentic_reporeview"
