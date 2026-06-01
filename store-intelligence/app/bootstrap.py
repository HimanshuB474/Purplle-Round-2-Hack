"""Seed committed events on empty DB (cloud cold start)."""

from __future__ import annotations

import json
import logging
import os
from datetime import date
from pathlib import Path

from app.config import ROOT
from app.db import count_events_for_store_date, session_scope
from app.ingestion import ingest_raw_events

logger = logging.getLogger(__name__)

EVENTS_PATH = ROOT / "data" / "events.jsonl"
REFERENCE_STORE = "ST1008"
REFERENCE_DATE = date(2026, 4, 10)


def _auto_ingest_enabled() -> bool:
    return os.getenv("AUTO_INGEST_ON_STARTUP", "1").strip().lower() in ("1", "true", "yes", "on")


def seed_events_if_empty() -> None:
    """Load events.jsonl when the reference day has no rows (Render/Railway ephemeral SQLite)."""
    if not _auto_ingest_enabled():
        return
    if not EVENTS_PATH.is_file():
        logger.warning("bootstrap: %s not found", EVENTS_PATH)
        return

    lines = [ln for ln in EVENTS_PATH.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if not lines:
        return

    events = [json.loads(ln) for ln in lines]
    with session_scope() as db:
        existing = count_events_for_store_date(db, REFERENCE_STORE, REFERENCE_DATE)
        if existing > 0:
            logger.info("bootstrap: skip ingest (%s events already loaded)", existing)
            return
        result = ingest_raw_events(db, events)
    logger.info(
        "bootstrap: ingested %s events (accepted=%s rejected=%s)",
        len(events),
        result.accepted,
        result.rejected,
    )
