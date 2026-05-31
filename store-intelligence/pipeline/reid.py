"""Cross-camera visitor linking — time window + optional appearance (HSV histogram)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import cv2
import numpy as np

from pipeline.config import (
    REID_APPEARANCE_MIN_CORRELATION,
    REID_ENABLED,
    REID_TIME_GAP_SEC,
    REID_USE_APPEARANCE,
)


def parse_event_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)


def appearance_histogram(frame: np.ndarray, x1: float, y1: float, x2: float, y2: float) -> np.ndarray:
    """Upper-body HSV histogram for lightweight Re-ID."""
    h, w = frame.shape[:2]
    x1i, y1i = max(0, int(x1)), max(0, int(y1))
    x2i, y2i = min(w, int(x2)), min(h, int(y2))
    if x2i <= x1i or y2i <= y1i:
        return np.zeros(512, dtype=np.float32)
    crop = frame[y1i:y2i, x1i:x2i]
    mid = y1i + (y2i - y1i) // 3
    crop = frame[y1i:mid, x1i:x2i]
    if crop.size == 0:
        return np.zeros(512, dtype=np.float32)
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist([hsv], [0, 1, 2], None, [8, 8, 8], [0, 180, 0, 256, 0, 256])
    cv2.normalize(hist, hist)
    return hist.flatten().astype(np.float32)


def histogram_correlation(a: np.ndarray, b: np.ndarray) -> float:
    if a.size == 0 or b.size == 0:
        return 0.0
    return float(cv2.compareHist(a.reshape(-1, 1), b.reshape(-1, 1), cv2.HISTCMP_CORREL))


@dataclass
class ActiveVisitor:
    visitor_id: str
    last_seen: datetime
    camera_id: str
    is_staff: bool = False
    appearance: np.ndarray | None = None
    has_entry: bool = False


@dataclass
class CrossCameraRegistry:
    """Tracks open visitors for time/appearance merge across clips."""

    gap: timedelta = field(default_factory=lambda: timedelta(seconds=REID_TIME_GAP_SEC))
    use_appearance: bool = REID_USE_APPEARANCE
    min_correlation: float = REID_APPEARANCE_MIN_CORRELATION
    active: dict[str, ActiveVisitor] = field(default_factory=dict)

    def register(
        self,
        visitor_id: str,
        *,
        camera_id: str,
        timestamp: datetime,
        is_staff: bool,
        appearance: np.ndarray | None = None,
        has_entry: bool = False,
    ) -> None:
        if is_staff:
            return
        existing = self.active.get(visitor_id)
        if existing:
            existing.last_seen = max(existing.last_seen, timestamp)
            existing.camera_id = camera_id
            if appearance is not None:
                if existing.appearance is None:
                    existing.appearance = appearance
                else:
                    existing.appearance = 0.7 * existing.appearance + 0.3 * appearance
            if has_entry:
                existing.has_entry = True
        else:
            self.active[visitor_id] = ActiveVisitor(
                visitor_id=visitor_id,
                last_seen=timestamp,
                camera_id=camera_id,
                is_staff=False,
                appearance=appearance,
                has_entry=has_entry,
            )

    def prune(self, now: datetime) -> None:
        stale = [vid for vid, av in self.active.items() if now - av.last_seen > self.gap * 2]
        for vid in stale:
            del self.active[vid]

    def match_or_none(
        self,
        *,
        timestamp: datetime,
        camera_id: str,
        appearance: np.ndarray | None,
        is_staff: bool,
    ) -> str | None:
        if is_staff or not REID_ENABLED:
            return None
        self.prune(timestamp)
        candidates: list[tuple[str, float]] = []
        for av in self.active.values():
            if av.is_staff:
                continue
            if av.camera_id == camera_id:
                continue
            dt = (timestamp - av.last_seen).total_seconds()
            if dt < 0 or dt > self.gap.total_seconds():
                continue
            if self.use_appearance and appearance is not None and av.appearance is not None:
                corr = histogram_correlation(appearance, av.appearance)
                if corr >= self.min_correlation:
                    candidates.append((av.visitor_id, corr))
            elif not self.use_appearance and av.has_entry:
                candidates.append((av.visitor_id, 1.0 - dt / max(self.gap.total_seconds(), 1)))

        if not candidates:
            return None
        return max(candidates, key=lambda x: x[1])[0]


def merge_visitor_ids_post(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Second pass: link floor-camera first activity to nearest prior ENTRY cam visitor."""
    if not REID_ENABLED or not events:
        return events

    entry_times: dict[str, datetime] = {}
    for event in events:
        if event.get("is_staff"):
            continue
        if event.get("event_type") != "ENTRY":
            continue
        if "CAM_ENTRY" not in event.get("camera_id", ""):
            continue
        ts = parse_event_ts(event["timestamp"])
        entry_times.setdefault(event["visitor_id"], ts)

    remap: dict[str, str] = {}
    gap = timedelta(seconds=REID_TIME_GAP_SEC)
    sorted_events = sorted(events, key=lambda e: e["timestamp"])

    for event in sorted_events:
        if event.get("is_staff"):
            continue
        vid = event["visitor_id"]
        if vid in remap:
            continue
        if "CAM_ENTRY" in event.get("camera_id", ""):
            continue
        ts = parse_event_ts(event["timestamp"])
        candidates: list[tuple[str, float]] = []
        for entry_vid, entry_ts in entry_times.items():
            if entry_ts > ts:
                continue
            dt = (ts - entry_ts).total_seconds()
            if dt > gap.total_seconds():
                continue
            candidates.append((entry_vid, dt))
        if len(candidates) != 1:
            continue
        best_entry, _ = candidates[0]
        if best_entry != vid:
            remap[vid] = best_entry

    if not remap:
        return events

    def resolve(vid: str) -> str:
        while vid in remap and remap[vid] != vid:
            vid = remap[vid]
        return vid

    for event in events:
        old = event["visitor_id"]
        new = resolve(old)
        if new != old:
            event["visitor_id"] = new
    return events
