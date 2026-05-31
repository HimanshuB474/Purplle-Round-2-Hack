# PROMPT: Add tests for Part E live dashboard routes
# CHANGES MADE: HTML page, snapshot JSON, replay start/stop/status endpoints

"""Dashboard tests — Part E bonus."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "dash.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("POS_CSV_PATH", str(ROOT / "data" / "pos_transactions.csv"))
    from app.db import init_db

    init_db()
    return TestClient(app)


def test_dashboard_page(client):
    r = client.get("/dashboard")
    assert r.status_code == 200
    assert "Store Intelligence" in r.text
    assert "Live replay" in r.text


def test_dashboard_snapshot(client):
    r = client.get("/dashboard/api/snapshot?store_id=ST1008&date=2026-04-10")
    assert r.status_code == 200
    body = r.json()
    assert "metrics" in body
    assert "funnel" in body
    assert "replay" in body
    assert body["metrics"]["store_id"] == "ST1008"


def test_replay_streams_events(client, monkeypatch):
    monkeypatch.setattr(
        "app.dashboard_replay.DEFAULT_EVENTS_PATH",
        ROOT / "data" / "sample_events.jsonl",
    )
    r = client.post(
        "/dashboard/api/replay/start?store_id=ST1008&target_date=2026-04-10"
        "&reset=true&batch_size=8&interval_ms=100",
    )
    assert r.status_code == 200, r.text
    assert r.json()["running"] is True

    import time

    time.sleep(0.5)
    client.post("/dashboard/api/replay/stop")

    snap = client.get("/dashboard/api/snapshot?store_id=ST1008&date=2026-04-10").json()
    assert snap["ingested_events"] > 0
    assert snap["metrics"]["unique_visitors"] >= 0
