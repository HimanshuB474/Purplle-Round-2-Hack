"""Shared pytest fixtures for API tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.config as config
import app.db as db_module
from app.main import app
from app.pos import load_pos_transactions

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_EVENTS_PATH = ROOT / "data" / "sample_events.jsonl"
REFERENCE_DATE = "2026-04-10"


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    db_url = f"sqlite:///{db_path}"
    monkeypatch.setenv("DATABASE_URL", db_url)
    config.DATABASE_URL = db_url
    db_module._engine = None
    db_module._SessionLocal = None
    db_module.init_db()
    load_pos_transactions.cache_clear()

    with TestClient(app) as test_client:
        yield test_client

    db_module._engine = None
    db_module._SessionLocal = None


@pytest.fixture()
def sample_events():
    events = []
    for line in SAMPLE_EVENTS_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip():
            events.append(json.loads(line))
    return events


@pytest.fixture()
def ingest_sample(client, sample_events):
    response = client.post("/events/ingest", json={"events": sample_events})
    assert response.status_code == 200
    return response.json()
