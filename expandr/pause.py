from __future__ import annotations

PAUSED_STATUS = "EXPANSION PAUSED"


def toggle_message(paused: bool) -> str:
    if paused:
        return "Expansion paused. Snippets will not expand until you resume from the tray."
    return "Expansion resumed."


def cleared_pause_message() -> str:
    return "Expansion is on. A saved pause was cleared — pause now lasts only until you quit."


def tray_title(
    app_name: str,
    *,
    expansion_paused: bool,
    session_live: bool,
    session_paused: bool,
    session_minutes: int,
) -> str:
    parts = [app_name]
    if session_live:
        state = "session paused" if session_paused else "session on"
        parts.append(f"{state} · {session_minutes} min")
    if expansion_paused:
        parts.append(PAUSED_STATUS)
    return " · ".join(parts) if len(parts) > 1 else app_name
