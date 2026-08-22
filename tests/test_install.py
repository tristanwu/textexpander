from pathlib import Path

from expandr.install import shortcut_spec, start_menu_shortcut


def test_start_menu_shortcut_is_under_programs():
    path = start_menu_shortcut()
    assert path.name == "TextExpander.lnk"
    assert path.parent.name == "Programs"


def test_shortcut_spec_points_at_a_real_launcher():
    spec = shortcut_spec()
    assert Path(spec.target).exists()
    assert spec.path == start_menu_shortcut()
    assert spec.working_directory
