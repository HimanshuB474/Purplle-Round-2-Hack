# PROMPT: Implement funnel tests per docs/context/09-testing.md section 17.3
# CHANGES MADE: Added four-stage shape, monotonic counts, re-entry dedup, and staff exclusion tests

"""Funnel tests — see docs/context/09-testing.md §17.3"""

REFERENCE_DATE = "2026-04-10"


def test_funnel_has_four_stages(client, ingest_sample):
    stages = client.get(f"/stores/ST1008/funnel?date={REFERENCE_DATE}").json()["stages"]
    assert [s["stage"] for s in stages] == ["ENTRY", "ZONE_VISIT", "BILLING_QUEUE", "PURCHASE"]


def test_funnel_monotonic_counts(client, ingest_sample):
    counts = [s["count"] for s in client.get(f"/stores/ST1008/funnel?date={REFERENCE_DATE}").json()["stages"]]
    assert counts[0] >= counts[1] >= counts[2] >= counts[3]


def test_reentry_not_double_counted_in_entry(client):
    events = [
        {
            "event_id": "b1000001-0001-4000-8000-000000000001",
            "store_id": "ST1008",
            "camera_id": "CAM_ENTRY_01",
            "visitor_id": "VIS_re",
            "event_type": "ENTRY",
            "timestamp": "2026-04-10T20:10:00Z",
            "zone_id": None,
            "dwell_ms": 0,
            "is_staff": False,
            "confidence": 0.9,
            "metadata": {"queue_depth": None, "sku_zone": None, "session_seq": 1},
        },
        {
            "event_id": "b1000001-0001-4000-8000-000000000002",
            "store_id": "ST1008",
            "camera_id": "CAM_ENTRY_01",
            "visitor_id": "VIS_re",
            "event_type": "EXIT",
            "timestamp": "2026-04-10T20:11:00Z",
            "zone_id": None,
            "dwell_ms": 0,
            "is_staff": False,
            "confidence": 0.9,
            "metadata": {"queue_depth": None, "sku_zone": None, "session_seq": 2},
        },
        {
            "event_id": "b1000001-0001-4000-8000-000000000003",
            "store_id": "ST1008",
            "camera_id": "CAM_ENTRY_01",
            "visitor_id": "VIS_re",
            "event_type": "REENTRY",
            "timestamp": "2026-04-10T20:12:00Z",
            "zone_id": None,
            "dwell_ms": 0,
            "is_staff": False,
            "confidence": 0.9,
            "metadata": {"queue_depth": None, "sku_zone": None, "session_seq": 3},
        },
    ]
    client.post("/events/ingest", json={"events": events})
    entry_count = client.get(f"/stores/ST1008/funnel?date={REFERENCE_DATE}").json()["stages"][0]["count"]
    assert entry_count == 1


def test_staff_only_session_excluded(client):
    events = [
        {
            "event_id": "c1000001-0001-4000-8000-000000000001",
            "store_id": "ST1008",
            "camera_id": "CAM_ENTRY_01",
            "visitor_id": "VIS_staff",
            "event_type": "ENTRY",
            "timestamp": "2026-04-10T20:10:00Z",
            "zone_id": None,
            "dwell_ms": 0,
            "is_staff": True,
            "confidence": 0.95,
            "metadata": {"queue_depth": None, "sku_zone": None, "session_seq": 1},
        }
    ]
    client.post("/events/ingest", json={"events": events})
    body = client.get(f"/stores/ST1008/funnel?date={REFERENCE_DATE}").json()
    assert body["total_sessions"] == 0
