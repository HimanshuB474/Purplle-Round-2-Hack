"""Anomaly detection — see docs/context/05-api-contracts.md §12.5"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.config import (
    CONVERSION_DROP_PCT,
    DEAD_ZONE_MINUTES,
    QUEUE_SPIKE_MIN_SECONDS,
    QUEUE_SPIKE_THRESHOLD,
)
from app.db import fetch_events_for_store_date, fetch_snapshots
from app.deps import require_db
from app.metrics import compute_metrics
from app.models import AnomaliesResponse, AnomalyItem
from app.sessions import customer_sessions, zone_visit_stats
from app.stores import canonical_store_id

router = APIRouter()


def _metadata(event) -> dict:
    try:
        return json.loads(event.metadata_json or "{}")
    except json.JSONDecodeError:
        return {}


def detect_queue_spike(events) -> AnomalyItem | None:
    join_events = [e for e in events if e.event_type == "BILLING_QUEUE_JOIN"]
    if not join_events:
        return None

    sustained_start: datetime | None = None
    for event in join_events:
        depth = _metadata(event).get("queue_depth", 0)
        if depth and int(depth) > QUEUE_SPIKE_THRESHOLD:
            if sustained_start is None:
                sustained_start = event.timestamp
            elif (event.timestamp - sustained_start).total_seconds() >= QUEUE_SPIKE_MIN_SECONDS:
                return AnomalyItem(
                    type="BILLING_QUEUE_SPIKE",
                    severity="WARN" if int(depth) <= 4 else "CRITICAL",
                    detected_at=event.timestamp.replace(tzinfo=timezone.utc),
                    detail=f"Queue depth reached {depth} at billing counter",
                    suggested_action="Open additional billing counter or deploy floor staff to assist queue",
                )
        else:
            sustained_start = None
    return None


def detect_conversion_drop(canonical: str, display_store_id: str, target_date: date, db) -> AnomalyItem | None:
    metrics = compute_metrics(canonical, display_store_id, target_date, db)
    snapshots = fetch_snapshots(db, canonical, target_date, limit=7)
    if not snapshots:
        return None

    baseline = sum(s.conversion_rate for s in snapshots) / len(snapshots)
    if baseline <= 0:
        return None

    drop_pct = ((baseline - metrics.conversion_rate) / baseline) * 100
    if drop_pct <= CONVERSION_DROP_PCT:
        return None

    severity = "WARN" if drop_pct <= 35 else "CRITICAL"
    return AnomalyItem(
        type="CONVERSION_DROP",
        severity=severity,
        detected_at=datetime.combine(target_date, datetime.max.time()).replace(tzinfo=timezone.utc),
        detail=f"Conversion rate {metrics.conversion_rate * 100:.0f}% vs 7-day avg {baseline * 100:.0f}%",
        suggested_action="Review staffing at billing; check for stock-outs in top dwell zones",
    )


def detect_dead_zones(events, target_date: date) -> list[AnomalyItem]:
    zone_last_enter: dict[str, datetime] = {}
    for event in events:
        if event.is_staff or event.event_type != "ZONE_ENTER" or not event.zone_id:
            continue
        zone_last_enter[event.zone_id] = event.timestamp

    day_end = datetime.combine(target_date, datetime.max.time())
    cutoff = timedelta(minutes=DEAD_ZONE_MINUTES)
    anomalies: list[AnomalyItem] = []
    for zone_id, last_seen in zone_last_enter.items():
        if day_end - last_seen >= cutoff:
            anomalies.append(
                AnomalyItem(
                    type="DEAD_ZONE",
                    severity="INFO" if (day_end - last_seen).total_seconds() < 3600 else "WARN",
                    detected_at=(last_seen + cutoff).replace(tzinfo=timezone.utc),
                    detail=f"Zone {zone_id} had no visits for {DEAD_ZONE_MINUTES} minutes",
                    suggested_action="Verify camera coverage; consider repositioning displays",
                )
            )
    return anomalies


def compute_anomalies(canonical: str, display_store_id: str, target_date: date, db) -> AnomaliesResponse:
    events = fetch_events_for_store_date(db, canonical, target_date)
    anomalies: list[AnomalyItem] = []

    queue = detect_queue_spike(events)
    if queue:
        anomalies.append(queue)

    conversion = detect_conversion_drop(canonical, display_store_id, target_date, db)
    if conversion:
        anomalies.append(conversion)

    anomalies.extend(detect_dead_zones(events, target_date))

    return AnomaliesResponse(
        store_id=display_store_id,
        anomalies=anomalies,
        computed_at=datetime.now(timezone.utc),
    )


@router.get("/stores/{store_id}/anomalies", response_model=AnomaliesResponse)
def get_anomalies(
    store_id: str,
    date: date | None = Query(default=None, alias="date"),
    db: Session = Depends(require_db),
) -> AnomaliesResponse:
    canonical = canonical_store_id(store_id)
    target_date = date or datetime.now(timezone.utc).date()
    return compute_anomalies(canonical, store_id, target_date, db)
