# Submission checklist

Architecture: [DESIGN.md §9](./DESIGN.md#9-implementation-notes--faq) · Demo: [DEPLOY.md](./DEPLOY.md)

## Demo for reviewers (live + local fallback)

### Option A — Live (try first)

| Link | URL |
|------|-----|
| **Dashboard** | https://purplle-round-2-hack.onrender.com/dashboard |
| API docs | https://purplle-round-2-hack.onrender.com/docs |

1. Open dashboard (may take ~30–60s if Render was idle).
2. Click **Live replay** → expect **~71** visitors, **~1.41%** conversion.

### Option B — Local (if live fails)

```bash
git clone git@github.com:HimanshuB474/Purplle-Round-2-Hack.git
cd Purplle-Round-2-Hack/store-intelligence
docker compose up -d --build
python scripts/ingest_events.py
```

| Link | URL |
|------|-----|
| **Dashboard** | http://localhost:8000/dashboard |
| API docs | http://localhost:8000/docs |
| Metrics | http://localhost:8000/stores/ST1008/metrics?date=2026-04-10 |

Same expected metrics as Option A after ingest.

## Acceptance gate

| # | Requirement | Status |
|---|-------------|--------|
| 1 | `docker compose up` | ✅ 71 visitors, 1.41% conversion after ingest |
| 2 | `/metrics` valid | ✅ local + Render |
| 3 | Pipeline → `events.jsonl` | ✅ 390 events, all 8 types (2 abandons) |
| 4 | `DESIGN.md` + `CHOICES.md` | ✅ |
| 5 | Stable execution | ✅ 48 pytest tests |
| 6 | Live dashboard (Part E) | ✅ Render + local `/dashboard` |

## Validation (local, from `store-intelligence/`)

```bash
pytest -q
python scripts/validate_part_ab.py   # 20/20
python scripts/validate_part_bc.py   # 40/40
python scripts/verify_docker.py
```

## Admin

- [ ] Submit **GitHub:** https://github.com/HimanshuB474/Purplle-Round-2-Hack
- [ ] Submit **live demo:** https://purplle-round-2-hack.onrender.com/dashboard
- [ ] Note **local fallback** in submission text (see [DEPLOY.md](./DEPLOY.md))
- [ ] Invite reviewers on private repo

## Not in git (local only)

- `CCTV Footage/*.mp4`, challenge PDFs/CSV/XLSX
- `*.db`, `.pytest_cache/`, `yolov8n.pt`
