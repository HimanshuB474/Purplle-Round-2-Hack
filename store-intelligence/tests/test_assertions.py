# PROMPT: Port challenge assertions.py examples into pytest per docs/context/09-testing.md §17.7
# CHANGES MADE: Implemented five example assertions using conftest client + sample_events

"""Challenge example assertions — mirrors official assertions.py spec."""

import json

REFERENCE_DATE = "2026-04-10"


def test_metrics_returns_valid_json(client, ingest_sample):
    r = client.get(f"/stores/ST1008/metrics?date={REFERENCE_DATE}")
    assert r.status_code == 200
    assert "conversion_rate" in r.json()


def test_funnel_has_four_stages(client, ingest_sample):
    stages = [
        s["stage"]
        for s in client.get(f"/stores/ST1008/funnel?date={REFERENCE_DATE}").json()["stages"]
    ]
    assert stages == ["ENTRY", "ZONE_VISIT", "BILLING_QUEUE", "PURCHASE"]


def test_ingest_idempotent(client, sample_events):
    payload = {"events": sample_events[:10]}
    r1 = client.post("/events/ingest", json=payload)
    r2 = client.post("/events/ingest", json=payload)
    assert r1.json()["accepted"] == r2.json()["accepted"]


def test_heatmap_has_zones(client, ingest_sample):
    body = client.get(f"/stores/ST1008/heatmap?date={REFERENCE_DATE}").json()
    assert body["data_confidence"] in ("LOW", "HIGH")
    assert isinstance(body["zones"], list)


def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "OK"
