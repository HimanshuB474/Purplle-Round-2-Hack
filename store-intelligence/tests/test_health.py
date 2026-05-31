# PROMPT: Extend health tests per docs/context/09-testing.md section 17.5
# CHANGES MADE: Added version field, store list, and stale feed detection test

"""Health endpoint tests — see docs/context/09-testing.md"""

REFERENCE_DATE = "2026-04-10"


def test_health_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "OK"
    assert body["version"] == "1.0.0"
    assert len(body["stores"]) == 2


def test_health_recent_events_ok(client):
    from datetime import datetime, timezone
    from uuid import uuid4

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    client.post(
        "/events/ingest",
        json={
            "events": [
                {
                    "event_id": str(uuid4()),
                    "store_id": "ST1008",
                    "camera_id": "CAM_ENTRY_01",
                    "visitor_id": "VIS_live",
                    "event_type": "ENTRY",
                    "timestamp": now,
                    "zone_id": None,
                    "dwell_ms": 0,
                    "is_staff": False,
                    "confidence": 0.9,
                    "metadata": {"queue_depth": None, "sku_zone": None, "session_seq": 1},
                }
            ]
        },
    )
    stores = client.get("/health").json()["stores"]
    st1008 = next(s for s in stores if s["store_id"] == "ST1008")
    assert st1008["feed_status"] == "OK"
    assert st1008["last_event_at"] is not None


def test_health_stale_feed_when_last_event_old(client):
    from uuid import uuid4

    client.post(
        "/events/ingest",
        json={
            "events": [
                {
                    "event_id": str(uuid4()),
                    "store_id": "ST1008",
                    "camera_id": "CAM_ENTRY_01",
                    "visitor_id": "VIS_stale",
                    "event_type": "ENTRY",
                    "timestamp": "2026-04-10T10:00:00Z",
                    "zone_id": None,
                    "dwell_ms": 0,
                    "is_staff": False,
                    "confidence": 0.9,
                    "metadata": {"queue_depth": None, "sku_zone": None, "session_seq": 1},
                }
            ]
        },
    )
    stores = client.get("/health").json()["stores"]
    st1008 = next(s for s in stores if s["store_id"] == "ST1008")
    assert st1008["feed_status"] == "STALE_FEED"
    assert any("ST1008" in w for w in client.get("/health").json().get("warnings", []))
