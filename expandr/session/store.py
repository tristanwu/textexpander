from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from uuid import uuid4

from expandr.session.models import SCHEMA_VERSION, SessionMeta
from expandr.session.filters import chunk_has_content
from expandr.store import data_dir

ROTATE_BYTES = 8 * 1024 * 1024


def sessions_dir() -> Path:
    path = data_dir() / "sessions"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _index_path() -> Path:
    return sessions_dir() / "index.json"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(moment: datetime | None = None) -> str:
    value = moment or _now()
    return value.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _tz_name() -> str:
    local = datetime.now().astimezone()
    name = local.tzname()
    offset = local.strftime("%z")
    if name:
        return f"{name} {offset}"
    return offset or "UTC"


def _slug(moment: datetime, suffix: str) -> str:
    return f"{moment.strftime('%Y%m%d-%H%M%S')}-{suffix}"


def _session_dir(meta: SessionMeta) -> Path:
    return sessions_dir() / meta.folder


def _write_json(path: Path, payload: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    try:
        tmp.replace(path)
    except OSError:
        path.write_text(tmp.read_text(encoding="utf-8"), encoding="utf-8")
        tmp.unlink(missing_ok=True)


def save_session(meta: SessionMeta) -> None:
    folder = _session_dir(meta)
    folder.mkdir(parents=True, exist_ok=True)
    _write_json(folder / "session.json", meta.to_dict())
    _rebuild_index()


def _rebuild_index() -> None:
    rows = []
    for folder in sessions_dir().iterdir():
        path = folder / "session.json"
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        rows.append(
            {
                "id": data.get("id"),
                "folder": data.get("folder") or folder.name,
                "title": data.get("title"),
                "started_at": data.get("started_at"),
                "ended_at": data.get("ended_at"),
                "status": data.get("status"),
                "apps": list((data.get("apps") or {}).keys()),
            }
        )
    rows.sort(key=lambda row: row.get("started_at") or "", reverse=True)
    _write_json(_index_path(), {"sessions": rows})


def start_session(title: str | None = None, goal: str | None = None, now: datetime | None = None) -> SessionMeta:
    moment = now or _now()
    ident = uuid4().hex
    local = moment.astimezone()
    clock = local.strftime("%a %I:%M %p").replace(" 0", " ")
    if clock.endswith("AM") or clock.endswith("PM"):
        parts = clock.rsplit(" ", 1)
        if parts[0].startswith("0"):
            clock = parts[0][1:] + " " + parts[1]
    meta = SessionMeta(
        schema_version=SCHEMA_VERSION,
        id=ident,
        folder=_slug(moment, ident[:4]),
        title=title or f"Session · {clock}",
        goal=goal,
        started_at=_iso(moment),
        tz=_tz_name(),
        status="live",
    )
    folder = _session_dir(meta)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "events.jsonl").touch()
    (folder / "chunks.jsonl").touch()
    save_session(meta)
    return meta


def stop_session(meta: SessionMeta, reason: str = "stop", now: datetime | None = None) -> SessionMeta:
    meta.status = "stopped"
    meta.ended_reason = reason
    meta.ended_at = _iso(now)
    meta.last_flush_at = meta.ended_at
    save_session(meta)
    return meta


def load_session(session_id: str) -> SessionMeta:
    for item in _iter_metas():
        if item.id == session_id:
            return item
    raise FileNotFoundError(session_id)


def _iter_metas() -> list[SessionMeta]:
    found: list[SessionMeta] = []
    for folder in sessions_dir().iterdir():
        path = folder / "session.json"
        if not path.exists():
            continue
        try:
            meta = SessionMeta.from_dict(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError, TypeError):
            continue
        if not meta.folder:
            meta.folder = folder.name
        found.append(meta)
    found.sort(key=lambda item: item.started_at, reverse=True)
    return found


def list_sessions() -> list[SessionMeta]:
    return _iter_metas()


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text:
            continue
        try:
            rows.append(json.loads(text))
        except json.JSONDecodeError:
            continue
    return rows


def _event_files(meta: SessionMeta) -> list[Path]:
    folder = _session_dir(meta)
    rotated = sorted(folder.glob("events-*.jsonl"))
    live = folder / "events.jsonl"
    files = rotated
    if live.exists():
        files = rotated + [live]
    return files


def load_events(meta: SessionMeta) -> list[dict]:
    rows: list[dict] = []
    for path in _event_files(meta):
        rows.extend(_read_jsonl(path))
    return rows


def load_chunks(meta: SessionMeta) -> list[dict]:
    return _read_jsonl(_session_dir(meta) / "chunks.jsonl")


def _rotate_if_needed(meta: SessionMeta, rotate_bytes: int) -> None:
    live = _session_dir(meta) / "events.jsonl"
    if not live.exists() or live.stat().st_size < rotate_bytes:
        return
    index = 1
    while True:
        dest = _session_dir(meta) / f"events-{index:04d}.jsonl"
        if not dest.exists():
            live.replace(dest)
            live.touch()
            return
        index += 1


def append_event(meta: SessionMeta, event: dict, rotate_bytes: int = ROTATE_BYTES) -> None:
    folder = _session_dir(meta)
    folder.mkdir(parents=True, exist_ok=True)
    _rotate_if_needed(meta, rotate_bytes)
    path = folder / "events.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")
    meta.event_count += 1
    app = event.get("app")
    if app:
        meta.apps[app] = meta.apps.get(app, 0) + 1
    stamp = event.get("t")
    if stamp:
        meta.last_event_at = stamp
        meta.last_flush_at = stamp


def append_chunk(meta: SessionMeta, chunk: dict) -> None:
    path = _session_dir(meta) / "chunks.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(chunk, ensure_ascii=False) + "\n")


def write_transcript(meta: SessionMeta) -> Path:
    path = _session_dir(meta) / "transcript.md"
    lines = [
        f"# {meta.title}",
        "",
        f"Started: {meta.started_at}",
        f"Ended: {meta.ended_at or 'live'}",
        f"Status: {meta.status}",
        "",
    ]
    if meta.goal:
        lines.extend([f"Goal: {meta.goal}", ""])
    for chunk in load_chunks(meta):
        if not chunk_has_content(chunk):
            continue
        header = f"## {chunk.get('app') or 'unknown'} · {chunk.get('t_start') or ''}"
        lines.append(header)
        lines.append("")
        lines.append(chunk.get("text") or "")
        lines.append("")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def delete_session(session_id: str) -> None:
    import shutil

    meta = load_session(session_id)
    folder = _session_dir(meta)
    if folder.exists():
        shutil.rmtree(folder)
    _rebuild_index()


def repair_orphans() -> list[SessionMeta]:
    repaired: list[SessionMeta] = []
    for meta in _iter_metas():
        if meta.status in {"live", "paused"}:
            stop_session(meta, reason="quit")
            write_transcript(meta)
            repaired.append(meta)
    return repaired
