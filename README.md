# Purplle Tech Challenge 2026 — Round 2

**Store Intelligence** for Brigade Bangalore (`ST1008` / `STORE_BLR_002`): CCTV → detection pipeline → events → FastAPI analytics.

Submission code: **[`store-intelligence/`](./store-intelligence/)**.

## Quick start (reviewers)

```bash
git clone git@github.com:HimanshuB474/Purplle-Round-2-Hack.git
cd Purplle-Round-2-Hack/store-intelligence

docker compose up -d --build
python scripts/ingest_events.py
curl "http://localhost:8000/health"
curl "http://localhost:8000/stores/ST1008/metrics?date=2026-04-10"
```

**Live dashboard (Part E):** http://localhost:8000/dashboard → **Live replay** streams `data/events.jsonl` and updates metrics in real time.

**Verify:** `python scripts/verify_docker.py` · `python scripts/validate_part_bc.py` · `pytest` (46 tests)

## What is committed

| Artifact | Details |
|----------|---------|
| `data/events.jsonl` | **299** pipeline events, **all 8 types** (incl. **3** `BILLING_QUEUE_ABANDON`), `store_id: STORE_BLR_002` |
| `data/sample_events.jsonl` | 24 schema examples for CI |
| API + Docker | Six endpoints, `docker compose up` on port 8000 |

Regenerating events needs local **`../CCTV Footage/*.mp4`** (gitignored, ~650 MB).

## Pipeline (how I built it)

YOLOv8n + ByteTrack on five Brigade clips → `python -m pipeline.detect` (see [`store-intelligence/README.md`](./store-intelligence/README.md)).

| Feature | Implementation |
|---------|----------------|
| Cross-camera linking | `pipeline/reid.py` — ENTRY cam first, 120s window + HSV appearance (`--no-reid` to disable) |
| Queue abandons | Emitted on billing zone exit; committed file uses `--no-pos-filter`; default run applies softer POS cleanup |
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
| Pre-submit | [`store-intelligence/docs/PRE-PHASE3-CHECKLIST.md`](./store-intelligence/docs/PRE-PHASE3-CHECKLIST.md) |

## Limits

- Conversion follows **documented rules** (time + billing zone); may differ from hidden eval labels.
- Details: [DESIGN.md §9](https://github.com/HimanshuB474/Purplle-Round-2-Hack/blob/main/store-intelligence/docs/DESIGN.md#9-known-gaps--reviewer-faq).
