# Demo: live (Render) + local fallback

Same FastAPI app and dashboard in both environments. Use **live** for a quick click-through; use **local** if Render fails.

## Live (Render)

**Base:** https://purplle-round-2-hack.onrender.com

| Page | URL |
|------|-----|
| **Dashboard** | https://purplle-round-2-hack.onrender.com/dashboard |
| API docs | https://purplle-round-2-hack.onrender.com/docs |
| Health | https://purplle-round-2-hack.onrender.com/health |
| Metrics | https://purplle-round-2-hack.onrender.com/stores/ST1008/metrics?date=2026-04-10 |

### Reviewer steps (live)

1. Open the **dashboard** (wait up to ~60s if the service was idle).
2. Click **Live replay** to stream committed `data/events.jsonl` (390 events).
3. Confirm metrics: **~71** unique visitors, **~1.41%** conversion (`0.0141`).

### When live may fail

| Symptom | What to do |
|---------|------------|
| Page times out / “Application loading” | Wait and retry, or use **local fallback** below |
| Metrics show `0` visitors | Click **Live replay** on the dashboard |
| Service unavailable | Run **local Docker** — no Render account needed |

---

## Local fallback (Docker)

Works without CCTV footage — uses committed `data/events.jsonl`.

**Requires:** [Docker Desktop](https://www.docker.com/products/docker-desktop/) (or Docker Engine) + Git.

```bash
git clone git@github.com:HimanshuB474/Purplle-Round-2-Hack.git
cd Purplle-Round-2-Hack/store-intelligence

docker compose up -d --build
python scripts/ingest_events.py
```

| Page | URL |
|------|-----|
| **Dashboard** | http://localhost:8000/dashboard |
| API docs | http://localhost:8000/docs |
| Metrics | http://localhost:8000/stores/ST1008/metrics?date=2026-04-10 |

Optional: on the dashboard, click **Live replay** to watch metrics update in real time.

### Verify locally

```bash
pytest -q
python scripts/validate_part_ab.py   # 20/20
python scripts/validate_part_bc.py   # 40/40
python scripts/verify_docker.py
curl http://localhost:8000/health
```

Expected after `ingest_events.py`: `unique_visitors=71`, `conversion_rate=0.0141`.

---

## What is deployed / shipped

- Docker image: API + dashboard only (no YOLO on server)
- `data/events.jsonl` (390 events), POS CSV, `store_layout.json`
- Render: `AUTO_INGEST_ON_STARTUP=1` when enabled in build; else use **Live replay**

## Redeploy Render

1. [render.com](https://render.com) → service **purplle-round-2-hack**
2. Repo `HimanshuB474/Purplle-Round-2-Hack`, **Root Directory:** `store-intelligence`
3. Runtime **Docker**, health check `/health`, env from `render.yaml`

## Submission form (copy-paste)

```text
Live demo:  https://purplle-round-2-hack.onrender.com/dashboard
            (click "Live replay" if metrics are empty)

Local demo: clone repo → store-intelligence/README.md Quick Start
            docker compose up -d --build && python scripts/ingest_events.py
            → http://localhost:8000/dashboard

Repository: https://github.com/HimanshuB474/Purplle-Round-2-Hack
```
