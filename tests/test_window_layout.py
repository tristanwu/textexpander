import customtkinter as ctk

from expandr.models import Folder, Library, Snippet
from expandr.ui.main_window import MainWindow
from expandr.ui.settings import SettingsWindow


def _library() -> Library:
    personal = Folder(
        id="p",
        name="Personal",
        snippets=[Snippet(id="1", label="Untitled", shortcut="/harvest", content="hello")],
    )
    agentic = Folder(
        id="a",
        name="Agentic",
        snippets=[Snippet(id="2", label="Repo review", shortcut="/agentic_reporeview", content="review")],
    )
    return Library(folders=[personal, agentic])


def _with_text(root, text):
    found = []

    def walk(widget) -> None:
        try:
            if widget.cget("text") == text:
                found.append(widget)
        except Exception:
            pass
        for child in widget.winfo_children():
            walk(child)

    walk(root)
    return found


def test_create_backup_is_on_the_first_settings_screen():
    root = ctk.CTk()
    root.withdraw()
    try:
        window = SettingsWindow(root, _library(), on_change=lambda: None)
        window.update_idletasks()
        backup = _with_text(window, "Create backup")[0]
        expansion = _with_text(window, "Expansion")[0]
        assert backup.winfo_rooty() < expansion.winfo_rooty()
        assert backup.winfo_rooty() + backup.winfo_height() <= window.winfo_rooty() + window.winfo_height()
    finally:
        root.destroy()


def test_snippet_list_groups_folders_and_skips_untitled():
    root = ctk.CTk()
    root.withdraw()
    try:
        window = MainWindow(root, _library(), on_change=lambda: None, on_settings=lambda: None)
        window.update_idletasks()
        labels = [widget.cget("text") for widget in _with_text(window, "Personal")]
        assert labels
        assert _with_text(window, "/harvest")
        assert not _with_text(window, "/harvest    Untitled")
        assert _with_text(window, "Settings")
        assert window.grid_size()[1] >= 3
    finally:
        root.destroy()
