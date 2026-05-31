# Store Intelligence API

Purplle Tech Challenge 2026 — Round 2. Brigade Bangalore (`ST1008` / `STORE_BLR_002`).

## Quick Start (5 commands)

```bash
git clone <repo> && cd store-intelligence
docker compose up -d --build
python -m pipeline.detect          # host — needs CCTV clips + pip install -r requirements.txt
python scripts/ingest_events.py    # POST events.jsonl → API
curl "http://localhost:8000/stores/ST1008/metrics?date=2026-04-10"
```

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

## Raw assets (repo root)

- `../CCTV Footage/CAM 1.mp4` – `CAM 5.mp4`
- `../Brigade_Bangalore_10_April_26 (1)bc6219c.csv`
- `../Brigade Road - Store layoutc5f5d56.xlsx`

## Status

- **Phase 1–3:** Complete — run `python -m pipeline.detect` then `python scripts/ingest_events.py`
