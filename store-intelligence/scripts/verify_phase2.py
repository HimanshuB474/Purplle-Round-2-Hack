"""End-to-end Phase 2 verification — ingest sample events and exercise all endpoints."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
REFERENCE_DATE = "2026-04-10"


def main() -> int:
    # Fresh DB for clean verification
    import app.config as config
    import app.db as db_module

    db_path = ROOT / "data" / "phase2_verify.db"
    if db_path.exists():
        db_path.unlink()
    db_url = f"sqlite:///{db_path}"
    config.DATABASE_URL = db_url
    db_module._engine = None
    db_module._SessionLocal = None

    from app.main import app
    from app.pos import load_pos_transactions

    load_pos_transactions.cache_clear()

    failures: list[str] = []
    checks: list[str] = []

    with TestClient(app) as client:
        # 1. Health (empty)
        r = client.get("/health")
        if r.status_code != 200:
            failures.append(f"health empty: {r.status_code}")
        else:
            checks.append("health (empty DB)")

        # 2. Metrics empty store
        r = client.get(f"/stores/ST1008/metrics?date={REFERENCE_DATE}")
        body = r.json()
        if r.status_code != 200:
            failures.append(f"metrics empty: {r.status_code}")
        elif body["unique_visitors"] != 0 or body["total_transactions"] != 24:
            failures.append(f"metrics empty unexpected: {body}")
        else:
            checks.append("metrics empty (0 visitors, 24 POS txns)")

        # 3. Ingest sample events
        events = [
            json.loads(line)
            for line in (ROOT / "data" / "sample_events.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        r = client.post("/events/ingest", json={"events": events})
        ingest = r.json()
        if r.status_code != 200 or ingest["accepted"] != 24 or ingest["rejected"] != 0:
            failures.append(f"ingest failed: {r.status_code} {ingest}")
        else:
            checks.append(f"ingest ({ingest['accepted']} events)")

        # 4. Idempotent re-ingest
        r2 = client.post("/events/ingest", json={"events": events})
        if r2.json()["accepted"] != 24:
            failures.append(f"idempotency failed: {r2.json()}")
        else:
            checks.append("ingest idempotent")

        # 5. All GET endpoints ST1008
        for path in ["metrics", "funnel", "heatmap", "anomalies"]:
            r = client.get(f"/stores/ST1008/{path}?date={REFERENCE_DATE}")
            if r.status_code != 200:
                failures.append(f"{path} ST1008: {r.status_code}")
            else:
                checks.append(f"GET /stores/ST1008/{path}")

        # 6. Alias STORE_BLR_002
        r = client.get(f"/stores/STORE_BLR_002/metrics?date={REFERENCE_DATE}")
        if r.status_code != 200 or r.json()["store_id"] != "STORE_BLR_002":
            failures.append(f"alias metrics: {r.status_code} {r.json()}")
        else:
            checks.append("STORE_BLR_002 alias")

        # 7. Metrics after ingest — sanity
        m = client.get(f"/stores/ST1008/metrics?date={REFERENCE_DATE}").json()
        if m["unique_visitors"] != 5:  # 6 ENTRY minus 1 staff
            failures.append(f"expected 5 unique_visitors, got {m['unique_visitors']}")
        else:
            checks.append(f"metrics: {m['unique_visitors']} visitors, conv={m['conversion_rate']}")

        # 8. Funnel shape
        stages = client.get(f"/stores/ST1008/funnel?date={REFERENCE_DATE}").json()["stages"]
        names = [s["stage"] for s in stages]
        counts = [s["count"] for s in stages]
        if names != ["ENTRY", "ZONE_VISIT", "BILLING_QUEUE", "PURCHASE"]:
            failures.append(f"funnel stages wrong: {names}")
        elif not (counts[0] >= counts[1] >= counts[2] >= counts[3]):
            failures.append(f"funnel not monotonic: {counts}")
        else:
            checks.append(f"funnel monotonic {counts}")

        # 9. Heatmap confidence
        h = client.get(f"/stores/ST1008/heatmap?date={REFERENCE_DATE}").json()
        if h["data_confidence"] not in ("LOW", "HIGH") or not h["zones"]:
            failures.append(f"heatmap bad: {h}")
        else:
            checks.append(f"heatmap ({h['data_confidence']}, {len(h['zones'])} zones)")

        # 10. Unknown store 404
        if client.get("/stores/UNKNOWN/metrics").status_code != 404:
            failures.append("unknown store should 404")
        else:
            checks.append("unknown store 404")

        # 11. Batch >500 rejected
        if client.post("/events/ingest", json={"events": events[:1] * 501}).status_code != 400:
            failures.append("batch >500 should 400")
        else:
            checks.append("batch limit 500")

    print("=" * 60)
    print("PHASE 2 E2E VERIFICATION")
    print("=" * 60)
    print(f"\nPASSED ({len(checks)}):")
    for c in checks:
        print(f"  [OK] {c}")
    if failures:
        print(f"\nFAILED ({len(failures)}):")
        for f in failures:
            print(f"  [FAIL] {f}")
        return 1
    print("\nAll Phase 2 checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
