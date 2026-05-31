"""SQLite persistence for events and daily metric snapshots."""

from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import date, datetime
from typing import Generator, Iterator
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    create_engine,
    select,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from app import config

_engine = None
_SessionLocal = None


class Base(DeclarativeBase):
    pass


class EventRow(Base):
    __tablename__ = "events"

    event_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    store_id: Mapped[str] = mapped_column(String(32), index=True)
    camera_id: Mapped[str] = mapped_column(String(64))
    visitor_id: Mapped[str] = mapped_column(String(64), index=True)
    event_type: Mapped[str] = mapped_column(String(32), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    zone_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    dwell_ms: Mapped[int] = mapped_column(Integer, default=0)
    is_staff: Mapped[bool] = mapped_column(Boolean, default=False)
    confidence: Mapped[float] = mapped_column(Float)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")


class DailyMetricsSnapshot(Base):
    __tablename__ = "daily_metrics_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    store_id: Mapped[str] = mapped_column(String(32), index=True)
    snapshot_date: Mapped[date] = mapped_column(Date, index=True)
    unique_visitors: Mapped[int] = mapped_column(Integer)
    converted_visitors: Mapped[int] = mapped_column(Integer)
    conversion_rate: Mapped[float] = mapped_column(Float)
    total_transactions: Mapped[int] = mapped_column(Integer)
    computed_at: Mapped[datetime] = mapped_column(DateTime)


def get_engine():
    global _engine, _SessionLocal
    if _engine is None:
        connect_args = {"check_same_thread": False} if config.DATABASE_URL.startswith("sqlite") else {}
        _engine = create_engine(config.DATABASE_URL, connect_args=connect_args)
        _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)
    return _engine


def init_db() -> None:
    get_engine()
    Base.metadata.create_all(_engine)


def is_db_available() -> bool:
    try:
        with session_scope() as db:
            db.execute(select(func.count()).select_from(EventRow))
        return True
    except Exception:
        return False


@contextmanager
def session_scope() -> Iterator[Session]:
    if _SessionLocal is None:
        get_engine()
    db = _SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_db() -> Generator[Session, None, None]:
    if _SessionLocal is None:
        get_engine()
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()


def event_exists(db: Session, event_id: UUID) -> bool:
    return db.get(EventRow, str(event_id)) is not None


def insert_event(db: Session, event) -> None:
    db.add(
        EventRow(
            event_id=str(event.event_id),
            store_id=event.store_id,
            camera_id=event.camera_id,
            visitor_id=event.visitor_id,
            event_type=event.event_type.value,
            timestamp=event.timestamp.replace(tzinfo=None) if event.timestamp.tzinfo else event.timestamp,
            zone_id=event.zone_id,
            dwell_ms=event.dwell_ms,
            is_staff=event.is_staff,
            confidence=event.confidence,
            metadata_json=json.dumps(event.metadata.model_dump()),
        )
    )


def fetch_events_for_store_date(db: Session, store_id: str, target_date: date) -> list[EventRow]:
    start = datetime.combine(target_date, datetime.min.time())
    end = datetime.combine(target_date, datetime.max.time())
    rows = db.scalars(
        select(EventRow)
        .where(
            EventRow.store_id == store_id,
            EventRow.timestamp >= start,
            EventRow.timestamp <= end,
        )
        .order_by(EventRow.timestamp)
    ).all()
    return list(rows)


def last_event_timestamp(db: Session, store_id: str) -> datetime | None:
    return db.scalar(
        select(func.max(EventRow.timestamp)).where(EventRow.store_id == store_id)
    )


def upsert_daily_snapshot(
    db: Session,
    store_id: str,
    snapshot_date: date,
    unique_visitors: int,
    converted_visitors: int,
    conversion_rate: float,
    total_transactions: int,
    computed_at: datetime,
) -> None:
    existing = db.scalars(
        select(DailyMetricsSnapshot).where(
            DailyMetricsSnapshot.store_id == store_id,
            DailyMetricsSnapshot.snapshot_date == snapshot_date,
        )
    ).first()
    if existing:
        existing.unique_visitors = unique_visitors
        existing.converted_visitors = converted_visitors
        existing.conversion_rate = conversion_rate
        existing.total_transactions = total_transactions
        existing.computed_at = computed_at
    else:
        db.add(
            DailyMetricsSnapshot(
                store_id=store_id,
                snapshot_date=snapshot_date,
                unique_visitors=unique_visitors,
                converted_visitors=converted_visitors,
                conversion_rate=conversion_rate,
                total_transactions=total_transactions,
                computed_at=computed_at,
            )
        )


def fetch_snapshots(db: Session, store_id: str, before_date: date, limit: int = 7) -> list[DailyMetricsSnapshot]:
    rows = db.scalars(
        select(DailyMetricsSnapshot)
        .where(
            DailyMetricsSnapshot.store_id == store_id,
            DailyMetricsSnapshot.snapshot_date < before_date,
        )
        .order_by(DailyMetricsSnapshot.snapshot_date.desc())
        .limit(limit)
    ).all()
    return list(rows)
