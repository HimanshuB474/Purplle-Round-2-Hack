"""Event ingest with validation, dedup, and partial success."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.config import MAX_INGEST_BATCH
from app.db import event_exists, insert_event
from app.deps import require_db
from app.models import IngestResponse, StoreEvent
from app.stores import normalize_event_store_id

router = APIRouter()


def ingest_raw_events(db: Session, raw_events: list[Any]) -> IngestResponse:
    """Shared ingest logic for REST and dashboard replay."""
    accepted = 0
    rejected = 0
    errors: list[dict] = []

    for index, raw in enumerate(raw_events):
        if not isinstance(raw, dict):
            rejected += 1
            errors.append({"index": index, "event_id": None, "reason": "event must be an object"})
            continue

        event, error = _parse_event(raw, index)
        if error:
            rejected += 1
            errors.append(error)
            continue

        assert event is not None
        if event_exists(db, event.event_id):
            accepted += 1
            continue

        insert_event(db, event)
        accepted += 1

    db.commit()
    return IngestResponse(accepted=accepted, rejected=rejected, errors=errors)


def _parse_event(raw: dict, index: int) -> tuple[StoreEvent | None, dict | None]:
    try:
        event = StoreEvent.model_validate(raw)
        event.store_id = normalize_event_store_id(event.store_id)
        return event, None
    except ValidationError as exc:
        event_id = raw.get("event_id")
        reason = "validation failed"
        for err in exc.errors():
            if err.get("type") == "missing":
                reason = f"missing field: {err.get('loc', [''])[-1]}"
                break
            if "uuid" in str(err.get("type", "")).lower():
                reason = "invalid UUID format"
                break
            if err.get("loc") and err["loc"][-1] == "event_type":
                reason = "invalid event_type"
                break
        return None, {"index": index, "event_id": event_id, "reason": reason}


@router.post("/events/ingest", response_model=IngestResponse)
def ingest_events(
    request: Request,
    payload: dict[str, Any],
    db: Session = Depends(require_db),
) -> IngestResponse:
    raw_events = payload.get("events", [])
    request.state.ingest_event_count = len(raw_events) if isinstance(raw_events, list) else 0

    if not isinstance(raw_events, list):
        raise HTTPException(status_code=400, detail={"error": "invalid_payload", "reason": "events must be a list"})

    if len(raw_events) > MAX_INGEST_BATCH:
        raise HTTPException(
            status_code=400,
            detail={"error": "batch_too_large", "max_batch_size": MAX_INGEST_BATCH},
        )

    return ingest_raw_events(db, raw_events)
