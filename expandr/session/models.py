from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

SCHEMA_VERSION = 1


@dataclass
class SessionMeta:
    schema_version: int
    id: str
    folder: str
    title: str
    started_at: str
    tz: str
    status: str
    goal: str | None = None
    ended_at: str | None = None
    ended_reason: str | None = None
    apps: dict[str, int] = field(default_factory=dict)
    event_count: int = 0
    last_event_at: str | None = None
    last_flush_at: str | None = None
    pause_spans: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "id": self.id,
            "folder": self.folder,
            "title": self.title,
            "goal": self.goal,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "tz": self.tz,
            "status": self.status,
            "ended_reason": self.ended_reason,
            "apps": dict(self.apps),
            "event_count": self.event_count,
            "last_event_at": self.last_event_at,
            "last_flush_at": self.last_flush_at,
            "pause_spans": list(self.pause_spans),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SessionMeta:
        return cls(
            schema_version=int(data.get("schema_version") or SCHEMA_VERSION),
            id=str(data.get("id") or ""),
            folder=str(data.get("folder") or ""),
            title=str(data.get("title") or "Session"),
            goal=data.get("goal"),
            started_at=str(data.get("started_at") or ""),
            ended_at=data.get("ended_at"),
            tz=str(data.get("tz") or "UTC"),
            status=str(data.get("status") or "stopped"),
            ended_reason=data.get("ended_reason"),
            apps=dict(data.get("apps") or {}),
            event_count=int(data.get("event_count") or 0),
            last_event_at=data.get("last_event_at"),
            last_flush_at=data.get("last_flush_at"),
            pause_spans=list(data.get("pause_spans") or []),
        )
