# Store Intelligence API

Purplle Tech Challenge 2026 — Round 2. Brigade Bangalore (`ST1008` / `STORE_BLR_002`).

## Run the demo

Try **live** first; if Render is down or slow, use **local Docker** (same UI and metrics).

| | Live (Render) | Local (Docker) |
|--|----------------|----------------|
| **Dashboard** | https://purplle-round-2-hack.onrender.com/dashboard | http://localhost:8000/dashboard |
| API docs | https://purplle-round-2-hack.onrender.com/docs | http://localhost:8000/docs |
| Metrics | [ST1008 metrics](https://purplle-round-2-hack.onrender.com/stores/ST1008/metrics?date=2026-04-10) | http://localhost:8000/stores/ST1008/metrics?date=2026-04-10 |

**Live:** open dashboard → **Live replay** (390 events). Allow ~30–60s on first load if idle.

**Local fallback:**

```bash
git clone git@github.com:HimanshuB474/Purplle-Round-2-Hack.git
cd Purplle-Round-2-Hack/store-intelligence
docker compose up -d --build
python scripts/ingest_events.py
```

Open http://localhost:8000/dashboard — optional **Live replay** to animate metrics. Details: [docs/DEPLOY.md](docs/DEPLOY.md).

**Validate (submission):**

```bash
pytest -q
python scripts/validate_part_ab.py
python scripts/validate_part_bc.py
python scripts/verify_docker.py
```

See [docs/SUBMISSION-CHECKLIST.md](docs/SUBMISSION-CHECKLIST.md) · [docs/DEPLOY.md](docs/DEPLOY.md)

### Verified output (local Docker)

After `docker compose up -d --build` and `python scripts/ingest_events.py` (390 events):

| Metric | Value |
|--------|-------|
| `unique_visitors` | **71** |
| `converted_visitors` | **1** |
| `conversion_rate` | **1.41%** (0.0141) |
| `abandonment_rate` | **25%** (0.25) |
| Funnel | ENTRY 71 → ZONE_VISIT 41 → BILLING_QUEUE 7 → PURCHASE 1 |

**Dashboard:** http://localhost:8000/dashboard — **Live replay** resets DB and streams the same 390 events; metrics climb in real time.

## Committed pipeline output

| File | Contents |
|------|----------|
| `data/events.jsonl` | **390** events, **all 8** `event_type` values (2× `BILLING_QUEUE_ABANDON`, 32 staff-tagged) |
| `data/sample_events.jsonl` | 24 events for CI / schema checks |

Generated with:

```bash
python -m pipeline.detect --root . --no-pos-filter
```

(`--no-pos-filter` keeps queue-abandon events that a POS correlation would treat as false positives.)

## Detection pipeline

| Step | Module |
|------|--------|
| Person detect + track | `pipeline/detect.py` (YOLOv8n + ByteTrack) |
| Zones / entry line | `pipeline/zones.py`, `data/store_layout.json` |
| Staff (CAM 4) | HOG fallback + `is_staff=true` |
| Cross-camera IDs | `pipeline/reid.py` (120s gap + HSV histogram + score-gap guard; `--no-reid` off) |
| Abandon cleanup | `pipeline/pos_filter.py` (optional; `--no-pos-filter` skips) |
| Emit | `data/events.jsonl` |

**Flags**

```bash
python -m pipeline.detect --root .                 # Re-ID on, softer POS filter
python -m pipeline.detect --root . --no-pos-filter # all abandons kept (matches commit)
python -m pipeline.detect --root . --no-reid       # per-track VIS IDs only
```

**Requires:** `../CCTV Footage/CAM 1.mp4` … `CAM 5.mp4` and `pip install -r requirements.txt`.

## API

| Method | Path |
|--------|------|
| GET | `/health` |
| POST | `/events/ingest` |
| GET | `/stores/{id}/metrics?date=` |
| GET | `/stores/{id}/funnel?date=` |
| GET | `/stores/{id}/heatmap?date=` |
| GET | `/stores/{id}/anomalies?date=` |
| GET | `/dashboard` |

Store IDs: `ST1008` and alias `STORE_BLR_002`. Sample date: `2026-04-10`.

## Intelligence layer (my rules)

- **Sessions:** `app/sessions.py` — staff excluded; REENTRY does not double ENTRY in funnel.
- **Conversion:** each of 24 POS rows converts **at most one** visitor (closest billing event in the 5‑minute window before txn).
- **Metrics:** compute-on-read from SQLite — no hardcoded counts.

## Documentation

| Doc | Path |
|-----|------|
| Design | [docs/DESIGN.md](docs/DESIGN.md) |
| Choices | [docs/CHOICES.md](docs/CHOICES.md) |
| Deploy / live URL | [docs/DEPLOY.md](docs/DEPLOY.md) |
| Submit checklist | [docs/SUBMISSION-CHECKLIST.md](docs/SUBMISSION-CHECKLIST.md) |
| Context | [docs/context/README.md](docs/context/README.md) |

## Status

Phases 1–3 + Part E dashboard complete. See [docs/SUBMISSION-CHECKLIST.md](docs/SUBMISSION-CHECKLIST.md).
