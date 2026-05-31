# API Contracts

> Part of [Project Context Index](./README.md)

---

## 12. API Contracts — Complete Reference

Base URL: `http://localhost:8000` (configurable via env).

All responses: `Content-Type: application/json`. All errors: structured JSON body, **no raw stack traces**.

### 12.1 `POST /events/ingest`

**Purpose:** Accept detection pipeline events; validate, deduplicate, persist.

**Request body:**

```json
{
  "events": [
    { "event_id": "uuid-v4", "store_id": "ST1008", "camera_id": "CAM_ENTRY_01", "visitor_id": "VIS_c8a2f1", "event_type": "ENTRY", "timestamp": "2026-04-10T12:15:00Z", "zone_id": null, "dwell_ms": 0, "is_staff": false, "confidence": 0.91, "metadata": { "queue_depth": null, "sku_zone": null, "session_seq": 1 } }
  ]
}
```

| Rule | Detail |
|------|--------|
| Max batch size | 500 events |
| Idempotency | Same `event_id` → no duplicate insert; return success for duplicate |
| Partial success | Malformed events skipped; valid ones persisted |
| HTTP on partial | `207` or `200` with `accepted`/`rejected` counts — document choice in CHOICES.md |
| HTTP on total failure | `400` with structured errors |
| HTTP on DB down | `503` — see Section 9 |

**Response (success example):**

```json
{
  "accepted": 498,
  "rejected": 2,
  "errors": [
    { "index": 12, "event_id": null, "reason": "missing field: timestamp" },
    { "index": 45, "event_id": "bad-uuid", "reason": "invalid UUID format" }
  ]
}
```

---

### 12.2 `GET /stores/{store_id}/metrics`

**Response schema:**

```json
{
  "store_id": "ST1008",
  "date": "2026-04-10",
  "unique_visitors": 42,
  "converted_visitors": 18,
  "conversion_rate": 0.4286,
  "total_transactions": 24,
  "avg_basket_value_inr": 1430.49,
  "queue_depth_current": 2,
  "abandonment_rate": 0.15,
  "avg_dwell_by_zone_ms": { "MAKEUP": 45000, "SKIN": 62000, "BILLING": 120000 },
  "computed_at": "2026-04-10T19:45:00Z"
}
```

| Field | Computation |
|-------|-------------|
| `unique_visitors` | Distinct `visitor_id` with ENTRY today, `is_staff=false` |
| `converted_visitors` | Sessions with billing-zone presence within 5 min before POS transaction |
| `conversion_rate` | `converted_visitors / unique_visitors` — return `0.0` if denominator is 0 |
| `total_transactions` | Count from `pos_transactions.csv` for store + date |
| `abandonment_rate` | `BILLING_QUEUE_ABANDON` sessions / billing-zone sessions |

**Edge cases:** zero visitors, zero purchases, all-staff clip → no crash, no null rates.

**Acceptance gate note:** Problem statement example uses `STORE_BLR_002` — support `ST1008` and optionally alias both to same store.

---

### 12.3 `GET /stores/{store_id}/funnel`

**Stages:** `ENTRY` → `ZONE_VISIT` → `BILLING_QUEUE` → `PURCHASE`

```json
{
  "store_id": "ST1008",
  "date": "2026-04-10",
  "stages": [
    { "stage": "ENTRY", "count": 42, "drop_off_pct": 0.0 },
    { "stage": "ZONE_VISIT", "count": 38, "drop_off_pct": 9.5 },
    { "stage": "BILLING_QUEUE", "count": 28, "drop_off_pct": 26.3 },
    { "stage": "PURCHASE", "count": 18, "drop_off_pct": 35.7 }
  ],
  "total_sessions": 42,
  "computed_at": "2026-04-10T19:45:00Z"
}
```

Session-based; exclude staff; REENTRY must not double-count visitor in ENTRY stage.

---

### 12.4 `GET /stores/{store_id}/heatmap`

```json
{
  "store_id": "ST1008",
  "date": "2026-04-10",
  "data_confidence": "HIGH",
  "zones": [
    { "zone_id": "MAKEUP", "visit_count": 35, "avg_dwell_ms": 45000, "visit_score": 83, "dwell_score": 72, "combined_score": 78 }
  ],
  "computed_at": "2026-04-10T19:45:00Z"
}
```

`data_confidence`: `"LOW"` if fewer than 20 sessions; else `"HIGH"`. Scores normalized 0–100.

---

### 12.5 `GET /stores/{store_id}/anomalies`

| Type | Trigger | Severity |
|------|---------|----------|
| `BILLING_QUEUE_SPIKE` | queue_depth > threshold sustained >2 min | WARN/CRITICAL |
| `CONVERSION_DROP` | Today conversion >X% below 7-day avg | WARN/CRITICAL |
| `DEAD_ZONE` | No ZONE_ENTER in zone for 30 min | INFO/WARN |

Each anomaly must include `suggested_action` string.

**Full response example:**

```json
{
  "store_id": "ST1008",
  "anomalies": [
    {
      "type": "BILLING_QUEUE_SPIKE",
      "severity": "WARN",
      "detected_at": "2026-04-10T19:10:00Z",
      "detail": "Queue depth reached 4 at billing counter",
      "suggested_action": "Open additional billing counter or deploy floor staff to assist queue"
    },
    {
      "type": "CONVERSION_DROP",
      "severity": "CRITICAL",
      "detected_at": "2026-04-10T18:00:00Z",
      "detail": "Conversion rate 12% vs 7-day avg 28%",
      "suggested_action": "Review staffing at billing; check for stock-outs in top dwell zones"
    },
    {
      "type": "DEAD_ZONE",
      "severity": "INFO",
      "detected_at": "2026-04-10T14:30:00Z",
      "detail": "Zone HAIR had no visits for 30 minutes",
      "suggested_action": "Verify camera coverage; consider repositioning displays"
    }
  ],
  "computed_at": "2026-04-10T19:45:00Z"
}
```

**7-day baseline note:** With 1 day of local data, store daily snapshots as history or document synthetic seed in CHOICES.md — logic must be real computation.

---

### 12.6 `GET /health`

```json
{
  "status": "OK",
  "version": "1.0.0",
  "stores": [{ "store_id": "ST1008", "last_event_at": "2026-04-10T19:54:02Z", "lag_seconds": 120, "feed_status": "OK" }],
  "warnings": [],
  "computed_at": "2026-04-10T19:56:02Z"
}
```

`feed_status = "STALE_FEED"` if last event > 10 minutes ago. DB down → HTTP 503.

---

## Appendix C: Structured Log Format

Every API request must emit one log line (JSON):

```json
{
  "trace_id": "uuid",
  "store_id": "ST1008",
  "endpoint": "/stores/ST1008/metrics",
  "latency_ms": 45,
  "event_count": null,
  "status_code": 200,
  "timestamp": "2026-04-10T19:45:00Z"
}
```

For ingest: `event_count` = number of events in request body.

---
