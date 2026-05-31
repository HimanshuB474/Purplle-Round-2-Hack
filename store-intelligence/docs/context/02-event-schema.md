# Event Schema

> Part of [Project Context Index](./README.md)

---

## 3. Event Schema (Required Output)

Every event your detection pipeline emits must follow this structure:

```json
{
  "event_id": "uuid-v4",
  "store_id": "STORE_BLR_002",
  "camera_id": "CAM_ENTRY_01",
  "visitor_id": "VIS_c8a2f1",
  "event_type": "ZONE_DWELL",
  "timestamp": "2026-03-03T14:22:10Z",
  "zone_id": "SKINCARE",
  "dwell_ms": 8400,
  "is_staff": false,
  "confidence": 0.91,
  "metadata": {
    "queue_depth": null,
    "sku_zone": "MOISTURISER",
    "session_seq": 5
  }
}
```

### Event Type Catalogue

| Event Type | When to Emit | Notes |
|------------|--------------|-------|
| `ENTRY` | Visitor crosses entry threshold (inbound) | Starts new session; assign new `visitor_id` |
| `EXIT` | Visitor crosses entry threshold (outbound) | Closes session |
| `ZONE_ENTER` | Visitor enters a named zone | Zone names from `store_layout.json` |
| `ZONE_EXIT` | Visitor leaves a named zone | |
| `ZONE_DWELL` | Visitor in zone continuously 30+ seconds | Emit every 30s of continued dwell |
| `BILLING_QUEUE_JOIN` | Visitor enters billing zone while `queue_depth > 0` | Set `queue_depth` in metadata |
| `BILLING_QUEUE_ABANDON` | Visitor leaves billing before POS transaction | Requires POS correlation |
| `REENTRY` | Same `visitor_id` detected after prior `EXIT` | Re-ID must catch this |

**Rules:**
- Do **not** suppress low-confidence events — flag them via `confidence`
- `event_id` must be globally unique (UUID v4)
- Timestamps: ISO-8601 UTC, derived from clip + frame offset
- `zone_id`: null for ENTRY/EXIT events only
- Full field validation: [Appendix B](#appendix-b-event-schema-validation-checklist)

### Pydantic Model Hint

```python
from enum import Enum
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional

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
```

---

## Appendix B: Event Schema Validation Checklist

| Field | Type | Required | Rules |
|-------|------|----------|-------|
| `event_id` | UUID v4 string | Yes | Globally unique |
| `store_id` | string | Yes | e.g. ST1008 |
| `camera_id` | string | Yes | From store_layout.json |
| `visitor_id` | string | Yes | e.g. VIS_abc123 |
| `event_type` | enum | Yes | 8 allowed values |
| `timestamp` | ISO-8601 UTC | Yes | Derived from frame + clip base |
| `zone_id` | string or null | Yes | null only for ENTRY/EXIT |
| `dwell_ms` | int | Yes | ≥0; 0 for instantaneous |
| `is_staff` | bool | Yes | |
| `confidence` | float | Yes | 0.0–1.0; do not filter low values |
| `metadata.queue_depth` | int or null | Yes | Set for BILLING_QUEUE_JOIN |
| `metadata.sku_zone` | string or null | Yes | From store_layout zone label |
| `metadata.session_seq` | int | Yes | Ordinal within session |

---
