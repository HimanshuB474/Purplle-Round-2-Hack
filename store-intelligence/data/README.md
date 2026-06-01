# Data directory

| File | Status | Notes |
|------|--------|--------|
| `pos_transactions.csv` | Done | 24 invoices — [04-pos](../docs/context/04-pos-and-business-logic.md) |
| `store_layout.json` | Done | 5 cameras, zones, entry line — [03b](../docs/context/03b-store-layout-brigade-road.md) |
| `sample_events.jsonl` | Done | 24 events, all 8 types (CI) |
| `events.jsonl` | **Committed** | **390** events, **8/8** types — 2× `BILLING_QUEUE_ABANDON`, 71× `ENTRY` (customer) |
| `layout/cctv_annotated/` | Done | Zone overlay frames |

**Regenerate `events.jsonl`:** `python -m pipeline.detect --root . --no-pos-filter` (needs `../CCTV Footage/`).

**Local only:** CCTV `.mp4` at repo root (gitignored).

Audit: `python scripts/validate_project.py`
