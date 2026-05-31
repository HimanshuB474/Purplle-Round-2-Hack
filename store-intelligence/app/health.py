"""Health endpoint — see docs/context/05-api-contracts.md §12.6"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.config import API_VERSION, STALE_FEED_SECONDS
from app.db import is_db_available, last_event_timestamp, session_scope
from app.models import HealthResponse, HealthStoreStatus
from app.stores import KNOWN_STORES, canonical_store_id

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    if not is_db_available():
        raise HTTPException(status_code=503, detail={"status": "UNAVAILABLE", "reason": "database_unavailable"})

    now = datetime.now(timezone.utc)
    stores: list[HealthStoreStatus] = []
    warnings: list[str] = []

    with session_scope() as db:
        for store_id in sorted(KNOWN_STORES):
            canonical = canonical_store_id(store_id)
            last_at = last_event_timestamp(db, canonical)
            if last_at is None:
                stores.append(
                    HealthStoreStatus(
                        store_id=store_id,
                        feed_status="OK",
                    )
                )
                continue

            last_utc = last_at.replace(tzinfo=timezone.utc)
            lag = int((now - last_utc).total_seconds())
            feed_status = "STALE_FEED" if lag > STALE_FEED_SECONDS else "OK"
            if feed_status == "STALE_FEED":
                warnings.append(f"{store_id}: last event {lag}s ago")

            stores.append(
                HealthStoreStatus(
                    store_id=store_id,
                    last_event_at=last_utc,
                    lag_seconds=lag,
                    feed_status=feed_status,
                )
            )

    return HealthResponse(
        status="OK",
        version=API_VERSION,
        stores=stores,
        warnings=warnings,
        computed_at=now,
    )
