"""Conversion funnel — see docs/context/05-api-contracts.md §12.3"""

from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import fetch_events_for_store_date
from app.deps import require_db
from app.models import FunnelResponse, FunnelStage
from app.pos import get_transactions_for_store_date
from app.sessions import apply_pos_conversions, customer_sessions, drop_off_pct, funnel_counts
from app.stores import canonical_store_id

router = APIRouter()

STAGE_ORDER = ["ENTRY", "ZONE_VISIT", "BILLING_QUEUE", "PURCHASE"]


def compute_funnel(canonical: str, display_store_id: str, target_date: date, db) -> FunnelResponse:
    events = fetch_events_for_store_date(db, canonical, target_date)
    sessions = customer_sessions(events)
    transactions = get_transactions_for_store_date(canonical, target_date)
    apply_pos_conversions(sessions, transactions)

    counts = funnel_counts(sessions, events)
    stages: list[FunnelStage] = []
    previous = counts["ENTRY"]
    for idx, stage in enumerate(STAGE_ORDER):
        current = counts[stage]
        stages.append(
            FunnelStage(
                stage=stage,
                count=current,
                drop_off_pct=0.0 if idx == 0 else drop_off_pct(previous, current),
            )
        )
        previous = current

    return FunnelResponse(
        store_id=display_store_id,
        date=target_date.isoformat(),
        stages=stages,
        total_sessions=counts["ENTRY"],
        computed_at=datetime.now(timezone.utc),
    )


@router.get("/stores/{store_id}/funnel", response_model=FunnelResponse)
def get_funnel(
    store_id: str,
    date: date | None = Query(default=None, alias="date"),
    db: Session = Depends(require_db),
) -> FunnelResponse:
    canonical = canonical_store_id(store_id)
    target_date = date or datetime.now(timezone.utc).date()
    return compute_funnel(canonical, store_id, target_date, db)
