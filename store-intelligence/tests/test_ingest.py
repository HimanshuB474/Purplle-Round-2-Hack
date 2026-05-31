# PROMPT: Implement ingest tests per docs/context/09-testing.md section 17.1
# CHANGES MADE: Added idempotency, batch limit, partial success, empty batch, and malformed event tests

"""Ingest tests — see docs/context/09-testing.md §17.1"""

import json
from pathlib import Path
from uuid import uuid4

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load_sample(n: int = 5):
    events = []
    for line in (ROOT / "data" / "sample_events.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            events.append(json.loads(line))
    return events[:n]


def test_valid_batch_ingest(client):
    payload = {"events": _load_sample(10)}
    response = client.post("/events/ingest", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["accepted"] == 10
    assert body["rejected"] == 0


def test_duplicate_event_id_is_idempotent(client):
    payload = {"events": _load_sample(5)}
    first = client.post("/events/ingest", json=payload).json()
    second = client.post("/events/ingest", json=payload).json()
    assert first["accepted"] == second["accepted"] == 5


def test_batch_over_500_rejected(client):
    event = _load_sample(1)[0]
    payload = {"events": [event] * 501}
    response = client.post("/events/ingest", json=payload)
    assert response.status_code == 400


def test_malformed_event_partial_success(client):
    events = _load_sample(2)
    events.append({"event_id": str(uuid4()), "visitor_id": "VIS_bad"})
    response = client.post("/events/ingest", json={"events": events})
    body = response.json()
    assert response.status_code == 200
    assert body["accepted"] == 2
    assert body["rejected"] == 1
    assert body["errors"]


def test_invalid_uuid_rejected(client):
    events = _load_sample(1)
    events.append(
        {
            "event_id": "bad-uuid",
            "store_id": "ST1008",
            "camera_id": "CAM_ENTRY_01",
            "visitor_id": "VIS_x",
            "event_type": "ENTRY",
            "timestamp": "2026-04-10T20:10:00Z",
            "zone_id": None,
            "dwell_ms": 0,
            "is_staff": False,
            "confidence": 0.9,
            "metadata": {"queue_depth": None, "sku_zone": None, "session_seq": 1},
        }
    )
    body = client.post("/events/ingest", json={"events": events}).json()
    assert body["rejected"] == 1


def test_invalid_event_type_rejected(client):
    bad = _load_sample(1)[0].copy()
    bad["event_id"] = str(uuid4())
    bad["event_type"] = "NOT_A_REAL_EVENT"
    body = client.post("/events/ingest", json={"events": [bad]}).json()
    assert body["rejected"] == 1


def test_empty_batch(client):
    body = client.post("/events/ingest", json={"events": []}).json()
    assert body["accepted"] == 0
    assert body["rejected"] == 0


def test_ingest_logs_event_count(client, caplog):
    import logging

    caplog.set_level(logging.INFO, logger="store_intelligence.api")
    events = _load_sample(4)
    client.post("/events/ingest", json={"events": events})
    assert any('"event_count": 4' in record.message for record in caplog.records)
