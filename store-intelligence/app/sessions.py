"""Session model and analytics helpers — see docs/context/04-pos-and-business-logic.md"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, datetime

from app.db import EventRow
from app.pos import PosTransaction, conversion_window_start

BILLING_EVENT_TYPES = frozenset({"BILLING_QUEUE_JOIN", "BILLING_QUEUE_ABANDON"})
ZONE_EVENT_TYPES = frozenset({"ZONE_ENTER", "ZONE_EXIT", "ZONE_DWELL"})


@dataclass
class VisitorSession:
    visitor_id: str
    started_at: datetime
    ended_at: datetime | None = None
    is_staff: bool = False
    has_entry: bool = False
    reached_zone: bool = False
    reached_billing: bool = False
    converted: bool = False
    abandoned_billing: bool = False
    events: list[EventRow] = field(default_factory=list)


def _is_billing_event(event: EventRow) -> bool:
    if event.event_type in BILLING_EVENT_TYPES:
        return True
    return event.zone_id == "BILLING" and event.event_type in ZONE_EVENT_TYPES | {"ZONE_ENTER"}


def _event_metadata(event: EventRow) -> dict:
    try:
        return json.loads(event.metadata_json or "{}")
    except json.JSONDecodeError:
        return {}


def build_sessions(events: list[EventRow]) -> list[VisitorSession]:
    by_visitor: dict[str, list[EventRow]] = {}
    for event in sorted(events, key=lambda e: e.timestamp):
        by_visitor.setdefault(event.visitor_id, []).append(event)

    sessions: list[VisitorSession] = []
    for visitor_id, visitor_events in by_visitor.items():
        current: VisitorSession | None = None
        for event in visitor_events:
            if event.event_type == "ENTRY":
                if current is not None:
                    sessions.append(current)
                current = VisitorSession(
                    visitor_id=visitor_id,
                    started_at=event.timestamp,
                    is_staff=event.is_staff,
                    has_entry=True,
                )
            elif event.event_type == "REENTRY":
                if current is not None:
                    sessions.append(current)
                current = VisitorSession(
                    visitor_id=visitor_id,
                    started_at=event.timestamp,
                    is_staff=event.is_staff,
                    has_entry=False,
                )
            elif current is None:
                current = VisitorSession(
                    visitor_id=visitor_id,
                    started_at=event.timestamp,
                    is_staff=event.is_staff,
                )

            current.events.append(event)
            current.is_staff = current.is_staff or event.is_staff

            if event.event_type in ZONE_EVENT_TYPES or event.event_type == "ZONE_ENTER":
                if event.zone_id and event.zone_id != "ENTRY":
                    current.reached_zone = True

            if _is_billing_event(event):
                current.reached_billing = True

            if event.event_type == "BILLING_QUEUE_ABANDON":
                current.abandoned_billing = True

            if event.event_type == "EXIT":
                current.ended_at = event.timestamp
                sessions.append(current)
                current = None

        if current is not None:
            sessions.append(current)

    return sessions


def customer_sessions(events: list[EventRow]) -> list[VisitorSession]:
    return [s for s in build_sessions(events) if not s.is_staff]


def unique_visitors_with_entry(events: list[EventRow]) -> set[str]:
    visitors: set[str] = set()
    for event in events:
        if event.is_staff:
            continue
        if event.event_type == "ENTRY":
            visitors.add(event.visitor_id)
    return visitors


def apply_pos_conversions(sessions: list[VisitorSession], transactions: list[PosTransaction]) -> None:
    """Assign at most one converted visitor per POS transaction (closest billing in window)."""
    eligible = [s for s in sessions if not s.is_staff and s.reached_billing]
    assigned: set[str] = set()

    for txn in sorted(transactions, key=lambda t: t.timestamp):
        window_start = conversion_window_start(txn.timestamp)
        best_session: VisitorSession | None = None
        best_delta: float | None = None

        for session in eligible:
            if session.visitor_id in assigned:
                continue
            billing_times = [e.timestamp for e in session.events if _is_billing_event(e)]
            qualifying = [ts for ts in billing_times if window_start <= ts <= txn.timestamp]
            if not qualifying:
                continue
            last_billing = max(qualifying)
            delta = (txn.timestamp - last_billing).total_seconds()
            if best_delta is None or delta < best_delta:
                best_delta = delta
                best_session = session

        if best_session is not None:
            best_session.converted = True
            assigned.add(best_session.visitor_id)


def funnel_counts(sessions: list[VisitorSession], events: list[EventRow]) -> dict[str, int]:
    entry_visitors = unique_visitors_with_entry(events)
    zone_visitors: set[str] = set()
    billing_visitors: set[str] = set()
    purchase_visitors: set[str] = set()

    for event in events:
        if event.is_staff:
            continue
        if event.event_type in ZONE_EVENT_TYPES and event.zone_id and event.zone_id != "ENTRY":
            zone_visitors.add(event.visitor_id)
        if _is_billing_event(event):
            billing_visitors.add(event.visitor_id)

    for session in sessions:
        if session.converted:
            purchase_visitors.add(session.visitor_id)

    return {
        "ENTRY": len(entry_visitors),
        "ZONE_VISIT": len(zone_visitors & entry_visitors),
        "BILLING_QUEUE": len(billing_visitors & entry_visitors),
        "PURCHASE": len(purchase_visitors & entry_visitors),
    }


def drop_off_pct(previous: int, current: int) -> float:
    if previous <= 0:
        return 0.0
    return round(((previous - current) / previous) * 100, 1)


def billing_sessions_count(sessions: list[VisitorSession]) -> int:
    return sum(1 for s in sessions if s.reached_billing)


def abandonment_rate(sessions: list[VisitorSession]) -> float:
    billing = billing_sessions_count(sessions)
    if billing == 0:
        return 0.0
    abandoned = sum(1 for s in sessions if s.abandoned_billing)
    return round(abandoned / billing, 4)


def avg_dwell_by_zone(events: list[EventRow]) -> dict[str, int]:
    totals: dict[str, list[int]] = {}
    for event in events:
        if event.is_staff:
            continue
        if event.event_type != "ZONE_DWELL" or not event.zone_id:
            continue
        totals.setdefault(event.zone_id, []).append(event.dwell_ms)
    return {zone: int(sum(values) / len(values)) for zone, values in totals.items()}


def queue_depth_current(events: list[EventRow]) -> int:
    for event in reversed(events):
        if event.event_type == "BILLING_QUEUE_JOIN":
            depth = _event_metadata(event).get("queue_depth")
            if depth is not None:
                return int(depth)
    return 0


def zone_visit_stats(events: list[EventRow]) -> dict[str, dict[str, float | int]]:
    stats: dict[str, dict[str, float | int]] = {}
    for event in events:
        if event.is_staff:
            continue
        if event.event_type != "ZONE_ENTER" or not event.zone_id:
            continue
        zone = event.zone_id
        bucket = stats.setdefault(zone, {"visit_count": 0, "dwell_total": 0, "dwell_count": 0})
        bucket["visit_count"] = int(bucket["visit_count"]) + 1

    for event in events:
        if event.is_staff:
            continue
        if event.event_type != "ZONE_DWELL" or not event.zone_id:
            continue
        zone = event.zone_id
        bucket = stats.setdefault(zone, {"visit_count": 0, "dwell_total": 0, "dwell_count": 0})
        bucket["dwell_total"] = float(bucket["dwell_total"]) + event.dwell_ms
        bucket["dwell_count"] = int(bucket["dwell_count"]) + 1

    for zone, bucket in stats.items():
        dwell_count = int(bucket["dwell_count"])
        bucket["avg_dwell_ms"] = int(bucket["dwell_total"] / dwell_count) if dwell_count else 0
    return stats
