# Submission readiness checklist

> **Superseded title:** was “Pre–Phase 3”; all phases complete as of May 2026.  
> Use this before submitting the GitHub link. Detailed gap analysis: [DESIGN.md §9](./DESIGN.md#9-known-gaps--reviewer-faq).

## Acceptance gate

| # | Requirement | Status | How to verify |
|---|-------------|--------|----------------|
| 1 | `docker compose up` without manual steps | ✅ | `cd store-intelligence && docker compose up -d --build` |
| 2 | `/metrics` returns valid JSON | ✅ | `curl "http://localhost:8000/stores/ST1008/metrics?date=2026-04-10"` |
| 3 | Detection pipeline → structured events | ✅ | Committed `data/events.jsonl` (302 events); regen: `python -m pipeline.detect` |
| 4 | `DESIGN.md` + `CHOICES.md` (>250 words, AI decisions) | ✅ | `docs/DESIGN.md` §8, `docs/CHOICES.md` ×3 |
| 5 | Stable execution | ✅ | `pytest` — 40 tests |

## Scoring areas (100 + 10 bonus)

| Area | Pts | Status | Notes |
|------|-----|--------|-------|
| A — Detection | 30 | ✅ submitted | Pipeline + committed `events.jsonl`; see [known gaps](./DESIGN.md#9-known-gaps--reviewer-faq) for Re-ID / abandon |
| B — API | 35 | ✅ | Six endpoints; `validate_part_bc.py` |
| C — Production | 20 | ✅ | Docker, logging, 503 on DB down (`test_degradation.py`) |
| D — Thinking | 15 | ✅ | DESIGN + CHOICES |
| E — Dashboard | +10 | ❌ not built | `dashboard/live.py` stub only — optional bonus |

## Integrity (score cap at 50 if violated)

| Check | Status |
|-------|--------|
| No hardcoded visitor counts | ✅ `app/metrics.py` compute-on-read |
| Metrics change after ingest | ✅ `tests/test_metrics.py` |
| Real POS correlation | ✅ `app/sessions.apply_pos_conversions()` |

## Known gaps (documented — not blockers)

| Gap | Where documented | Reviewer action |
|-----|------------------|-----------------|
| No cross-camera Re-ID | DESIGN §9.1, CHOICES §Limitations | Expect separate `VIS_####` per track/clip |
| No `BILLING_QUEUE_ABANDON` in `events.jsonl` | DESIGN §9.2, `data/README.md` | Use `sample_events.jsonl` for all 8 types |
| Conversion rate heuristic | DESIGN §9.3, CHOICES Decision 3 | 5‑min POS window; may differ from hidden labels |
| Part E dashboard | DESIGN §9.4 | API + Swagger sufficient for base score |

## Pre-submit commands

```bash
cd store-intelligence
docker compose down -v && docker compose up -d --build
python scripts/verify_docker.py
python scripts/ingest_events.py
python scripts/validate_part_ab.py
python scripts/validate_part_bc.py
pytest -q
```

## Admin

- [ ] GitHub repo link submitted
- [ ] Reviewer GitHub handle invited (private repo)
- [ ] Root [README.md](../../README.md) quick start works from fresh clone
