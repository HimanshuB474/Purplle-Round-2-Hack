# Data directory



| File | Status | Spec |

|------|--------|------|

| `pos_transactions.csv` | Done | 24 invoices — `scripts/build_pos_transactions.py` — [04-pos-and-business-logic.md](../docs/context/04-pos-and-business-logic.md) |

| `store_layout.json` | Done | Verified cameras + zone polygons — [03b-store-layout](../docs/context/03b-store-layout-brigade-road.md) |

| `sample_events.jsonl` | Done | 24 sample events, all 8 types — [02-event-schema.md](../docs/context/02-event-schema.md) |

| `layout/cctv_annotated/` | Done | Zone overlays on sample frames |

| `events.jsonl` | Generated | ~90 events from CCTV via `python -m pipeline.detect` |



**Local only:** `../CCTV Footage/` for pipeline re-runs (not in git).



Run `python scripts/validate_project.py` to audit data + docs consistency.


