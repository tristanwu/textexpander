from expandr.icon import make_icon
from expandr.pause import PAUSED_STATUS, cleared_pause_message, toggle_message, tray_title


def _color(image, xy) -> tuple:
    pixel = image.getpixel(xy)
    return pixel[:3]


def test_paused_tray_icon_is_distinct_from_the_running_icon():
    running = make_icon(64)
    paused = make_icon(64, paused=True)
    assert running.tobytes() != paused.tobytes()
    assert _color(running, (32, 8)) == (37, 99, 235)
    assert _color(paused, (32, 8)) == (180, 83, 9)
    assert _color(paused, (24, 32)) == (255, 255, 255)
    assert _color(running, (32, 32)) == (255, 255, 255)
    assert _color(paused, (32, 32)) == (180, 83, 9)


def test_recording_dot_remains_visible_while_expansion_is_paused():
    paused = make_icon(64, paused=True)
    both = make_icon(64, recording=True, paused=True)
    assert _color(paused, (50, 14)) != (220, 38, 38)
    assert _color(both, (50, 14)) == (220, 38, 38)
    assert _color(both, (32, 8)) == (180, 83, 9)


def test_tray_title_shouts_when_expansion_is_paused():
    assert tray_title("TextExpander", expansion_paused=False, session_live=False, session_paused=False, session_minutes=0) == "TextExpander"
    paused = tray_title(
        "TextExpander",
        expansion_paused=True,
        session_live=True,
        session_paused=False,
        session_minutes=4,
    )
    assert paused == f"TextExpander · session on · 4 min · {PAUSED_STATUS}"


def test_pause_toggle_messages_say_which_way_it_went():
    assert "paused" in toggle_message(True).lower()
    assert "tray" in toggle_message(True).lower()
    assert "resumed" in toggle_message(False).lower()
    assert "cleared" in cleared_pause_message().lower()
