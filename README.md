# Purplle Tech Challenge 2026 — Round 2

**Store Intelligence** for Brigade Bangalore (`ST1008` / `STORE_BLR_002`): CCTV → detection pipeline → events → FastAPI analytics.

All submission code lives in **[`store-intelligence/`](./store-intelligence/)**.

## Quick start (reviewers)

```bash
git clone git@github.com:HimanshuB474/Purplle-Round-2-Hack.git
cd Purplle-Round-2-Hack/store-intelligence

docker compose up -d --build
python scripts/ingest_events.py
curl "http://localhost:8000/health"
curl "http://localhost:8000/stores/ST1008/metrics?date=2026-04-10"
```

**Live dashboard (Part E):** http://localhost:8000/dashboard → click **Live replay** to stream events and watch metrics update.

**Docker smoke test:** `python scripts/verify_docker.py`  
**Full validation:** `python scripts/validate_part_bc.py`  
**Tests:** `pytest` (from `store-intelligence/`)

Pre-generated pipeline output is committed as `store-intelligence/data/events.jsonl` (~302 events). Re-running CV locally requires CCTV clips (not in git; see below).

## Repository layout

| Path | Purpose |
|------|---------|
| [`store-intelligence/`](./store-intelligence/) | Pipeline, API, tests, Docker, committed `data/` |
| [`store-intelligence/docs/DESIGN.md`](./store-intelligence/docs/DESIGN.md) | Architecture (submission) |
| [`store-intelligence/docs/CHOICES.md`](./store-intelligence/docs/CHOICES.md) | Three design decisions (submission) |
| [`CONTEXT.md`](./CONTEXT.md) | Dev context index → `store-intelligence/docs/context/` |

## API (summary)

| Method | Path |
|--------|------|
| POST | `/events/ingest` |
| GET | `/stores/{id}/metrics?date=` |
| GET | `/stores/{id}/funnel?date=` |
| GET | `/stores/{id}/heatmap?date=` |
| GET | `/stores/{id}/anomalies?date=` |
| GET | `/health` |

Swagger: `http://localhost:8000/docs` after `docker compose up`.

## Not in this repository

These are **local-only** (gitignored). The repo ships derived artifacts under `store-intelligence/data/` instead:

- Challenge PDFs and assessment framework
- Brigade POS line-item CSV and layout `.xlsx`
- `CCTV Footage/*.mp4` (~650 MB) — needed only to re-run `python -m pipeline.detect`

Place CCTV at repo root next to `store-intelligence/` if regenerating events:

```
Purplle-Round-2-Hack/
├── CCTV Footage/          # local
│   ├── CAM 1.mp4 … CAM 5.mp4
└── store-intelligence/
```

## Known gaps (documented for reviewers)

| Topic | Summary |
|-------|---------|
| Cross-camera Re-ID | Not implemented — `VIS_####` per track, not per person across cameras |
| `BILLING_QUEUE_ABANDON` | **0** in committed `events.jsonl`; **1** in `sample_events.jsonl` (all 8 types) |
| Conversion rate | 5‑min POS window + billing zone — heuristic, not ground-truth labels |
| Live dashboard | **Built** — http://localhost:8000/dashboard |

Other gaps (Re-ID, abandon in pipeline file, conversion heuristic): [`DESIGN.md §9`](./store-intelligence/docs/DESIGN.md#9-known-gaps--reviewer-faq).

## Status

Phases 1–3 complete: pipeline, ingest, metrics/funnel/heatmap/anomalies, Docker, 40 tests. Pre-submit checklist: [`store-intelligence/docs/PRE-PHASE3-CHECKLIST.md`](./store-intelligence/docs/PRE-PHASE3-CHECKLIST.md).
