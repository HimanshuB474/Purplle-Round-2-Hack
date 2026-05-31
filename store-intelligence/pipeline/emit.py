"""Event schema + JSONL emission — see docs/context/02-event-schema.md"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


def frame_to_timestamp(clip_base_iso: str, frame_index: int, fps: float) -> str:
    base = datetime.fromisoformat(clip_base_iso.replace("Z", "+00:00"))
    offset = timedelta(seconds=frame_index / fps)
    ts = base + offset
    return ts.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class EventEmitter:
    def __init__(self, store_id: str, camera_id: str) -> None:
        self.store_id = store_id
        self.camera_id = camera_id
        self.events: list[dict[str, Any]] = []

    def emit(
        self,
        *,
        visitor_id: str,
        event_type: str,
        timestamp: str,
        zone_id: str | None,
        dwell_ms: int,
        is_staff: bool,
        confidence: float,
        queue_depth: int | None = None,
        sku_zone: str | None = None,
        session_seq: int,
    ) -> None:
        self.events.append(
            {
                "event_id": str(uuid4()),
                "store_id": self.store_id,
                "camera_id": self.camera_id,
                "visitor_id": visitor_id,
                "event_type": event_type,
                "timestamp": timestamp,
                "zone_id": zone_id,
                "dwell_ms": dwell_ms,
                "is_staff": is_staff,
                "confidence": round(confidence, 2),
                "metadata": {
                    "queue_depth": queue_depth,
                    "sku_zone": sku_zone,
                    "session_seq": session_seq,
                },
            }
        )

    def extend(self, other: "EventEmitter") -> None:
        self.events.extend(other.events)


def write_jsonl(events: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(e, separators=(",", ":")) for e in sorted(events, key=lambda x: x["timestamp"])]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
