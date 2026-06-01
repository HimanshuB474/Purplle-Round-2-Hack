# Purplle Tech Challenge 2026 — Round 2

**Store Intelligence**: CCTV → detection pipeline → events → FastAPI analytics.

Submission code: **[`store-intelligence/`](./store-intelligence/)**.

## Run the demo

**Repository:** https://github.com/HimanshuB474/Purplle-Round-2-Hack (code in `store-intelligence/`)

Try the **live** dashboard first. If Render is sleeping, slow, or metrics are empty, use the **local** steps below — same app, fully offline after clone.

| | Live (Render) | Local (Docker) |
|--|----------------|----------------|
| **Dashboard** | https://purplle-round-2-hack.onrender.com/dashboard | http://localhost:8000/dashboard |
| API docs | https://purplle-round-2-hack.onrender.com/docs | http://localhost:8000/docs |
| Metrics | [link](https://purplle-round-2-hack.onrender.com/stores/ST1008/metrics?date=2026-04-10) | http://localhost:8000/stores/ST1008/metrics?date=2026-04-10 |

**Live:** open dashboard → **Live replay** (loads 390 events). First request after idle may take 30–60s.

**Local** (requires Docker Desktop):

```bash
git clone git@github.com:HimanshuB474/Purplle-Round-2-Hack.git
cd Purplle-Round-2-Hack/store-intelligence
docker compose up -d --build
python scripts/ingest_events.py
```

Then open http://localhost:8000/dashboard (optional: **Live replay** again). Expect **71** visitors, **1.41%** conversion on `2026-04-10`.

**Verify (local):** `pytest -q` · `python scripts/validate_part_bc.py` · `python scripts/verify_docker.py`

## What is committed

| Artifact | Details |
|----------|---------|
| `data/events.jsonl` | **390** pipeline events, **all 8 types** (incl. **2** `BILLING_QUEUE_ABANDON`), `store_id: STORE_BLR_002` |
| `data/sample_events.jsonl` | 24 schema examples for CI |
| API + Docker | Six endpoints, `docker compose up` on port 8000 |

Regenerating events needs local **`../CCTV Footage/*.mp4`** (gitignored, ~650 MB).

## Pipeline (how I built it)

YOLOv8n + ByteTrack on five Brigade clips → `python -m pipeline.detect` (see [`store-intelligence/README.md`](./store-intelligence/README.md)).

| Feature | Implementation |
|---------|----------------|
| Cross-camera linking | `pipeline/reid.py` — ENTRY cam first, 120s window + HSV + score-gap guard (`--no-reid` to disable) |
| Queue abandons | Dwell-gated join/abandon in `detect.py`; committed file uses `--no-pos-filter`; default run applies POS cleanup |
| Conversion | 5‑min POS window; **one transaction → one visitor** in `app/sessions.py` |

```bash
cd store-intelligence
pip install -r requirements.txt
python -m pipeline.detect --root .              # default: Re-ID + softer abandon filter
python -m pipeline.detect --root . --no-pos-filter   # keep every abandon (committed file)
```

## Docs

| Doc | Path |
|-----|------|
| Design | [`store-intelligence/docs/DESIGN.md`](./store-intelligence/docs/DESIGN.md) |
| Choices | [`store-intelligence/docs/CHOICES.md`](./store-intelligence/docs/CHOICES.md) |
| Pre-submit | [`store-intelligence/docs/SUBMISSION-CHECKLIST.md`](./store-intelligence/docs/SUBMISSION-CHECKLIST.md) |
| Deploy | [`store-intelligence/docs/DEPLOY.md`](./store-intelligence/docs/DEPLOY.md) |

## Implementation notes

- Re-ID, queue abandons, and conversion rules are documented in [DESIGN.md §9](./store-intelligence/docs/DESIGN.md#9-implementation-notes--faq).
