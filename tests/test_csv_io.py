from expandr.csv_io import export_csv, import_csv
from expandr.models import Folder, Library, Snippet, TriggerMode


def test_csv_roundtrip_adds_snippets(tmp_path):
    source = Library(
        folders=[
            Folder(
                id="f",
                name="Work",
                trigger=TriggerMode.WORD_START,
                snippets=[Snippet(id="s", label="Thanks", shortcut="/ty", content="Thank you")],
            )
        ]
    )
    path = tmp_path / "snippets.csv"
    export_csv(source, path)
    dest = Library()
    added = import_csv(dest, path)
    assert added == 1
    assert dest.folders[0].name == "Work"
    assert dest.folders[0].snippets[0].shortcut == "/ty"
    assert dest.folders[0].snippets[0].content == "Thank you"
