"""Shared FastAPI dependencies."""

from __future__ import annotations

from collections.abc import Generator

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db, is_db_available


def _service_unavailable(reason: str) -> dict:
    return {"status": "UNAVAILABLE", "reason": reason}


def require_db() -> Generator[Session, None, None]:
    if not is_db_available():
        raise HTTPException(status_code=503, detail=_service_unavailable("database_unavailable"))
    yield from get_db()


def get_db_session(db: Session = Depends(require_db)) -> Session:
    return db
