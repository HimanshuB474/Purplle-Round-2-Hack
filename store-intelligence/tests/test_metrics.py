# PROMPT: Implement metrics tests per docs/context/09-testing.md section 17.2
# CHANGES MADE: Added empty store, all-staff, alias store ID, and ingested sample event checks

"""Metrics tests — see docs/context/09-testing.md §17.2"""

REFERENCE_DATE = "2026-04-10"


def test_metrics_returns_valid_json(client):
    response = client.get(f"/stores/ST1008/metrics?date={REFERENCE_DATE}")
    assert response.status_code == 200
    body = response.json()
    assert "conversion_rate" in body
    assert body["unique_visitors"] == 0
    assert body["conversion_rate"] == 0.0


def test_empty_store_no_crash(client):
    body = client.get(f"/stores/ST1008/metrics?date={REFERENCE_DATE}").json()
    assert body["unique_visitors"] == 0
    assert body["conversion_rate"] == 0.0
    assert body["total_transactions"] == 24
    assert body["abandonment_rate"] == 0.0


def test_all_staff_events(client, sample_events):
    staff_events = []
    for event in sample_events:
        copy = event.copy()
        copy["is_staff"] = True
        staff_events.append(copy)
    client.post("/events/ingest", json={"events": staff_events})
    body = client.get(f"/stores/ST1008/metrics?date={REFERENCE_DATE}").json()
    assert body["unique_visitors"] == 0


def test_metrics_after_sample_ingest(client, ingest_sample):
    body = client.get(f"/stores/ST1008/metrics?date={REFERENCE_DATE}").json()
    assert body["unique_visitors"] > 0
    assert body["total_transactions"] == 24
    assert body["avg_basket_value_inr"] > 0
    assert isinstance(body["avg_dwell_by_zone_ms"], dict)


def test_store_alias_metrics(client, ingest_sample):
    response = client.get(f"/stores/STORE_BLR_002/metrics?date={REFERENCE_DATE}")
    assert response.status_code == 200
    assert response.json()["store_id"] == "STORE_BLR_002"


def test_unknown_store_404(client):
    assert client.get("/stores/UNKNOWN/metrics").status_code == 404
