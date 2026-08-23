from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
import threading
import time
from typing import Callable
from uuid import uuid4

from expandr.keys import MOD_CTRL, MOD_SHIFT, VK_BACK, VK_INSERT, VK_RETURN, VK_TAB, VK_V, vk_to_char
from expandr.session.filters import mask_secrets, should_record
from expandr.session.models import SCHEMA_VERSION, SessionMeta
from expandr.session.store import (
    ROTATE_BYTES,
    append_chunk,
    append_event,
    save_session,
    start_session,
    stop_session,
    write_transcript,
)

FLUSH_EVERY = 50
FLUSH_SECONDS = 1.0
HEARTBEAT_SECONDS = 30.0


@dataclass
class _Incoming:
    vk: int
    mods: int
    hwnd: int
    t: str
    kind: str | None = None
    shortcut: str | None = None
    dropped_count: int | None = None


def classify_key(vk: int, mods: int) -> tuple[str, str | None] | None:
    if (mods & MOD_CTRL) and vk == VK_V:
        return "paste", None
    if (mods & MOD_SHIFT) and vk == VK_INSERT:
        return "paste", None
    if (mods & MOD_CTRL) and vk == VK_RETURN:
        return "ctrl_enter", None
    if mods & (MOD_CTRL) and vk not in {VK_V, VK_RETURN}:
        return None
    if vk == VK_BACK:
        return "backspace", None
    if vk == VK_RETURN:
        return "enter", "\n"
    if vk == VK_TAB:
        return "tab", "\t"
    char = vk_to_char(vk, mods)
    if char is None or (len(char) != 1 and char not in {"\n", "\t"}):
        return None
    return "char", char


