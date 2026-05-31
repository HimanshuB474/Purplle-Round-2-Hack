"""Post-process pipeline events — drop false BILLING_QUEUE_ABANDON when POS follows."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from app.pos import conversion_window_start, get_transactions_for_store_date


def _parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)


def _visitor_has_pos_conversion(
    billing_times: list[datetime],
    transactions: list,
) -> bool:
    """True when billing activity falls in the 5-min window before a POS txn."""
    for billing_ts in billing_times:
        for txn in transactions:
            window_start = conversion_window_start(txn.timestamp)
            if window_start <= billing_ts <= txn.timestamp:
                return True
    return False


def filter_false_billing_abandons(
    events: list[dict[str, Any]],
    store_id: str,
    target_date: date,
) -> list[dict[str, Any]]:
    transactions = get_transactions_for_store_date("ST1008", target_date)

    billing_by_visitor: dict[str, list[datetime]] = {}
    for event in events:
        if event.get("is_staff"):
            continue
        if event.get("event_type") not in ("BILLING_QUEUE_JOIN", "ZONE_ENTER"):
            continue
        if event.get("zone_id") != "BILLING":
            continue
        billing_by_visitor.setdefault(event["visitor_id"], []).append(_parse_ts(event["timestamp"]))

    kept: list[dict[str, Any]] = []
    dropped = 0
    for event in events:
        if event.get("event_type") != "BILLING_QUEUE_ABANDON":
            kept.append(event)
            continue
        billing_times = billing_by_visitor.get(event["visitor_id"], [])
        if billing_times and _visitor_has_pos_conversion(billing_times, transactions):
            dropped += 1
            continue
        kept.append(event)
    if dropped:
        print(f"  POS filter: removed {dropped} false BILLING_QUEUE_ABANDON event(s)")
    return kept
