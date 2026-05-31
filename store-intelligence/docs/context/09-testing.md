# Testing Requirements

> Part of [Project Context Index](./README.md)

---

## 17. Mandatory Test Matrix

> **Coverage target:** >70% statement coverage. Every test file needs `# PROMPT:` + `# CHANGES MADE:` header (Section 10.2).

### 17.1 Ingest Tests (`test_ingest.py`)

| Test Case | Expected Behavior |
|-----------|-------------------|
| Valid batch ingest | 200/207, events persisted |
| Duplicate `event_id` | Idempotent — no duplicate rows, accepted count unchanged |
| Batch >500 events | 400 rejection |
| Malformed event (missing timestamp) | Partial success; malformed rejected with reason |
| Invalid UUID `event_id` | Rejected with structured error |
| Invalid `event_type` | Rejected |
| Empty batch | 200 with accepted=0 |
| DB unavailable | 503 structured body, no stack trace |

### 17.2 Metrics Tests (`test_metrics.py`)

| Test Case | Expected Behavior |
|-----------|-------------------|
| Empty store (no events) | `unique_visitors=0`, `conversion_rate=0.0`, no 500 |
| All staff events | `unique_visitors=0` |
| Zero purchases (no POS rows) | `conversion_rate=0.0`, `total_transactions=0` |
| Known events + 24 POS rows | Conversion rate matches hand-calculated value |
| Staff events ingested | Excluded from visitor count |

### 17.3 Funnel Tests (`test_funnel.py`)

| Test Case | Expected Behavior |
|-----------|-------------------|
| Normal funnel | Monotonic decreasing counts stage → stage |
| Re-entry session | Visitor counted once in ENTRY stage |
| Staff-only session | Excluded entirely |
| Purchase correlation | PURCHASE stage matches POS-correlated sessions |

### 17.4 Anomaly Tests (`test_anomalies.py`)

| Test Case | Expected Behavior |
|-----------|-------------------|
| High queue_depth events | `BILLING_QUEUE_SPIKE` returned |
| Low conversion vs baseline | `CONVERSION_DROP` returned |
| 30 min no zone visits | `DEAD_ZONE` returned |
| Each anomaly | Has `severity` + `suggested_action` |

### 17.5 Health Tests (`test_health.py`)

| Test Case | Expected Behavior |
|-----------|-------------------|
| Recent events | `feed_status=OK` |
| Last event >10 min ago | `feed_status=STALE_FEED`, warning present |
| DB down | HTTP 503 |

### 17.6 Pipeline Tests (`test_pipeline.py`)

| Test Case | Expected Behavior |
|-----------|-------------------|
| Emitted events validate against Pydantic schema | All fields correct types |
| All `event_id` unique | No duplicates |
| ENTRY assigns new `visitor_id` | Distinct per session |
| Low confidence events | Present in output, not filtered |
| Timestamps monotonic per visitor | No time travel |

### 17.7 Example Assertions (substitute for missing `assertions.py`)

Implement these as pytest tests — they mirror the challenge's example assertion file:

```python
def test_metrics_returns_valid_json(client):
    r = client.get("/stores/ST1008/metrics")
    assert r.status_code == 200
    assert "conversion_rate" in r.json()

def test_funnel_has_four_stages(client):
    stages = [s["stage"] for s in client.get("/stores/ST1008/funnel").json()["stages"]]
    assert stages == ["ENTRY", "ZONE_VISIT", "BILLING_QUEUE", "PURCHASE"]

def test_ingest_idempotent(client, sample_events):
    payload = {"events": sample_events[:10]}
    r1 = client.post("/events/ingest", json=payload)
    r2 = client.post("/events/ingest", json=payload)
    assert r1.json()["accepted"] == r2.json()["accepted"]

def test_health_stale_feed_flag(client, stale_store):
    assert any(s["feed_status"] == "STALE_FEED" for s in client.get("/health").json()["stores"])

def test_heatmap_low_confidence_flag(client, few_sessions):
    assert client.get("/stores/ST1008/heatmap").json()["data_confidence"] == "LOW"
```

---
