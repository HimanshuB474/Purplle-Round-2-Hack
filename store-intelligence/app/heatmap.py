"""Zone heatmap scores — see docs/context/05-api-contracts.md §12.4"""

from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.config import HEATMAP_LOW_CONFIDENCE_SESSIONS
from app.db import fetch_events_for_store_date
from app.deps import require_db
from app.models import HeatmapResponse, HeatmapZone
from app.sessions import customer_sessions, zone_visit_stats
from app.stores import canonical_store_id

router = APIRouter()


def _normalize_scores(stats: dict[str, dict]) -> list[HeatmapZone]:
    if not stats:
        return []

    max_visits = max(int(v["visit_count"]) for v in stats.values()) or 1
    max_dwell = max(int(v.get("avg_dwell_ms", 0)) for v in stats.values()) or 1

    zones: list[HeatmapZone] = []
    for zone_id, bucket in sorted(stats.items()):
        visit_count = int(bucket["visit_count"])
        avg_dwell_ms = int(bucket.get("avg_dwell_ms", 0))
        visit_score = int(round((visit_count / max_visits) * 100))
        dwell_score = int(round((avg_dwell_ms / max_dwell) * 100))
        combined_score = int(round((visit_score + dwell_score) / 2))
        zones.append(
            HeatmapZone(
                zone_id=zone_id,
                visit_count=visit_count,
                avg_dwell_ms=avg_dwell_ms,
                visit_score=visit_score,
                dwell_score=dwell_score,
                combined_score=combined_score,
            )
        )
    return zones


def compute_heatmap(store_id: str, target_date: date, db) -> HeatmapResponse:
    canonical = canonical_store_id(store_id)
    events = fetch_events_for_store_date(db, canonical, target_date)
    sessions = customer_sessions(events)
    stats = zone_visit_stats(events)
    session_count = len({s.visitor_id for s in sessions if s.has_entry or s.reached_zone})

    return HeatmapResponse(
        store_id=store_id,
        date=target_date.isoformat(),
        data_confidence="LOW" if session_count < HEATMAP_LOW_CONFIDENCE_SESSIONS else "HIGH",
        zones=_normalize_scores(stats),
        computed_at=datetime.now(timezone.utc),
    )


@router.get("/stores/{store_id}/heatmap", response_model=HeatmapResponse)
def get_heatmap(
    store_id: str,
    date: date | None = Query(default=None, alias="date"),
    db: Session = Depends(require_db),
) -> HeatmapResponse:
    canonical_store_id(store_id)
    target_date = date or datetime.now(timezone.utc).date()
    return compute_heatmap(store_id, target_date, db)
