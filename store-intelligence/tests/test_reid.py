# PROMPT: Unit tests for cross-camera visitor merge
# CHANGES MADE: post-pass time linking and POS abandon filter modes

"""Re-ID and abandon filter unit tests."""

import json
from datetime import date

from pipeline.pos_filter import filter_false_billing_abandons
from pipeline.reid import merge_visitor_ids_post, pick_unambiguous_match


def test_pick_unambiguous_match_single_candidate():
    assert pick_unambiguous_match([("VIS_0001", 0.9)], min_gap=0.08) == "VIS_0001"


def test_pick_unambiguous_match_rejects_ambiguous():
    candidates = [("VIS_0001", 0.72), ("VIS_0002", 0.68)]
    assert pick_unambiguous_match(candidates, min_gap=0.08) is None
    assert pick_unambiguous_match(candidates, min_gap=0.02) == "VIS_0001"


def test_merge_floor_visitor_to_entry():
    events = [
        {
            "visitor_id": "VIS_0001",
            "camera_id": "CAM_ENTRY_01",
            "event_type": "ENTRY",
            "timestamp": "2026-04-10T19:52:10Z",
            "is_staff": False,
        },
        {
            "visitor_id": "VIS_0002",
            "camera_id": "CAM_FLOOR_SKIN_01",
            "event_type": "ZONE_ENTER",
            "timestamp": "2026-04-10T19:52:40Z",
            "is_staff": False,
        },
    ]
    merged = merge_visitor_ids_post(events)
    floor_ids = {e["visitor_id"] for e in merged if "FLOOR" in e["camera_id"]}
    assert floor_ids == {"VIS_0001"}


def test_pos_filter_disabled_keeps_abandon():
    events = [
        {
            "event_id": "a1",
            "event_type": "BILLING_QUEUE_ABANDON",
            "visitor_id": "VIS_0001",
            "is_staff": False,
            "zone_id": "BILLING",
            "timestamp": "2026-04-10T19:55:00Z",
        }
    ]
    out = filter_false_billing_abandons(events, "STORE_BLR_002", date(2026, 4, 10), enabled=False)
    assert len(out) == 1
    assert out[0]["event_type"] == "BILLING_QUEUE_ABANDON"
