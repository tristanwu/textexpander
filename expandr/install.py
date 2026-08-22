from __future__ import annotations

from pathlib import Path

from expandr.icon import write_ico
from expandr.identity import APP_NAME, LEGACY_APP_NAME
from expandr.shortcut import ShortcutSpec, create_shortcut
from expandr.startup import launch_target, project_dir
from expandr.store import data_dir


def start_menu_dir() -> Path:
    return Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs"


def start_menu_shortcut() -> Path:
    return start_menu_dir() / f"{APP_NAME}.lnk"


def is_on_start_menu() -> bool:
    return start_menu_shortcut().exists()


def project_root() -> Path:
    return project_dir()


def shortcut_spec() -> ShortcutSpec:
    target, arguments, working = launch_target()
    return ShortcutSpec(
        path=start_menu_shortcut(),
        target=target,
        arguments=arguments,
        working_directory=working,
        icon=str(write_ico(data_dir() / "textexpander.ico")),
        description=f"{APP_NAME} text expander",
    )


def install_start_menu() -> Path:
    _remove_legacy_shortcut()
    return create_shortcut(shortcut_spec())


def uninstall_start_menu() -> None:
    path = start_menu_shortcut()
    if path.exists():
        path.unlink()
    _remove_legacy_shortcut()


def _remove_legacy_shortcut() -> None:
    legacy = start_menu_dir() / f"{LEGACY_APP_NAME}.lnk"
    if legacy.exists():
        legacy.unlink()


def main() -> None:
    path = install_start_menu()
    print(f"Start menu shortcut: {path}")


if __name__ == "__main__":
    main()
