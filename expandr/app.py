from __future__ import annotations

import os
import queue
import sys
import threading
from pathlib import Path

import customtkinter as ctk

from expandr.hook import KeyboardEngine, MatchEvent
from expandr.icon import make_icon
from expandr.insert import insert_expansion
from expandr.pause import cleared_pause_message, toggle_message, tray_title
from expandr.parser import collect_fields, evaluate, parse
from expandr.processutil import become_only_instance, text_blaze_running
from expandr.session.engine import SessionRecorder
from expandr.session.store import repair_orphans
from expandr.startup import ensure_startup_registration
from expandr.store import data_dir, load_library, save_library
from expandr.ui.coach import CoachDialog
from expandr.ui.fill_in import ask_fields
from expandr.ui.main_window import MainWindow
from expandr.ui.search import ask_snippet
from expandr.ui.session_consent import ask_session_consent
from expandr.ui.sessions import SessionsWindow
from expandr.ui.present import present
from expandr.ui.settings import SettingsWindow
from expandr.identity import APP_NAME
from expandr.win32api import foreground_hwnd, foreground_process_name, get_clipboard_text, process_name


class ExpandrApp:
    def __init__(self) -> None:
        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")
        self.root = ctk.CTk()
        self.root.withdraw()
        self.root.title(APP_NAME)
        loaded = load_library()
        self.library = loaded.library
        self._cleared_pause = loaded.cleared_pause
        if loaded.quarantined is not None:
            self.root.after(100, lambda path=loaded.quarantined: self._warn_recovered_library(path))
        startup_enabled = ensure_startup_registration(self.library.settings.start_with_windows)
        if startup_enabled != self.library.settings.start_with_windows:
            self.library.settings.start_with_windows = startup_enabled
            save_library(self.library)
        self.events: queue.Queue = queue.Queue()
        self.window: MainWindow | None = None
        self.settings: SettingsWindow | None = None
        self.sessions_window: SessionsWindow | None = None
        self.tray = None
        self._dead = False
        repair_orphans()
        self.recorder = SessionRecorder(
            skip_provider=lambda: self.library.settings.session_skip_apps,
            resolve_app=lambda hwnd: process_name(hwnd) or foreground_process_name() or "unknown.exe",
            on_error=lambda exc: self.events.put(("session_error", exc)),
        )
        self.engine = KeyboardEngine(
            library_provider=lambda: self.library,
            on_match=lambda event: self.events.put(("match", event)),
            on_search=lambda: self.events.put(("search", None)),
            on_pause=lambda: self.events.put(("toggle", None)),
            is_paused=lambda: self.library.settings.paused,
            is_app_disabled=self._app_disabled,
            on_key=self.recorder.enqueue,
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

    def _warn_recovered_library(self, quarantined: Path) -> None:
        from tkinter import messagebox

        messagebox.showwarning(
            APP_NAME,
            "The snippet library could not be read, so it was moved aside and a new library was created.\n\n"
            f"Your previous file is here:\n{quarantined}",
            parent=self._dialog_parent(),
        )


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
                elif kind == "session_start":
                    self._start_session()
                elif kind == "session_stop":
                    self._stop_session()
                elif kind == "session_pause":
                    self._toggle_session_pause()
                elif kind == "session_open":
                    self.show_sessions()
                elif kind == "session_error":
                    self._session_failed(payload)
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
            if self.recorder.live:
                self.recorder.note_expand(snippet.shortcut)
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
                on_sessions=self.show_sessions,
                status_provider=self.engine.status,
                conflict_provider=text_blaze_running,
                session_status_provider=self._session_banner,
            )
        self.window.show()

    def _dialog_parent(self):
        for window in (self.settings, self.sessions_window, self.window):
            if window is not None and window.winfo_exists() and window.winfo_viewable():
                return window
        return self.root

    def show_settings(self) -> None:
        if self.settings is None or not self.settings.winfo_exists():
            self.settings = SettingsWindow(self.root, self.library, on_change=self._library_changed)
        present(self.settings)

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
        self._notify(toggle_message(self.library.settings.paused))

    def _start_tray(self) -> None:
        import pystray

        self.tray = pystray.Icon(APP_NAME, self._tray_image(), self._tray_title(), self._tray_menu())
        threading.Thread(target=self.tray.run, args=(self._tray_ready,), name="expandr-tray", daemon=True).start()

    def _tray_ready(self, icon) -> None:
        icon.visible = True
        if self._cleared_pause:
            self._notify(cleared_pause_message(), icon)

    def _notify(self, message: str, icon=None) -> None:
        tray = icon or self.tray
        if tray is None:
            return
        try:
            tray.notify(message, APP_NAME)
        except Exception:
            pass

    def _tray_image(self):
        return make_icon(
            64,
            recording=self.recorder.live and not self.recorder.paused,
            paused=self.library.settings.paused,
        )

    def _tray_menu(self):
        import pystray

        paused = self.library.settings.paused
        live = self.recorder.live
        session_paused = self.recorder.paused
        items = [
            pystray.MenuItem("Open library", lambda: self.events.put(("open", None)), default=True),
            pystray.Menu.SEPARATOR,
        ]
        if not live:
            items.append(pystray.MenuItem("Start session", lambda: self.events.put(("session_start", None))))
        else:
            items.append(pystray.MenuItem("Stop session", lambda: self.events.put(("session_stop", None))))
            items.append(
                pystray.MenuItem(
                    "Resume session" if session_paused else "Pause session",
                    lambda: self.events.put(("session_pause", None)),
                )
            )
        items.extend(
            [
                pystray.MenuItem("Open sessions", lambda: self.events.put(("session_open", None))),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(
                    "Resume expansion" if paused else "Pause expansion",
                    lambda: self.events.put(("toggle", None)),
                ),
                pystray.MenuItem("Quit", lambda: self.events.put(("quit", None))),
            ]
        )
        return pystray.Menu(*items)

    def _tray_title(self) -> str:
        minutes = 0
        if self.recorder.live and self.recorder.meta and self.recorder.meta.started_at:
            try:
                from datetime import datetime, timezone

                started = datetime.fromisoformat(self.recorder.meta.started_at.replace("Z", "+00:00"))
                minutes = int((datetime.now(timezone.utc) - started).total_seconds() // 60)
            except ValueError:
                minutes = 0
        return tray_title(
            APP_NAME,
            expansion_paused=self.library.settings.paused,
            session_live=self.recorder.live,
            session_paused=self.recorder.paused,
            session_minutes=minutes,
        )

    def _session_banner(self) -> str:
        if not self.recorder.live:
            return ""
        if self.recorder.paused:
            return "Session paused · nothing new is being written"
        return "SESSION ON · saving what you type"

    def _refresh_tray(self) -> None:
        if self.tray:
            self.tray.menu = self._tray_menu()
            self.tray.title = self._tray_title()
            try:
                self.tray.icon = self._tray_image()
            except Exception:
                pass

    def show_sessions(self) -> None:
        if self.sessions_window is None or not self.sessions_window.winfo_exists():
            self.sessions_window = SessionsWindow(
                self.root,
                self.library,
                self.recorder,
                on_start=self._start_session,
                on_stop=self._stop_session,
                on_change=self._library_changed,
            )
        self.sessions_window.show()

    def _start_session(self) -> None:
        if self.recorder.live:
            return
        if not self.library.settings.seen_session_consent:
            if not ask_session_consent(self.root):
                return
            self.library.settings.seen_session_consent = True
            save_library(self.library)
        self.recorder.start()
        self._refresh_tray()
        if self.sessions_window is not None and self.sessions_window.winfo_exists():
            self.sessions_window.refresh()

    def _stop_session(self) -> None:
        if not self.recorder.live:
            return
        self.recorder.stop()
        self._refresh_tray()
        if self.sessions_window is not None and self.sessions_window.winfo_exists():
            self.sessions_window.refresh()

    def _toggle_session_pause(self) -> None:
        if not self.recorder.live:
            return
        if self.recorder.paused:
            self.recorder.resume()
        else:
            self.recorder.pause()
        self._refresh_tray()

    def _session_failed(self, exc) -> None:
        from tkinter import messagebox

        self._refresh_tray()
        messagebox.showerror("Sessions", f"Could not save the session.\n\n{exc}", parent=self._dialog_parent())

    def shutdown(self) -> None:
        if self._dead:
            return
        self._dead = True
        try:
            if self.recorder.live or self.recorder.meta:
                self.recorder.stop(reason="quit")
        except Exception:
            pass
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
