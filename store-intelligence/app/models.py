"""Pydantic models — see docs/context/02-event-schema.md"""

from enum import Enum
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class EventType(str, Enum):
    ENTRY = "ENTRY"
    EXIT = "EXIT"
    ZONE_ENTER = "ZONE_ENTER"
    ZONE_EXIT = "ZONE_EXIT"
    ZONE_DWELL = "ZONE_DWELL"
    BILLING_QUEUE_JOIN = "BILLING_QUEUE_JOIN"
    BILLING_QUEUE_ABANDON = "BILLING_QUEUE_ABANDON"
    REENTRY = "REENTRY"


class EventMetadata(BaseModel):
    queue_depth: Optional[int] = None
    sku_zone: Optional[str] = None
    session_seq: int


class StoreEvent(BaseModel):
    event_id: UUID
    store_id: str
    camera_id: str
    visitor_id: str
    event_type: EventType
    timestamp: datetime
    zone_id: Optional[str]
    dwell_ms: int = Field(ge=0)
    is_staff: bool
    confidence: float = Field(ge=0.0, le=1.0)
    metadata: EventMetadata


class IngestRequest(BaseModel):
    events: list[StoreEvent]


class IngestResponse(BaseModel):
    accepted: int
    rejected: int
    errors: list[dict] = Field(default_factory=list)


class MetricsResponse(BaseModel):
    store_id: str
    date: str
    unique_visitors: int
    converted_visitors: int
    conversion_rate: float
    total_transactions: int
    avg_basket_value_inr: float
    queue_depth_current: int
    abandonment_rate: float
    avg_dwell_by_zone_ms: dict[str, int]
    computed_at: datetime


class FunnelStage(BaseModel):
    stage: str
    count: int
    drop_off_pct: float


class FunnelResponse(BaseModel):
    store_id: str
    date: str
    stages: list[FunnelStage]
    total_sessions: int
    computed_at: datetime


class HeatmapZone(BaseModel):
    zone_id: str
    visit_count: int
    avg_dwell_ms: int
    visit_score: int
    dwell_score: int
    combined_score: int


class HeatmapResponse(BaseModel):
    store_id: str
    date: str
    data_confidence: str
    zones: list[HeatmapZone]
    computed_at: datetime


class AnomalyItem(BaseModel):
    type: str
    severity: str
    detected_at: datetime
    detail: str
    suggested_action: str


class AnomaliesResponse(BaseModel):
    store_id: str
    anomalies: list[AnomalyItem]
    computed_at: datetime


class HealthStoreStatus(BaseModel):
    store_id: str
    last_event_at: Optional[datetime] = None
    lag_seconds: Optional[int] = None
    feed_status: str


class HealthResponse(BaseModel):
    status: str
    version: str
    stores: list[HealthStoreStatus]
    warnings: list[str]
    computed_at: datetime
