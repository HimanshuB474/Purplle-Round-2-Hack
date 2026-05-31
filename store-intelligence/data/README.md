# Data directory



| File | Status | Spec |

|------|--------|------|

| `pos_transactions.csv` | Done | 24 invoices — `scripts/build_pos_transactions.py` — [04-pos-and-business-logic.md](../docs/context/04-pos-and-business-logic.md) |

| `store_layout.json` | Done | Verified cameras + zone polygons — [03b-store-layout](../docs/context/03b-store-layout-brigade-road.md) |

| `sample_events.jsonl` | Done | 24 events — **all 8 types** (includes `BILLING_QUEUE_ABANDON`) for CI/schema — [02-event-schema.md](../docs/context/02-event-schema.md) |

| `layout/cctv_annotated/` | Done | Zone overlays on sample frames |

| `events.jsonl` | Committed | **302** events from pipeline (`python -m pipeline.detect`); **7/8** types — no `BILLING_QUEUE_ABANDON` (see [DESIGN.md §9.2](../docs/DESIGN.md#92-billing_queue_abandon-absent-from-eventsjsonl)) |



**Local only:** `../CCTV Footage/` for pipeline re-runs (not in git).



Run `python scripts/validate_project.py` to audit data + docs consistency.


