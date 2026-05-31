"""Validate Part B (Intelligence API) and Part C (Production Readiness) requirements."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

REFERENCE_DATE = "2026-04-10"


def check(name: str, ok: bool, detail: str = "") -> tuple[str, bool, str]:
    return (name, ok, detail)


def validate_part_b() -> list[tuple[str, bool, str]]:
    import app.config as cfg
    import app.db as db
    from fastapi.testclient import TestClient
    from app.main import app

    db_path = ROOT / "data" / "validation_bc.db"
    if db_path.exists():
        db_path.unlink()
    cfg.DATABASE_URL = f"sqlite:///{db_path}"
    db._engine = None
    db._SessionLocal = None

    events = [
        json.loads(l)
        for l in (ROOT / "data" / "sample_events.jsonl").read_text().splitlines()
        if l.strip()
    ]
    pipeline_events = []
    pe = ROOT / "data" / "events.jsonl"
    if pe.exists():
        pipeline_events = [json.loads(l) for l in pe.read_text().splitlines() if l.strip()]

    results: list[tuple[str, bool, str]] = []

    with TestClient(app) as client:
        # ingest contract
        r = client.post("/events/ingest", json={"events": events[:10]})
        r2 = client.post("/events/ingest", json={"events": events[:10]})
        results.append(check("Ingest idempotent by event_id", r.json()["accepted"] == r2.json()["accepted"] == 10))

        bad = client.post("/events/ingest", json={"events": events[:2] + [{"visitor_id": "x"}]})
        bj = bad.json()
        results.append(check(
            "Ingest partial success + structured errors",
            bad.status_code == 200 and bj["rejected"] >= 1 and bj["errors"],
        ))

        over = client.post("/events/ingest", json={"events": [events[0]] * 501})
        results.append(check("Ingest batch limit 500", over.status_code == 400))

        client.post("/events/ingest", json={"events": events})

        # metrics
        m = client.get(f"/stores/ST1008/metrics?date={REFERENCE_DATE}").json()
        metrics_fields = [
            "unique_visitors", "conversion_rate", "avg_dwell_by_zone_ms",
            "queue_depth_current", "abandonment_rate",
        ]
        results.append(check("Metrics returns all required fields", all(f in m for f in metrics_fields)))

        staff = [dict(e, is_staff=True) for e in events]
        for i, e in enumerate(staff):
            e["event_id"] = f"a0000000-0000-4000-8000-{i:012d}"
        client.post("/events/ingest", json={"events": staff})
        m_staff = client.get(f"/stores/ST1008/metrics?date={REFERENCE_DATE}").json()
        results.append(check("Metrics excludes is_staff (still 5 visitors)", m_staff["unique_visitors"] == 5))

        empty = client.get(f"/stores/ST1008/metrics?date=2099-01-01").json()
        results.append(check(
            "Zero-purchase / empty day (no crash, 0 conversion)",
            empty["unique_visitors"] == 0 and empty["conversion_rate"] == 0.0,
        ))

        # funnel
        f = client.get(f"/stores/ST1008/funnel?date={REFERENCE_DATE}").json()
        stages = [s["stage"] for s in f["stages"]]
        counts = [s["count"] for s in f["stages"]]
        results.append(check("Funnel 4 stages with drop-off", stages == ["ENTRY", "ZONE_VISIT", "BILLING_QUEUE", "PURCHASE"]))
        results.append(check("Funnel monotonic counts", counts[0] >= counts[1] >= counts[2] >= counts[3]))

        re_events = [
            {
                "event_id": "b1000001-0001-4000-8000-000000000001",
                "store_id": "ST1008", "camera_id": "CAM_ENTRY_01", "visitor_id": "VIS_re",
                "event_type": "ENTRY", "timestamp": "2026-04-10T20:10:00Z", "zone_id": None,
                "dwell_ms": 0, "is_staff": False, "confidence": 0.9,
                "metadata": {"queue_depth": None, "sku_zone": None, "session_seq": 1},
            },
            {
                "event_id": "b1000001-0001-4000-8000-000000000002",
                "store_id": "ST1008", "camera_id": "CAM_ENTRY_01", "visitor_id": "VIS_re",
                "event_type": "EXIT", "timestamp": "2026-04-10T20:11:00Z", "zone_id": None,
                "dwell_ms": 0, "is_staff": False, "confidence": 0.9,
                "metadata": {"queue_depth": None, "sku_zone": None, "session_seq": 2},
            },
            {
                "event_id": "b1000001-0001-4000-8000-000000000003",
                "store_id": "ST1008", "camera_id": "CAM_ENTRY_01", "visitor_id": "VIS_re",
                "event_type": "REENTRY", "timestamp": "2026-04-10T20:12:00Z", "zone_id": None,
                "dwell_ms": 0, "is_staff": False, "confidence": 0.9,
                "metadata": {"queue_depth": None, "sku_zone": None, "session_seq": 3},
            },
        ]
        client.post("/events/ingest", json={"events": re_events})
        entry_n = client.get(f"/stores/ST1008/funnel?date={REFERENCE_DATE}").json()["stages"][0]["count"]
        results.append(check("Funnel re-entry not double-counted", entry_n == 6))  # 5 sample + VIS_re

        # heatmap
        h = client.get(f"/stores/ST1008/heatmap?date={REFERENCE_DATE}").json()
        scores_ok = all(0 <= z["combined_score"] <= 100 for z in h["zones"]) if h["zones"] else True
        results.append(check("Heatmap scores 0-100 + data_confidence", scores_ok and h["data_confidence"] in ("LOW", "HIGH")))

        h_empty = client.get(f"/stores/ST1008/heatmap?date=2099-01-01").json()
        results.append(check("Heatmap LOW confidence when <20 sessions", h_empty["data_confidence"] == "LOW"))

        # anomalies
        from uuid import uuid4
        spike = [
            {
                "event_id": str(uuid4()), "store_id": "ST1008", "camera_id": "CAM_BILLING_01",
                "visitor_id": "VIS_q", "event_type": "BILLING_QUEUE_JOIN",
                "timestamp": "2026-04-10T20:10:00Z", "zone_id": "BILLING", "dwell_ms": 0,
                "is_staff": False, "confidence": 0.9,
                "metadata": {"queue_depth": 4, "sku_zone": "QUEUE", "session_seq": 1},
            },
            {
                "event_id": str(uuid4()), "store_id": "ST1008", "camera_id": "CAM_BILLING_01",
                "visitor_id": "VIS_q2", "event_type": "BILLING_QUEUE_JOIN",
                "timestamp": "2026-04-10T20:12:30Z", "zone_id": "BILLING", "dwell_ms": 0,
                "is_staff": False, "confidence": 0.9,
                "metadata": {"queue_depth": 4, "sku_zone": "QUEUE", "session_seq": 1},
            },
        ]
        client.post("/events/ingest", json={"events": spike})
        anom = client.get(f"/stores/ST1008/anomalies?date={REFERENCE_DATE}").json()["anomalies"]
        types = {a["type"] for a in anom}
        sev_ok = all(a["severity"] in ("INFO", "WARN", "CRITICAL") for a in anom)
        action_ok = all(a.get("suggested_action") for a in anom)
        results.append(check("Anomalies: queue spike detector", "BILLING_QUEUE_SPIKE" in types))
        results.append(check("Anomalies: dead zone detector", "DEAD_ZONE" in types))
        results.append(check("Anomalies: severity + suggested_action", sev_ok and action_ok))

        # health
        health = client.get("/health").json()
        results.append(check("Health: status + per-store feed", health["status"] == "OK" and len(health["stores"]) >= 1))

        # alias
        alias = client.get(f"/stores/STORE_BLR_002/metrics?date={REFERENCE_DATE}")
        results.append(check("Store alias STORE_BLR_002", alias.status_code == 200))

        # real-time: computed_at fresh
        results.append(check("Metrics computed_at present (real-time)", "computed_at" in m))

        if pipeline_events:
            db_path2 = ROOT / "data" / "validation_bc_pipeline.db"
            if db_path2.exists():
                db_path2.unlink()
            cfg.DATABASE_URL = f"sqlite:///{db_path2}"
            db._engine = None
            db._SessionLocal = None
            with TestClient(app) as c2:
                c2.post("/events/ingest", json={"events": pipeline_events})
                pm = c2.get(f"/stores/ST1008/metrics?date={REFERENCE_DATE}").json()
                results.append(check(
                    "Pipeline events ingest + metrics",
                    pm["unique_visitors"] > 0,
                    f"{pm['unique_visitors']} visitors",
                ))

    return results


def validate_part_c() -> list[tuple[str, bool, str]]:
    results: list[tuple[str, bool, str]] = []

    docker = (ROOT / "docker-compose.yml").exists() and (ROOT / "Dockerfile").exists()
    results.append(check("Dockerfile + docker-compose.yml present", docker))

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    results.append(check("README Quick Start section", "Quick Start" in readme and "docker compose" in readme))
    results.append(check("README pipeline instructions", "pipeline.detect" in readme or "pipeline/run.sh" in readme))
    results.append(check("README ingest into API", "ingest" in readme.lower()))

    # logging fields in code
    log_src = (ROOT / "app" / "logging_config.py").read_text(encoding="utf-8")
    for field in ("trace_id", "store_id", "endpoint", "latency_ms", "event_count", "status_code"):
        results.append(check(f"Logging field: {field}", field in log_src))

    # 503 handling in code
    ingest_src = (ROOT / "app" / "ingestion.py").read_text(encoding="utf-8")
    deps_src = (ROOT / "app" / "deps.py").read_text(encoding="utf-8")
    health_src = (ROOT / "app" / "health.py").read_text(encoding="utf-8")
    results.append(check("503 on ingest when DB down (code)", "require_db" in ingest_src and "503" in deps_src))
    results.append(check("503 on health when DB down (code)", "503" in health_src and "UNAVAILABLE" in health_src))

    main_src = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
    results.append(check("No raw stack traces in responses (generic handler)", "traceback" not in main_src.lower()))

    # tests
    test_dir = ROOT / "tests"
    test_files = list(test_dir.glob("test_*.py"))
    test_text = "\n".join(t.read_text(encoding="utf-8") for t in test_files)
    edge_cases = {
        "empty store": "empty_store" in test_text or "empty store" in test_text.lower(),
        "all-staff": "all_staff" in test_text or "is_staff" in test_text,
        "re-entry funnel": "reentry" in test_text.lower() or "REENTRY" in test_text,
        "idempotent ingest": "idempotent" in test_text.lower(),
    }
    for name, ok in edge_cases.items():
        results.append(check(f"Test edge case: {name}", ok))

    # coverage threshold in pyproject
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    results.append(check("Coverage fail_under >= 70 in pyproject.toml", "fail_under = 70" in pyproject))

    # pytest run
    import subprocess
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "--cov=app", "-q"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    cov_line = [l for l in proc.stdout.splitlines() if "Total coverage" in l or "Required test coverage" in l]
    cov_ok = proc.returncode == 0
    results.append(check("pytest + coverage >70%", cov_ok, cov_line[-1] if cov_line else proc.stdout[-200:]))

    # missing tests noted in checklist
    results.append(check("Test: STALE_FEED (automated)", "STALE_FEED" in test_text))
    results.append(check("Test: DB unavailable 503 (automated)", "503" in test_text and "unavailable" in test_text.lower()))
    results.append(check("Test: CONVERSION_DROP (automated)", "CONVERSION_DROP" in test_text))

    return results


def main() -> int:
    print("=" * 70)
    print("PART B + PART C VALIDATION")
    print("=" * 70)

    part_b = validate_part_b()
    part_c = validate_part_c()

    def report(title: str, rows: list[tuple[str, bool, str]]) -> tuple[int, int]:
        print(f"\n{title}")
        print("-" * 70)
        passed = 0
        for name, ok, detail in rows:
            status = "YES" if ok else "NO "
            print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))
            if ok:
                passed += 1
        return passed, len(rows)

    pb, tb = report("PART B — Intelligence API", part_b)
    pc, tc = report("PART C — Production Readiness", part_c)

    print("\n" + "=" * 70)
    print(f"PART B: {pb}/{tb}")
    print(f"PART C: {pc}/{tc}")
    print(f"TOTAL:  {pb + pc}/{tb + tc}")
    print("=" * 70)
    print("\nNote: docker compose not run (Docker CLI not available on this machine).")
    return 0 if pb == tb and pc == tc else 1


if __name__ == "__main__":
    sys.exit(main())
