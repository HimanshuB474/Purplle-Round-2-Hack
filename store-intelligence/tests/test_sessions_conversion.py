# PROMPT: Test one POS transaction maps to at most one converted visitor
# CHANGES MADE: apply_pos_conversions greedy assignment by closest billing time

"""POS conversion assignment tests."""

from datetime import datetime

from app.db import EventRow
from app.pos import PosTransaction
from app.sessions import apply_pos_conversions, build_sessions


def _billing_event(visitor_id: str, ts: str) -> EventRow:
    return EventRow(
        event_id=f"{visitor_id}-b",
        store_id="ST1008",
        camera_id="CAM_BILLING_01",
        visitor_id=visitor_id,
        event_type="BILLING_QUEUE_JOIN",
        timestamp=datetime.fromisoformat(ts),
        zone_id="BILLING",
        dwell_ms=0,
        is_staff=False,
        confidence=0.9,
        metadata_json='{"queue_depth": 2, "session_seq": 1}',
    )


def test_one_transaction_one_converted_visitor():
    events = [
        _billing_event("VIS_0001", "2026-04-10 19:53:00"),
        _billing_event("VIS_0002", "2026-04-10 19:53:30"),
    ]
    sessions = build_sessions(events)
    for s in sessions:
        s.reached_billing = True

    txn = PosTransaction(
        store_id="ST1008",
        transaction_id="T1",
        timestamp=datetime.fromisoformat("2026-04-10 19:54:00"),
        basket_value_inr=500.0,
    )
    apply_pos_conversions(sessions, [txn])

    converted = [s for s in sessions if s.converted]
    assert len(converted) == 1
    assert converted[0].visitor_id == "VIS_0002"
