"""Store metrics computation — see docs/context/05-api-contracts.md §12.2"""

from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import fetch_events_for_store_date, upsert_daily_snapshot
from app.deps import require_db
from app.models import MetricsResponse
from app.pos import get_transactions_for_store_date
from app.sessions import (
    abandonment_rate,
    apply_pos_conversions,
    avg_dwell_by_zone,
    customer_sessions,
    queue_depth_current,
    unique_visitors_with_entry,
)
from app.stores import canonical_store_id

router = APIRouter()


def compute_metrics(canonical: str, display_store_id: str, target_date: date, db: Session) -> MetricsResponse:
    events = fetch_events_for_store_date(db, canonical, target_date)
    sessions = customer_sessions(events)
    transactions = get_transactions_for_store_date(canonical, target_date)
    apply_pos_conversions(sessions, transactions)

    unique = unique_visitors_with_entry(events)
    converted = {s.visitor_id for s in sessions if s.converted}
    unique_count = len(unique)
    converted_count = len(converted & unique)
    conversion_rate = round(converted_count / unique_count, 4) if unique_count else 0.0

    total_transactions = len(transactions)
    avg_basket = (
        round(sum(t.basket_value_inr for t in transactions) / total_transactions, 2)
        if total_transactions
        else 0.0
    )

    computed_at = datetime.now(timezone.utc)
    upsert_daily_snapshot(
        db,
        canonical,
        target_date,
        unique_count,
        converted_count,
        conversion_rate,
        total_transactions,
        computed_at.replace(tzinfo=None),
    )
    db.commit()

    return MetricsResponse(
        store_id=display_store_id,
        date=target_date.isoformat(),
        unique_visitors=unique_count,
        converted_visitors=converted_count,
        conversion_rate=conversion_rate,
        total_transactions=total_transactions,
        avg_basket_value_inr=avg_basket,
        queue_depth_current=queue_depth_current(events),
        abandonment_rate=abandonment_rate(sessions),
        avg_dwell_by_zone_ms=avg_dwell_by_zone(events),
        computed_at=computed_at,
    )


@router.get("/stores/{store_id}/metrics", response_model=MetricsResponse)
def get_metrics(
    store_id: str,
    date: date | None = Query(default=None, alias="date"),
    db: Session = Depends(require_db),
) -> MetricsResponse:
    canonical = canonical_store_id(store_id)
    target_date = date or datetime.now(timezone.utc).date()
    return compute_metrics(canonical, store_id, target_date, db)