class SessionRecorder:
    def __init__(
        self,
        skip_provider: Callable[[], list[str]],
        resolve_app: Callable[[int], str],
        *,
        queue_size: int = 8192,
        rotate_bytes: int = ROTATE_BYTES,
        on_error: Callable[[Exception], None] | None = None,
        heartbeat_s: float = HEARTBEAT_SECONDS,
    ) -> None:
        self._skip_provider = skip_provider
        self._resolve_app = resolve_app
        self._queue_size = queue_size
        self._rotate_bytes = rotate_bytes
        self._on_error = on_error
        self._heartbeat_s = heartbeat_s
        self._pending: deque[_Incoming] = deque()
        self._qlock = threading.Lock()
        self._dropped = 0
        self._accepting = False
        self._paused = False
        self._live = False
        self._run_writer = False
        self.meta: SessionMeta | None = None
        self._thread: threading.Thread | None = None
        self._last_hwnd: int | None = None
        self._last_app = ""
        self._chunk_app = ""
        self._chunk_text: list[str] = []
        self._chunk_start = ""
        self._chunk_last = ""
        self._chunk_backspaces = 0
        self._since_flush = 0
        self._last_disk = 0.0
        self._last_heartbeat = 0.0
        self._pause_started: str | None = None
        self._error: Exception | None = None

    @property
    def live(self) -> bool:
        return self._live

    @property
    def paused(self) -> bool:
        return self._paused

    def start(self, title: str | None = None, goal: str | None = None, *, run_writer: bool = True) -> SessionMeta:
        self.meta = start_session(title=title, goal=goal)
        self._live = True
        self._paused = False
        self._accepting = True
        self._error = None
        self._reset_chunk()
        self._run_writer = run_writer
        if run_writer:
            self._thread = threading.Thread(target=self._run, name="expandr-session", daemon=True)
            self._thread.start()
        return self.meta

    def stop(self, reason: str = "stop") -> SessionMeta | None:
        if not self.meta:
            return None
        self._accepting = False
        self._flush_pause_span()
        if self._thread and self._thread.is_alive():
            self._live = False
            self._thread.join(timeout=2.0)
        else:
            self.pump()
            self._live = False
        if self._chunk_text or self._chunk_start:
            self._flush_chunk("stop")
        try:
            write_transcript(self.meta)
        except OSError as exc:
            self._fail(exc)
        stop_session(self.meta, reason=reason)
        self._paused = False
        return self.meta

    def pause(self) -> None:
        if not self._live or self._paused:
            return
        self._paused = True
        self._pause_started = _stamp()
        incoming = _Incoming(0, 0, self._last_hwnd or 0, self._pause_started, kind="pause")
        self._offer(incoming)
        self.pump()

    def resume(self) -> None:
        if not self._live or not self._paused:
            return
        self._flush_pause_span()
        self._paused = False

    def enqueue(self, vk: int, mods: int, hwnd: int) -> None:
        if not self._accepting:
            return
        classified = classify_key(vk, mods)
        if classified is None:
            return
        kind, _char = classified
        self._offer(_Incoming(vk, mods, hwnd, _stamp(), kind=kind))

    def note_expand(self, shortcut: str) -> None:
        if not self._accepting:
            return
        self._offer(_Incoming(0, 0, self._last_hwnd or 0, _stamp(), kind="expand", shortcut=shortcut))

    def wait_idle(self, timeout: float = 2.0) -> None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            with self._qlock:
                empty = not self._pending and self._dropped == 0
            if empty and (not self._thread or True):
                time.sleep(0.05)
                with self._qlock:
                    if not self._pending and self._dropped == 0:
                        return
            time.sleep(0.02)

    def pump(self) -> None:
        while True:
            batch, dropped = self._take()
            if dropped:
                self._write_gap(dropped)
            if not batch:
                return
            for item in batch:
                try:
                    self._handle(item)
                except Exception as exc:
                    self._fail(exc)
                    return
            self._maybe_flush_disk(force=True)

    def _offer(self, item: _Incoming) -> None:
        with self._qlock:
            if len(self._pending) >= self._queue_size:
                self._pending.popleft()
                self._dropped += 1
            self._pending.append(item)

    def _take(self) -> tuple[list[_Incoming], int]:
        with self._qlock:
            dropped = self._dropped
            self._dropped = 0
            batch = list(self._pending)
            self._pending.clear()
        return batch, dropped

    def _run(self) -> None:
        while self._live or self._pending or self._dropped:
            if not self._accepting and not self._pending and not self._dropped:
                break
            batch, dropped = self._take()
            if dropped:
                try:
                    self._write_gap(dropped)
                except Exception as exc:
                    self._fail(exc)
                    return
            if not batch:
                self._maybe_heartbeat()
                time.sleep(0.05)
                continue
            for item in batch:
                try:
                    self._handle(item)
                except Exception as exc:
                    self._fail(exc)
                    return
            self._maybe_flush_disk()

    def _handle(self, item: _Incoming) -> None:
        if item.kind == "gap":
            self._write_event(item, app=self._last_app or "unknown.exe")
            return
        if item.kind == "pause":
            self._flush_chunk("pause")
            self._write_event(item, app=self._last_app or "unknown.exe")
            return
        if item.kind == "expand":
            self._write_event(item, app=self._last_app or "unknown.exe")
            if self._chunk_text is not None:
                self._chunk_text.append(f"[expanded {item.shortcut}]")
            return
        app = self._app_for(item.hwnd)
        skip = self._skip_provider()
        if not should_record(app, skip, live=True, paused=self._paused and item.kind != "pause"):
            if self._paused:
                return
            skip_item = _Incoming(item.vk, item.mods, item.hwnd, item.t, kind="skip")
            self._write_event(skip_item, app=app)
            return
        classified = classify_key(item.vk, item.mods) if item.kind not in {"paste", "ctrl_enter"} else (item.kind, None)
        if item.kind in {"paste", "ctrl_enter", "enter", "tab", "backspace", "char"}:
            kind, char = item.kind, None
            if kind == "char" or kind == "tab" or kind == "enter":
                kind, char = classify_key(item.vk, item.mods) or (kind, None)
        else:
            kind, char = classified or (item.kind, None)
        if kind is None:
            return
        if self._chunk_app and app != self._chunk_app and (self._chunk_text or self._chunk_start):
            self._flush_chunk("app_switch")
        if not self._chunk_start:
            self._chunk_start = item.t
            self._chunk_app = app
        self._chunk_last = item.t
        self._write_event(_Incoming(item.vk, item.mods, item.hwnd, item.t, kind=kind, shortcut=item.shortcut), app=app)
        if kind == "backspace":
            if self._chunk_text:
                self._chunk_text.pop()
            self._chunk_backspaces += 1
        elif kind == "paste":
            self._chunk_text.append("[paste]")
        elif kind == "char" and char:
            self._chunk_text.append(char)
        elif kind == "tab":
            self._chunk_text.append("\t")
        elif kind in {"enter", "ctrl_enter"}:
            self._flush_chunk(kind)
        self._since_flush += 1

    def _app_for(self, hwnd: int) -> str:
        if hwnd == self._last_hwnd and self._last_app:
            return self._last_app
        try:
            app = self._resolve_app(hwnd) or "unknown.exe"
        except Exception:
            app = "unknown.exe"
        self._last_hwnd = hwnd
        self._last_app = app.casefold() if app else "unknown.exe"
        return self._last_app

    def _write_gap(self, dropped: int) -> None:
        if not self.meta:
            return
        item = _Incoming(0, 0, self._last_hwnd or 0, _stamp(), kind="gap", dropped_count=dropped)
        self._write_event(item, app=self._last_app or "unknown.exe")

    def _write_event(self, item: _Incoming, app: str) -> None:
        if not self.meta:
            return
        event = {
            "schema_version": SCHEMA_VERSION,
            "session_id": self.meta.id,
            "t": item.t,
            "app": app,
            "kind": item.kind,
        }
        if item.kind != "skip":
            event["vk"] = item.vk
            event["mods"] = item.mods
        if item.kind == "char":
            classified = classify_key(item.vk, item.mods)
            event["char"] = classified[1] if classified else None
        if item.shortcut:
            event["shortcut"] = item.shortcut
        if item.dropped_count:
            event["dropped_count"] = item.dropped_count
        self._append_event(self.meta, event, rotate_bytes=self._rotate_bytes)

    def _append_event(self, meta: SessionMeta, event: dict, rotate_bytes: int = ROTATE_BYTES) -> None:
        append_event(meta, event, rotate_bytes=rotate_bytes)

    def _flush_chunk(self, reason: str) -> None:
        if not self.meta:
            self._reset_chunk()
            return
        if not self._chunk_start and not self._chunk_text:
            self._reset_chunk()
            return
        text = mask_secrets("".join(self._chunk_text))
        append_chunk(
            self.meta,
            {
                "chunk_id": uuid4().hex,
                "app": self._chunk_app or self._last_app or "unknown.exe",
                "t_start": self._chunk_start or _stamp(),
                "t_end": self._chunk_last or _stamp(),
                "text": text,
                "flush_reason": reason,
                "backspace_count": self._chunk_backspaces,
            },
        )
        self._reset_chunk()

    def _reset_chunk(self) -> None:
        self._chunk_app = ""
        self._chunk_text = []
        self._chunk_start = ""
        self._chunk_last = ""
        self._chunk_backspaces = 0

    def _maybe_flush_disk(self, force: bool = False) -> None:
        if not self.meta:
            return
        now = time.time()
        if force or self._since_flush >= FLUSH_EVERY or now - self._last_disk >= FLUSH_SECONDS:
            save_session(self.meta)
            self._since_flush = 0
            self._last_disk = now
            self._last_heartbeat = now

    def _maybe_heartbeat(self) -> None:
        if not self.meta:
            return
        now = time.time()
        if now - self._last_heartbeat >= self._heartbeat_s:
            save_session(self.meta)
            self._last_heartbeat = now

    def _flush_pause_span(self) -> None:
        if self.meta and self._pause_started:
            self.meta.pause_spans.append({"started_at": self._pause_started, "ended_at": _stamp()})
            self._pause_started = None

    def _fail(self, exc: Exception) -> None:
        self._error = exc
        self._accepting = False
        self._live = False
        if self.meta and self.meta.status == "live":
            try:
                stop_session(self.meta, reason="error")
            except OSError:
                pass
        if self._on_error:
            self._on_error(exc)


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
