"""Stream events.jsonl into ingest in batches for live dashboard demo."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from app import config
from app.db import delete_events_for_store_date, session_scope
from app.ingestion import ingest_raw_events
from app.stores import canonical_store_id

DEFAULT_EVENTS_PATH = config.ROOT / "data" / "events.jsonl"


@dataclass
class ReplayStatus:
    running: bool = False
    total: int = 0
    sent: int = 0
    batch_size: int = 12
    interval_ms: int = 700
    store_id: str = "ST1008"
    target_date: str = "2026-04-10"
    last_event_type: str | None = None
    last_visitor_id: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        pct = round(100 * self.sent / self.total, 1) if self.total else 0.0
        return {
            "running": self.running,
            "total": self.total,
            "sent": self.sent,
            "progress_pct": pct,
            "batch_size": self.batch_size,
            "interval_ms": self.interval_ms,
            "store_id": self.store_id,
            "target_date": self.target_date,
            "last_event_type": self.last_event_type,
            "last_visitor_id": self.last_visitor_id,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "error": self.error,
        }


class EventReplay:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._task: asyncio.Task | None = None
        self.status = ReplayStatus()
        self._events: list[dict[str, Any]] = []

    def _load_events(self, path: Path) -> list[dict[str, Any]]:
        rows = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                rows.append(json.loads(line))
        rows.sort(key=lambda e: e.get("timestamp", ""))
        return rows

    async def start(
        self,
        *,
        store_id: str = "ST1008",
        target_date: str = "2026-04-10",
        reset: bool = True,
        batch_size: int = 12,
        interval_ms: int = 700,
        events_path: Path | None = None,
    ) -> ReplayStatus:
        async with self._lock:
            if self.status.running:
                return self.status

            path = events_path or DEFAULT_EVENTS_PATH
            if not path.is_file():
                self.status.error = f"events file not found: {path}"
                return self.status

            self._events = self._load_events(path)
            canonical = canonical_store_id(store_id)
            parsed_date = date.fromisoformat(target_date)

            if reset:
                with session_scope() as db:
                    delete_events_for_store_date(db, canonical, parsed_date)

            self.status = ReplayStatus(
                running=True,
                total=len(self._events),
                sent=0,
                batch_size=batch_size,
                interval_ms=interval_ms,
                store_id=store_id,
                target_date=target_date,
                started_at=datetime.now(timezone.utc).isoformat(),
                finished_at=None,
                error=None,
            )
            self._task = asyncio.create_task(self._run_loop(canonical))
            return self.status

    async def stop(self) -> ReplayStatus:
        async with self._lock:
            self.status.running = False
            if self._task and not self._task.done():
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass
            self._task = None
            if not self.status.finished_at:
                self.status.finished_at = datetime.now(timezone.utc).isoformat()
            return self.status

    async def _run_loop(self, canonical: str) -> None:
        try:
            batch_size = self.status.batch_size
            interval = self.status.interval_ms / 1000.0
            for offset in range(0, len(self._events), batch_size):
                if not self.status.running:
                    break
                batch = self._events[offset : offset + batch_size]
                with session_scope() as db:
                    ingest_raw_events(db, batch)
                last = batch[-1]
                self.status.sent = min(offset + len(batch), self.status.total)
                self.status.last_event_type = last.get("event_type")
                self.status.last_visitor_id = last.get("visitor_id")
                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self.status.error = str(exc)
        finally:
            self.status.running = False
            self.status.finished_at = datetime.now(timezone.utc).isoformat()


replay_manager = EventReplay()
