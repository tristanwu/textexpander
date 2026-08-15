from __future__ import annotations

import os
import queue
import sys
import threading
from pathlib import Path

import customtkinter as ctk
import pystray

from expandr.hook import KeyboardEngine, MatchEvent
from expandr.icon import make_icon
from expandr.insert import insert_expansion
from expandr.parser import collect_fields, evaluate, parse
from expandr.processutil import become_only_instance, text_blaze_running
from expandr.startup import set_start_with_windows
from expandr.store import data_dir, load_library, save_library
from expandr.ui.coach import CoachDialog
from expandr.ui.fill_in import ask_fields
from expandr.ui.main_window import MainWindow
from expandr.ui.search import ask_snippet
from expandr.ui.settings import SettingsWindow
from expandr.identity import APP_NAME
from expandr.win32api import foreground_hwnd, foreground_process_name, get_clipboard_text


class ExpandrApp:
    def __init__(self) -> None:
        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")
        self.root = ctk.CTk()
        self.root.withdraw()
        self.root.title(APP_NAME)
        self.library = load_library()
        if self.library.settings.start_with_windows:
            set_start_with_windows(True)
        self.events: queue.Queue = queue.Queue()
        self.window: MainWindow | None = None
        self.settings: SettingsWindow | None = None
        self.tray = None
        self._dead = False
        self.engine = KeyboardEngine(
            library_provider=lambda: self.library,
            on_match=lambda event: self.events.put(("match", event)),
            on_search=lambda: self.events.put(("search", None)),
            on_pause=lambda: self.events.put(("toggle", None)),
            is_paused=lambda: self.library.settings.paused,
            is_app_disabled=self._app_disabled,
        )
        self.root.protocol("WM_DELETE_WINDOW", self._hide_root)
        self.root.after(40, self._poll)
        self.engine.start()
        self._start_tray()
        if not self.library.settings.seen_coach:
            self.root.after(200, self._show_coach)

    def _hide_root(self) -> None:
        self.root.withdraw()

    def _app_disabled(self) -> bool:
        name = foreground_process_name()
        blocked = {item.casefold() for item in self.library.settings.disabled_apps}
        return name in blocked

    def _poll(self) -> None:
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if self._dead:
                    return
                if kind == "match":
                    self._expand(payload)
                elif kind == "search":
                    self._search()
                elif kind == "quit":
                    self.shutdown()
                    return
                elif kind == "open":
                    self.show_library()
                elif kind == "toggle":
                    self._toggle_pause()
        except queue.Empty:
            pass
        self.root.after(40, self._poll)

    def _expand(self, event: MatchEvent, snippet=None, hwnd: int | None = None, delete_count: int = 0, suffix: str = "") -> None:
        if snippet is None:
            snippet = event.snippet
            hwnd = event.hwnd
            delete_count = event.delete_count
            suffix = event.suffix
        if self._app_disabled():
            return
        self.engine.busy = True
        self.engine.clear()
        try:
            fields = collect_fields(parse(snippet.content))
            answers = {}
            clipboard = get_clipboard_text() or ""
            if fields:
                answers = ask_fields(self.root, snippet.label, fields, snippet.content, self.library, clipboard)
                if answers is None:
                    return
            result = evaluate(snippet.content, answers, library=self.library, clipboard=clipboard)
            how = insert_expansion(hwnd or foreground_hwnd(), delete_count, result.text + suffix, result.cursor)
            self.engine.last_insert = how
        except Exception as exc:
            self.engine.last_insert = "failed"
            try:
                (data_dir() / "error.log").write_text(f"{type(exc).__name__}: {exc}\n", encoding="utf-8")
            except OSError:
                pass
        finally:
            self.engine.busy = False
            self.engine.clear()

    def _search(self) -> None:
        self.engine.busy = True
        hwnd = foreground_hwnd()
        try:
            snippet = ask_snippet(self.root, self.library)
            if snippet:
                self._expand(None, snippet=snippet, hwnd=hwnd, delete_count=0, suffix="")
        finally:
            self.engine.busy = False

    def show_library(self) -> None:
        if self.window is None or not self.window.winfo_exists():
            self.window = MainWindow(
                self.root,
                self.library,
                on_change=self._library_changed,
                on_settings=self.show_settings,
                on_quit=lambda: self.events.put(("quit", None)),
                status_provider=self.engine.status,
                conflict_provider=text_blaze_running,
            )
        self.window.show()

    def show_settings(self) -> None:
        if self.settings is None or not self.settings.winfo_exists():
            self.settings = SettingsWindow(self.root, self.library, on_change=self._library_changed)
        self.settings.lift()
        self.settings.focus_force()

    def _show_coach(self) -> None:
        def done() -> None:
            self.library.settings.seen_coach = True
            save_library(self.library)

        CoachDialog(self.root, on_done=done)

    def _library_changed(self) -> None:
        save_library(self.library)
        self._refresh_tray()
        if self.window is not None and self.window.winfo_exists():
            self.window.folder_box.configure(values=self.window._folder_names())
            self.window._refresh_list()
            self.window._update_status()

    def _toggle_pause(self) -> None:
        self.library.settings.paused = not self.library.settings.paused
        save_library(self.library)
        self._refresh_tray()

    def _start_tray(self) -> None:
        icon = make_icon(64)
        self.tray = pystray.Icon(APP_NAME, icon, APP_NAME, self._tray_menu())
        threading.Thread(target=self.tray.run, name="expandr-tray", daemon=True).start()

    def _tray_menu(self):
        paused = self.library.settings.paused
        return pystray.Menu(
            pystray.MenuItem("Open library", lambda: self.events.put(("open", None)), default=True),
            pystray.MenuItem(
                "Resume expansion" if paused else "Pause expansion",
                lambda: self.events.put(("toggle", None)),
            ),
            pystray.MenuItem("Quit", lambda: self.events.put(("quit", None))),
        )

    def _refresh_tray(self) -> None:
        if self.tray:
            self.tray.menu = self._tray_menu()
            self.tray.title = f"{APP_NAME} (paused)" if self.library.settings.paused else APP_NAME

    def shutdown(self) -> None:
        if self._dead:
            return
        self._dead = True
        try:
            self.engine.stop()
        except Exception:
            pass
        try:
            if self.tray:
                self.tray.visible = False
                self.tray.stop()
        except Exception:
            pass
        try:
            self.root.quit()
        except Exception:
            pass
        os._exit(0)

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    if getattr(sys, "frozen", False):
        sys.path.insert(0, str(Path(sys.executable).parent))
    if not become_only_instance():
        return
    ExpandrApp().run()
