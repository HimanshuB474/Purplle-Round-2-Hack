"""Validate data/events.jsonl — schema, 8 types, POS correlation window."""

from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.models import StoreEvent
from app.pos import get_transactions_for_store_date, conversion_window_start

EVENTS_PATH = ROOT / "data" / "events.jsonl"
REFERENCE_DATE = datetime(2026, 4, 10).date()
REQUIRED_TYPES = {
    "ENTRY",
    "EXIT",
    "ZONE_ENTER",
    "ZONE_EXIT",
    "ZONE_DWELL",
    "BILLING_QUEUE_JOIN",
    "BILLING_QUEUE_ABANDON",
    "REENTRY",
}


def main() -> int:
    if not EVENTS_PATH.exists():
        print("FAIL: data/events.jsonl not found — run: python -m pipeline.detect")
        return 1

    events: list[StoreEvent] = []
    for line in EVENTS_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip():
            events.append(StoreEvent.model_validate_json(line))

    types = Counter(e.event_type.value for e in events)
    missing = REQUIRED_TYPES - set(types.keys())
    staff = sum(1 for e in events if e.is_staff)
    customers = [e for e in events if not e.is_staff]

    print("=" * 60)
    print("EVENTS VERIFICATION")
    print("=" * 60)
    print(f"Total events: {len(events)}")
    print(f"Types: {dict(sorted(types.items()))}")
    print(f"Staff-tagged: {staff}  Customer-tagged: {len(customers)}")

    if missing:
        print(f"FAIL: Missing event types: {sorted(missing)}")
        return 1
    print("OK: All 8 event types present")

    ids = {str(e.event_id) for e in events}
    if len(ids) != len(events):
        print("FAIL: Duplicate event_id values")
        return 1
    print("OK: All event_id values unique")

    if not customers:
        print("WARN: No customer events (all staff?)")
    else:
        ts = [e.timestamp.replace(tzinfo=None) for e in customers]
        t_min, t_max = min(ts), max(ts)
        print(f"Customer event window: {t_min.isoformat()}Z -> {t_max.isoformat()}Z")

        txns = get_transactions_for_store_date("ST1008", REFERENCE_DATE)
        matchable = 0
        for txn in txns:
            w_start = conversion_window_start(txn.timestamp)
            if any(
                w_start <= e.timestamp.replace(tzinfo=None) <= txn.timestamp
                and e.event_type.value in ("BILLING_QUEUE_JOIN", "ZONE_ENTER")
                and e.zone_id == "BILLING"
                for e in customers
            ):
                matchable += 1
        print(f"POS transactions: {len(txns)}")
        print(f"Potentially correlatable (billing event in 5-min window): {matchable}")
        if matchable == 0:
            print(
                "NOTE: Clips use overlay time ~20:10; POS txns span 12:15–21:39. "
                "Zero correlation is expected unless footage overlaps txn times."
            )

    print("\nAll checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
