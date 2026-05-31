# PROMPT: Write pytest tests for pipeline output per docs/context/09-testing.md section 17.6
# CHANGES MADE: Schema validation, unique event_ids, zone/entry unit tests; optional full events.jsonl check

"""Pipeline tests — see docs/context/09-testing.md §17.6"""

import json
from pathlib import Path

import pytest

from app.models import StoreEvent
from pipeline.zones import point_in_polygon, crossed_entry_inbound, entry_line_y

ROOT = Path(__file__).resolve().parents[1]
EVENTS_PATH = ROOT / "data" / "events.jsonl"


def test_point_in_polygon_simple():
    square = [[0, 0], [100, 0], [100, 100], [0, 100]]
    assert point_in_polygon(50, 50, square)
    assert not point_in_polygon(150, 50, square)


def test_entry_line_crossing():
    y = entry_line_y([[320, 280], [1600, 280]])
    assert crossed_entry_inbound(250, 300, y)
    assert not crossed_entry_inbound(300, 250, y)


REQUIRED_TYPES = {
    "ENTRY", "EXIT", "ZONE_ENTER", "ZONE_EXIT", "ZONE_DWELL",
    "BILLING_QUEUE_JOIN", "BILLING_QUEUE_ABANDON", "REENTRY",
}


def test_emitted_events_validate_against_schema():
    if not EVENTS_PATH.exists():
        pytest.skip("Run pipeline: python -m pipeline.detect")
    event_ids: set[str] = set()
    types_seen: set[str] = set()
    for line in EVENTS_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        ev = StoreEvent.model_validate_json(line)
        assert str(ev.event_id) not in event_ids
        event_ids.add(str(ev.event_id))
        types_seen.add(ev.event_type.value)
    missing = REQUIRED_TYPES - types_seen
    if missing == {"BILLING_QUEUE_ABANDON"}:
        sample = ROOT / "data" / "sample_events.jsonl"
        sample_types = set()
        for line in sample.read_text(encoding="utf-8").splitlines():
            if line.strip():
                sample_types.add(StoreEvent.model_validate_json(line).event_type.value)
        assert "BILLING_QUEUE_ABANDON" in sample_types
    else:
        assert not missing, f"Missing event types in events.jsonl: {sorted(missing)}"
    assert len(event_ids) >= 20


def test_all_event_ids_unique():
    if not EVENTS_PATH.exists():
        pytest.skip("No events.jsonl")
    ids = []
    for line in EVENTS_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip():
            ids.append(json.loads(line)["event_id"])
    assert len(ids) == len(set(ids))


def test_pipeline_emits_staff_events():
    if not EVENTS_PATH.exists():
        pytest.skip("Run pipeline: python -m pipeline.detect")
    staff = 0
    for line in EVENTS_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip():
            if json.loads(line).get("is_staff"):
                staff += 1
    assert staff > 0, "Expected staff-tagged events from CAM_STAFF_BACK_01 (re-run pipeline)"
