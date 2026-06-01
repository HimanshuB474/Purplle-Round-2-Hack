"""Load data/events.jsonl into the API database (replaces events for that store/date)."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DEFAULT_PATH = ROOT / "data" / "events.jsonl"
API = "http://127.0.0.1:8000/events/ingest"


def _target_date(events: list[dict]) -> date:
    ts = events[0]["timestamp"]
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).date()


def _ingest_via_db(events: list[dict], *, replace: bool) -> dict:
    from app.db import delete_events_for_store_date, init_db, session_scope
    from app.ingestion import ingest_raw_events
    from app.stores import canonical_store_id, normalize_event_store_id

    init_db()
    store_raw = events[0].get("store_id", "ST1008")
    canonical = canonical_store_id(normalize_event_store_id(store_raw))
    target = _target_date(events)

    with session_scope() as db:
        if replace:
            removed = delete_events_for_store_date(db, canonical, target)
            if removed:
                print(f"Cleared {removed} existing event(s) for {canonical} on {target}")
        result = ingest_raw_events(db, events)
    return result.model_dump()


def _ingest_via_http(events: list[dict]) -> dict:
    body = json.dumps({"events": events}).encode()
    req = urllib.request.Request(
        API,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest events.jsonl into store DB")
    parser.add_argument("path", nargs="?", default=str(DEFAULT_PATH), help="JSONL file path")
    parser.add_argument(
        "--http",
        action="store_true",
        help="POST to running API only (no local DB replace; use fresh docker volume if re-ingesting)",
    )
    parser.add_argument(
        "--no-replace",
        action="store_true",
        help="Append without clearing existing events for that store/date (DB mode only)",
    )
    args = parser.parse_args()

    path = Path(args.path)
    events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not events:
        print("No events in file", file=sys.stderr)
        sys.exit(1)

    if args.http:
        out = _ingest_via_http(events)
    else:
        out = _ingest_via_db(events, replace=not args.no_replace)

    print(json.dumps(out))


if __name__ == "__main__":
    main()
