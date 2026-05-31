"""Post-process pipeline events — optional BILLING_QUEUE_ABANDON cleanup."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from app.pos import conversion_window_start, get_transactions_for_store_date


def _parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)


def _abandon_is_false_positive(
    abandon_ts: datetime,
    billing_times: list[datetime],
    transactions: list,
) -> bool:
    """
    Drop abandon only when conversion is strongly indicated:
    - POS txn within 5 min *after* abandon (paid after leaving queue), or
    - billing in [T-5m, T] window before a txn that occurred *before* abandon.
    """
    for txn in transactions:
        txn_ts = txn.timestamp
        if billing_times and abandon_ts <= txn_ts <= abandon_ts + timedelta(minutes=5):
            if any(bt <= abandon_ts for bt in billing_times):
                return True
        for billing_ts in billing_times:
            window_start = conversion_window_start(txn_ts)
            if window_start <= billing_ts <= txn_ts < abandon_ts:
                return True
    return False


def filter_false_billing_abandons(
    events: list[dict[str, Any]],
    store_id: str,
    target_date: date,
    *,
    enabled: bool = True,
) -> list[dict[str, Any]]:
    if not enabled:
        return events

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
        if billing_times and _abandon_is_false_positive(_parse_ts(event["timestamp"]), billing_times, transactions):
            dropped += 1
            continue
        kept.append(event)
    if dropped:
        print(f"  POS filter: removed {dropped} false BILLING_QUEUE_ABANDON event(s)")
    return kept
