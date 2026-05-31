"""Live dashboard — Part E bonus. Serves UI + replay API."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.anomalies import compute_anomalies
from app.dashboard_replay import replay_manager
from app.db import count_events_for_store_date
from app.deps import require_db
from app.funnel import compute_funnel
from app.health import build_health_response
from app.metrics import compute_metrics
from app.stores import canonical_store_id

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

_STATIC = Path(__file__).resolve().parents[1] / "dashboard" / "static"


@router.get("", include_in_schema=False)
@router.get("/", include_in_schema=False)
def dashboard_page() -> FileResponse:
    index = _STATIC / "index.html"
    if not index.is_file():
        raise HTTPException(status_code=503, detail="dashboard static files missing")
    return FileResponse(index, media_type="text/html")


@router.get("/api/snapshot")
def dashboard_snapshot(
    store_id: str = Query("ST1008"),
    target_date: str = Query("2026-04-10"),
    db: Session = Depends(require_db),
) -> dict:
    canonical = canonical_store_id(store_id)
    parsed = date.fromisoformat(target_date)
    metrics = compute_metrics(canonical, store_id, parsed, db)
    funnel = compute_funnel(canonical, store_id, parsed, db)
    health = build_health_response(db)
    anomalies = compute_anomalies(canonical, store_id, parsed, db)
    ingested = count_events_for_store_date(db, canonical, parsed)

    return {
        "metrics": metrics.model_dump(mode="json"),
        "funnel": funnel.model_dump(mode="json"),
        "health": health.model_dump(mode="json"),
        "anomalies": anomalies.model_dump(mode="json"),
        "ingested_events": ingested,
        "replay": replay_manager.status.to_dict(),
    }


@router.post("/api/replay/start")
async def replay_start(
    store_id: str = Query("ST1008"),
    target_date: str = Query("2026-04-10"),
    reset: bool = Query(True, description="Clear existing events for this store/date before replay"),
    batch_size: int = Query(12, ge=1, le=100),
    interval_ms: int = Query(700, ge=100, le=5000),
) -> dict:
    status = await replay_manager.start(
        store_id=store_id,
        target_date=target_date,
        reset=reset,
        batch_size=batch_size,
        interval_ms=interval_ms,
    )
    if status.error and not status.running:
        raise HTTPException(status_code=400, detail=status.error)
    return status.to_dict()


@router.post("/api/replay/stop")
async def replay_stop() -> dict:
    return (await replay_manager.stop()).to_dict()


@router.get("/api/replay/status")
def replay_status() -> dict:
    return replay_manager.status.to_dict()
