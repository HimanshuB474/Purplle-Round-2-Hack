# Pre–Phase 3 Checklist (vs Evaluation Framework PDF)

Source: `Assessment  Evaluation Frameworkb24a398.pdf` + Problem Statement PDF.  
Last reviewed: after Phase 2.

## Acceptance gate (mandatory before scoring)

| # | Framework requirement | Status | Notes |
|---|----------------------|--------|-------|
| 1 | `docker compose up` without manual steps | ⚠️ Verify | Compose file ready; confirm on a machine with Docker |
| 2 | `/metrics` returns valid response | ✅ | `GET /stores/ST1008/metrics` + `STORE_BLR_002` alias |
| 3 | **Detection pipeline produces structured events** | ✅ | `data/events.jsonl` from `python -m pipeline.detect` |
| 4 | `DESIGN.md` + `CHOICES.md` non-trivial (>250 words) | ✅ | Updated post–Phase 2 |
| 5 | System stable on basic execution | ✅ | 22+ pytest tests; no crash on empty store |

**Blocker:** Item 3 fails until Phase 3 emits real events from CCTV clips.

## Scoring areas (100 marks)

| Area | Pts | Ready? | Gap |
|------|-----|--------|-----|
| **A — Detection** | 30 | ⚠️ | Pipeline runs; tune entry counts vs ground truth; CAM4 often 0 detections |
| **B — API** | 35 | ✅ mostly | Held-out event set at scoring time; funnel/anomalies implemented |
| **C — Production** | 20 | ⚠️ | Docker untested here; logging OK; add DB-down test; `test_pipeline.py` empty |
| **D — Thinking** | 15 | ✅ | DESIGN §7 + CHOICES (3 decisions) filled |
| **E — Dashboard** | +10 | ❌ | Optional `dashboard/live.py` stub |

## Integrity caps (score max 50 if violated)

| Check | Status |
|-------|--------|
| No hardcoded metrics | ✅ Compute-on-read from SQLite |
| Outputs vary with ingest | ✅ Verified in tests |
| Real computation | ✅ POS + event correlation in `app/sessions.py` |

## Smaller fixes applied before Phase 3

- `assertions.py` — challenge example assertions (pytest)
- README — 5-command acceptance flow + pipeline step
- 503 body — `{ "status": "UNAVAILABLE", "reason": "..." }` on health/ingest when DB down
- This checklist document

## Still recommended before / during Phase 3

1. Implement `pipeline/detect.py` + wire `run.sh` → `data/events.jsonl`
2. Fill `tests/test_pipeline.py` PROMPT block + schema/unique-id tests
3. Add `test_ingest_db_unavailable_503` (mock DB failure)
4. Mount or document `../CCTV Footage` for Docker pipeline runs
5. Optional: live dashboard for +10 bonus
6. Re-run ingest of **pipeline** events (not only `sample_events.jsonl`) so conversion rate aligns with POS windows

## Reviewer time box (from framework)

Reviewers spend ~2 min running system, ~2 min inspecting events, ~3 min API outputs — ensure `events.jsonl` is easy to find and schema-valid after Phase 3.
