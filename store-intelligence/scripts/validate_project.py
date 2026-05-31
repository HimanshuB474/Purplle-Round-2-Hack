"""Validate project state against docs and rules."""
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
issues: list[str] = []
warnings: list[str] = []
ok: list[str] = []


def check(name: str, condition: bool, msg: str, *, warn: bool = False) -> None:
    (warnings if warn else issues).append(msg) if not condition else ok.append(name)


# --- Data files ---
pos_path = ROOT / "data" / "pos_transactions.csv"
if pos_path.exists():
    pos = pd.read_csv(pos_path)
    check("pos_rows", len(pos) == 24, f"POS has {len(pos)} rows, expected 24")
    check("pos_store", pos["store_id"].eq("ST1008").all(), "POS store_id must be ST1008")
    check("pos_cols", list(pos.columns) == ["store_id", "transaction_id", "timestamp", "basket_value_inr"], "POS columns mismatch")
    bad_float = pos["basket_value_inr"].apply(lambda x: round(float(x), 2) != float(x))
    check("pos_rounding", not bad_float.any(), "POS basket_value_inr has >2 decimal places", warn=True)
else:
    issues.append("Missing data/pos_transactions.csv")

layout_path = ROOT / "data" / "store_layout.json"
if layout_path.exists():
    layout = json.loads(layout_path.read_text(encoding="utf-8"))
    store = layout["stores"][0]
    check("layout_store", store["store_id"] == "ST1008", "store_layout store_id must be ST1008")
    cams = store["cameras"]
    check("layout_cam_count", len(cams) == 5, f"Expected 5 cameras, got {len(cams)}")

    expected = {
        "CAM 3.mp4": ("CAM_ENTRY_01", "ENTRY"),
        "CAM 1.mp4": ("CAM_FLOOR_SKIN_01", "MAIN"),
        "CAM 2.mp4": ("CAM_FLOOR_MAKEUP_01", "MAIN"),
        "CAM 5.mp4": ("CAM_BILLING_01", "BILLING"),
        "CAM 4.mp4": ("CAM_STAFF_BACK_01", "STAFF"),
    }
    for cam in cams:
        exp = expected.get(cam["source_file"])
        if exp:
            cid, role = exp
            check(f"cam_{cam['source_file']}", cam["camera_id"] == cid and cam["role"] == role,
                  f"{cam['source_file']}: expected {cid}/{role}, got {cam['camera_id']}/{cam['role']}")
        clip = (ROOT / cam["clip_path"]).resolve()
        check(f"clip_{cam['source_file']}", clip.exists(), f"Clip not found: {clip}")
        if cam["role"] == "ENTRY" and "entry_line" not in cam:
            issues.append(f"{cam['camera_id']}: ENTRY camera missing entry_line")
        for z in cam.get("zones", []):
            if "polygon" not in z or len(z["polygon"]) < 3:
                issues.append(f"{cam['camera_id']}: zone {z.get('zone_id')} missing polygon")
else:
    issues.append("Missing data/store_layout.json")

# --- Docs consistency ---
stale = ROOT / "docs" / "context" / "06-detection-pipeline.md"
if stale.exists():
    text = stale.read_text(encoding="utf-8")
    check("doc06_no_stale_cam1_entry", "CAM 1.mp4 | CAM_ENTRY_01 | ENTRY" not in text,
          "06-detection-pipeline.md still has wrong CAM1=ENTRY mapping", warn=True)
    check("doc06_no_tbd", '"entry_line": "TBD"' not in text,
          "06-detection-pipeline.md still has TBD entry_line", warn=True)

# --- Sample events ---
sample_path = ROOT / "data" / "sample_events.jsonl"
if sample_path.exists():
    from app.models import StoreEvent

    lines = [ln for ln in sample_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    check("sample_event_count", len(lines) >= 20, f"sample_events.jsonl has {len(lines)} events, need >=20")
    types_seen: set[str] = set()
    for i, ln in enumerate(lines, 1):
        try:
            ev = StoreEvent.model_validate_json(ln)
            types_seen.add(ev.event_type.value)
        except Exception as e:
            issues.append(f"sample_events.jsonl line {i}: {e}")
    missing_types = {
        "ENTRY", "EXIT", "ZONE_ENTER", "ZONE_EXIT", "ZONE_DWELL",
        "BILLING_QUEUE_JOIN", "BILLING_QUEUE_ABANDON", "REENTRY",
    } - types_seen
    check("sample_event_types", not missing_types,
          f"sample_events.jsonl missing event types: {sorted(missing_types)}")
else:
    warnings.append("Missing: data/sample_events.jsonl")

# --- Missing deliverables ---
for rel, warn_only in [
    ("docs/DESIGN.md", True),
    ("docs/CHOICES.md", True),
]:
    p = ROOT / rel
    if not p.exists():
        (warnings if warn_only else issues).append(f"Missing: {rel}")
    elif rel.endswith(".md") and len(p.read_text(encoding="utf-8").split()) < 250:
        warnings.append(f"{rel} under 250 words (acceptance gate)")

# --- API acceptance gate ---
try:
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    check("health", client.get("/health").status_code == 200, "GET /health failed")
    m = client.get("/stores/ST1008/metrics?date=2026-04-10")
    check("metrics_st1008", m.status_code == 200, f"GET /stores/ST1008/metrics returned {m.status_code}")
    m2 = client.get("/stores/STORE_BLR_002/metrics?date=2026-04-10")
    check("metrics_alias", m2.status_code == 200, f"GET /stores/STORE_BLR_002/metrics returned {m2.status_code}")
except Exception as e:
    issues.append(f"API import/test failed: {e}")

# --- Tests ---
test_files = list((ROOT / "tests").glob("test_*.py"))
for tf in test_files:
    head = tf.read_text(encoding="utf-8")[:300]
    if "PROMPT:" not in head:
        warnings.append(f"{tf.name}: missing # PROMPT: block (Part D requirement)")

print("=" * 60)
print("VALIDATION REPORT")
print("=" * 60)
print(f"\nOK ({len(ok)}):", *ok, sep="\n  " if ok else " none")
print(f"\nWARNINGS ({len(warnings)}):")
for w in warnings:
    print(f"  [WARN] {w}")
print(f"\nISSUES ({len(issues)}):")
for i in issues:
    print(f"  [FAIL] {i}")
print()
sys.exit(1 if issues else 0)
