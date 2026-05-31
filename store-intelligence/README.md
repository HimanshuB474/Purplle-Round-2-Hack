# Store Intelligence API

Purplle Tech Challenge 2026 — Round 2. Brigade Bangalore (`ST1008` / `STORE_BLR_002`).

## Quick Start (5 commands)

```bash
git clone git@github.com:HimanshuB474/Purplle-Round-2-Hack.git
cd Purplle-Round-2-Hack/store-intelligence
docker compose up -d --build
python -m pipeline.detect          # host — needs CCTV clips + pip install -r requirements.txt
python scripts/ingest_events.py    # POST events.jsonl → API
curl "http://localhost:8000/stores/ST1008/metrics?date=2026-04-10"
```

**Live dashboard:** http://localhost:8000/dashboard (click **Live replay** after `docker compose up`)

**Verify Docker only:** `python scripts/verify_docker.py`

**Windows:** If `docker` is not on PATH, start Docker Desktop first. Compose uses API-only image (~150 MB, no PyTorch).

Pipeline writes `data/events.jsonl` with `store_id: STORE_BLR_002`. Verify: `python scripts/verify_events.py`.

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | API index (links to endpoints) |
| GET | `/health` | Service + feed status (`STALE_FEED` if lag >10 min) |
| GET | `/docs` | Swagger UI |
| POST | `/events/ingest` | Batch ingest (≤500, idempotent) |
| GET | `/stores/{id}/metrics?date=` | Visitors, conversion, dwell |
| GET | `/stores/{id}/funnel?date=` | Session funnel |
| GET | `/stores/{id}/heatmap?date=` | Zone scores |
| GET | `/stores/{id}/anomalies?date=` | Queue spike, conversion drop, dead zones |

Store IDs: `ST1008` (canonical) and `STORE_BLR_002` (alias). Use `?date=2026-04-10` for sample/POS data.

## Verify

```bash
pytest
python scripts/validate_part_bc.py
python scripts/verify_phase2.py
python scripts/verify_events.py
```

## Documentation

| Doc | Path |
|-----|------|
| Context index | [docs/context/README.md](docs/context/README.md) |
| Design (submit) | [docs/DESIGN.md](docs/DESIGN.md) |
| Choices (submit) | [docs/CHOICES.md](docs/CHOICES.md) |

## Data in repo

Committed under `data/`: `events.jsonl`, `sample_events.jsonl`, `pos_transactions.csv`, `store_layout.json`, layout images.

**Local only (not in git):** `../CCTV Footage/*.mp4` for re-running `python -m pipeline.detect`.

## Known gaps (reviewers)

Documented in [`docs/DESIGN.md`](docs/DESIGN.md#9-known-gaps--reviewer-faq): no cross-camera Re-ID; `BILLING_QUEUE_ABANDON` only in `sample_events.jsonl`; conversion heuristic. **Dashboard:** [`/dashboard`](http://localhost:8000/dashboard).

## Status

- **Phase 1–3:** Complete — `data/events.jsonl` committed; regen with `python -m pipeline.detect` + `scripts/ingest_events.py`
