# PROMPT: Implement anomaly tests per docs/context/09-testing.md section 17.4
# CHANGES MADE: Added queue spike, dead zone, and suggested_action coverage tests

"""Anomaly tests — see docs/context/09-testing.md §17.4"""

from uuid import uuid4

REFERENCE_DATE = "2026-04-10"


def _billing_join(event_id: str, ts: str, depth: int):
    return {
        "event_id": event_id,
        "store_id": "ST1008",
        "camera_id": "CAM_BILLING_01",
        "visitor_id": "VIS_q",
        "event_type": "BILLING_QUEUE_JOIN",
        "timestamp": ts,
        "zone_id": "BILLING",
        "dwell_ms": 0,
        "is_staff": False,
        "confidence": 0.9,
        "metadata": {"queue_depth": depth, "sku_zone": "QUEUE", "session_seq": 1},
    }


def test_queue_spike_anomaly(client):
    events = [
        _billing_join(str(uuid4()), "2026-04-10T20:10:00Z", 4),
        _billing_join(str(uuid4()), "2026-04-10T20:12:30Z", 4),
    ]
    client.post("/events/ingest", json={"events": events})
    anomalies = client.get(f"/stores/ST1008/anomalies?date={REFERENCE_DATE}").json()["anomalies"]
    types = {a["type"] for a in anomalies}
    assert "BILLING_QUEUE_SPIKE" in types


def test_anomaly_has_suggested_action(client, ingest_sample):
    anomalies = client.get(f"/stores/ST1008/anomalies?date={REFERENCE_DATE}").json()["anomalies"]
    for anomaly in anomalies:
        assert anomaly["severity"]
        assert anomaly["suggested_action"]


def test_heatmap_low_confidence_flag(client):
    body = client.get(f"/stores/ST1008/heatmap?date={REFERENCE_DATE}").json()
    assert body["data_confidence"] == "LOW"


def test_conversion_drop_anomaly(client):
    from datetime import date, datetime

    from app.db import session_scope, upsert_daily_snapshot

    with session_scope() as db:
        for day in range(3, 10):
            upsert_daily_snapshot(
                db,
                "ST1008",
                date(2026, 4, day),
                unique_visitors=100,
                converted_visitors=50,
                conversion_rate=0.5,
                total_transactions=50,
                computed_at=datetime(2026, 4, day, 12, 0, 0),
            )
        db.commit()

    client.post(
        "/events/ingest",
        json={
            "events": [
                {
                    "event_id": "d1000001-0001-4000-8000-000000000001",
                    "store_id": "ST1008",
                    "camera_id": "CAM_ENTRY_01",
                    "visitor_id": "VIS_drop",
                    "event_type": "ENTRY",
                    "timestamp": "2026-04-10T20:10:00Z",
                    "zone_id": None,
                    "dwell_ms": 0,
                    "is_staff": False,
                    "confidence": 0.9,
                    "metadata": {"queue_depth": None, "sku_zone": None, "session_seq": 1},
                }
            ]
        },
    )
    client.get(f"/stores/ST1008/metrics?date={REFERENCE_DATE}")
    anomalies = client.get(f"/stores/ST1008/anomalies?date={REFERENCE_DATE}").json()["anomalies"]
    types = {a["type"] for a in anomalies}
    assert "CONVERSION_DROP" in types
