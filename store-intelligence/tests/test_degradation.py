# PROMPT: Add graceful degradation tests per docs/context/09-testing.md section 17
# CHANGES MADE: HTTP 503 on DB unavailable for health, ingest, and metrics routes

"""503 graceful degradation when database is unavailable."""

REFERENCE_DATE = "2026-04-10"


def _patch_db_down(monkeypatch):
    monkeypatch.setattr("app.db.is_db_available", lambda: False)
    monkeypatch.setattr("app.health.is_db_available", lambda: False)
    monkeypatch.setattr("app.deps.is_db_available", lambda: False)


def test_health_returns_503_when_db_unavailable(client, monkeypatch):
    _patch_db_down(monkeypatch)
    response = client.get("/health")
    assert response.status_code == 503
    body = response.json()
    assert body["detail"]["status"] == "UNAVAILABLE"
    assert "reason" in body["detail"]


def test_ingest_returns_503_when_db_unavailable(client, monkeypatch, sample_events):
    _patch_db_down(monkeypatch)
    response = client.post("/events/ingest", json={"events": sample_events[:2]})
    assert response.status_code == 503
    assert response.json()["detail"]["status"] == "UNAVAILABLE"


def test_metrics_returns_503_when_db_unavailable(client, monkeypatch):
    _patch_db_down(monkeypatch)
    response = client.get(f"/stores/ST1008/metrics?date={REFERENCE_DATE}")
    assert response.status_code == 503
    assert response.json()["detail"]["status"] == "UNAVAILABLE"


def test_funnel_returns_503_when_db_unavailable(client, monkeypatch):
    _patch_db_down(monkeypatch)
    response = client.get(f"/stores/ST1008/funnel?date={REFERENCE_DATE}")
    assert response.status_code == 503


def test_no_stack_trace_in_503_body(client, monkeypatch):
    _patch_db_down(monkeypatch)
    body = client.get("/health").text
    assert "Traceback" not in body
    assert "File \"" not in body
