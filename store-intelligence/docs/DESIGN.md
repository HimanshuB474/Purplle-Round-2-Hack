# Store Intelligence System — Design

> **Submission deliverable.** Updated through Phase 3 (May 2026).

## 1. Problem & North Star

Purplle’s offline stores need the same analytical rigour as online funnels. For **Brigade Bangalore (`ST1008`)** on **10 April 2026**, the north-star metric is:

**conversion_rate = converted_visitors ÷ unique_visitors**

where a visitor counts as converted if they had billing-zone presence in the **five minutes before** a POS transaction timestamp. POS carries no `customer_id` in the challenge contract—only store + time—so we deliberately never join on `customer_name` or `customer_number` from the Brigade CSV.

Analytics are **session-oriented**, not raw event counts: a group of three people produces three `ENTRY` events and three sessions; staff (`is_staff=true`) are excluded from all customer metrics; `REENTRY` must not inflate the funnel’s ENTRY stage. This matches how a store manager thinks about “how many people came in” versus “how many events fired.”

## 2. Repository Layout (vs §7.1 suggestion)

Git root is the **parent workspace** (`purple hack/`); the **submission tree** is `store-intelligence/`, matching the problem statement’s suggested `/store-intelligence/` root.

| §7.1 suggested | This repo | Notes |
|------------------|-----------|--------|
| `pipeline/detect.py`, `tracker.py`, `emit.py`, `run.sh` | Same + `zones.py`, `staff.py`, `staff_detect.py`, `pos_filter.py`, `config.py`, `run.py` | Zone polygons, staff tagging, POS abandon filter |
| `app/main.py` … `health.py` | Same + `heatmap.py`, `sessions.py`, `db.py`, `deps.py`, `pos.py`, `stores.py`, `config.py`, `logging_config.py` | Heatmap endpoint; shared session/POS helpers |
| `tests/test_pipeline.py`, `test_metrics.py`, `test_anomalies.py` | Same + `test_ingest`, `test_funnel`, `test_health`, `test_degradation`, `test_assertions`, `conftest.py` | Broader API + degradation coverage |
| `docs/DESIGN.md`, `CHOICES.md`, `SUBMISSION-CHECKLIST.md` | Same + `docs/context/` (dev reference) | Context index optional for reviewers |
| — | `scripts/`, `dashboard/static/`, `app/dashboard.py`, `app/dashboard_replay.py` | Ops/validation; **Part E** web UI at `/dashboard` |
| — | Repo root: `README.md`, `CONTEXT.md`; local CCTV + challenge PDFs/CSV | Footage and reference materials **gitignored**; committed `data/*` suffices for reviewers |

**Intentionally not moved:** CCTV clips and challenge PDFs stay at repo root for local pipeline runs; reviewers use committed `data/events.jsonl` + Docker API without re-running CV.

## 3. System Overview

```
CCTV clips (5 cams) ──► Detection pipeline (Phase 3) ──► events.jsonl
                                                          │
                                                          ▼
                                              POST /events/ingest
                                                          │
                     ┌────────────────────────────────────┼────────────────────┐
                     ▼                                    ▼                    ▼
              SQLite (events)                    pos_transactions.csv    store_layout.json
                     │                                    │                    │
                     └──────────────► FastAPI compute-on-read ◄─────────────────┘
                                           │
                     metrics / funnel / heatmap / anomalies / health
                                           │
                                    GET /dashboard (live UI + replay)
```

| Component | Responsibility |
|-----------|----------------|
| `pipeline/detect.py` | YOLOv8n + ByteTrack, zone/entry logic, writes `data/events.jsonl` |
| `data/store_layout.json` | Camera roles, polygons, `entry_line`, clip base timestamps |
| `data/pos_transactions.csv` | 24 invoices aggregated from Brigade line items |
| `app/ingestion.py` | Validate, dedupe by `event_id`, partial batch success |
| `app/sessions.py` | Session split, POS correlation, funnel helpers |
| `app/metrics.py` etc. | On-read analytics for a store + date |
| `scripts/validate_project.py` | Data/doc/API consistency checks |

## 4. Detection Pipeline Architecture

**Status: implemented** (`python -m pipeline.detect` or `pipeline/run.sh`).

| Setting | Value |
|---------|--------|
| Detector | YOLOv8n (`yolov8n.pt`) — COCO person class |
| Tracker | ByteTrack via `ultralytics` `.track(persist=True)` |
| Sample rate | 1 frame / 0.5 s per clip (`PIPELINE_SAMPLE_SEC`) |
| Zones | Centroid-in-polygon from `store_layout.json` |
| Entry | Line-cross at `entry_line` + polygon fallback on `CAM_ENTRY_01` |
| Staff | `is_staff=true` only on `CAM_STAFF_BACK_01` (no uniform heuristic on floor) |
| Zone exit debounce | 3 missed samples before `ZONE_EXIT` (reduces jitter) |
| Dwell | `ZONE_DWELL` every 30 s continuous presence |

**Cameras (verified 2026-05-31 on sample frames):**

| Clip | Role | `camera_id` |
|------|------|-------------|
| CAM 3.mp4 | ENTRY (glass doors) | `CAM_ENTRY_01` |
| CAM 1.mp4 | MAIN / skincare wall | `CAM_FLOOR_SKIN_01` |
| CAM 2.mp4 | MAIN / makeup–hair | `CAM_FLOOR_MAKEUP_01` |
| CAM 5.mp4 | BILLING | `CAM_BILLING_01` |
| CAM 4.mp4 | STAFF / back office | `CAM_STAFF_BACK_01` (excluded from customer metrics) |

**Outputs:** `data/events.jsonl` — **390 events**, **all 8** event types (2× `BILLING_QUEUE_ABANDON` in committed file; generated with `--no-pos-filter`). Timestamps use `clip_base_timestamp` at `19:52` UTC (overlay ~20:10 in layout metadata).

**Visitor IDs:** `VIS_####` via ByteTrack + `pipeline/reid.py` online registry (ENTRY cam first, 120s + HSV). Post-pass merge is **off** by default (`PIPELINE_REID_POST=0`) to avoid over-merging.

## 5. Event Stream & Schema

Eight `event_type` values (see `app/models.py`): `ENTRY`, `EXIT`, `ZONE_ENTER`, `ZONE_EXIT`, `ZONE_DWELL`, `BILLING_QUEUE_JOIN`, `BILLING_QUEUE_ABANDON`, `REENTRY`.

Design choices:

- **`zone_id` null only for ENTRY/EXIT/REENTRY** — keeps funnel and heatmap queries simple.
- **`dwell_ms`** — 0 for instantaneous events; `ZONE_DWELL` emitted every 30s of continuous presence (≥30000 ms).
- **`metadata.queue_depth`** — required on `BILLING_QUEUE_JOIN` for queue-spike anomalies.
- **`metadata.session_seq`** — monotonic per visitor session for debugging.
- **Low confidence is never dropped** — `confidence` flags uncertainty; ingest still persists the row.

## 6. Intelligence API Architecture

**Framework:** FastAPI 0.110+, Pydantic v2 models shared between ingest and tests.

**Storage:** SQLite (`data/store_intelligence.db` by default; overridable via `DATABASE_URL`). Table `events` keyed by `event_id` (UUID v4). Table `daily_metrics_snapshots` stores conversion rate per day for seven-day anomaly baseline.

**Ingestion (`app/ingestion.py`):** Accepts `{"events": [...]}` with max **500** events. Each event validated individually—malformed rows increment `rejected` with structured `errors[]`; valid rows persist. Duplicate `event_id` returns success without a second insert (idempotent). HTTP **200** with `{accepted, rejected, errors}` (partial success documented in CHOICES.md).

**Computation:** **Compute-on-read** for metrics, funnel, heatmap, and anomalies for a given `store_id` + `?date=YYYY-MM-DD`. No hardcoded visitor counts—outputs change when different events are ingested.

**POS correlation (`app/sessions.py` + `app/pos.py`):** For each POS row at time `T`, assign conversion to **at most one** non-staff session—the one whose latest billing event in `[T−5min, T]` is closest to `T`. `unique_visitors` = distinct `visitor_id` with `ENTRY` (staff excluded). `abandonment_rate` = sessions with `BILLING_QUEUE_ABANDON` ÷ sessions that reached billing.

**Funnel:** Four stages—`ENTRY` → `ZONE_VISIT` → `BILLING_QUEUE` → `PURCHASE`. ENTRY counts **unique visitors**; later stages count visitors (subset of entrants) so REENTRY does not double ENTRY and counts stay monotonic. Implemented in `funnel_counts()`.

**Store alias:** `STORE_BLR_002` maps to canonical `ST1008` (`app/stores.py`) for acceptance-gate URLs.

## 7. Deployment & Observability

**Docker:** `docker-compose.yml` builds the API image, mounts `./data`, exposes port 8000, healthcheck on `/health`. CCTV clips stay at repo root (`../CCTV Footage/`) for pipeline runs on the host.

**Logging:** `RequestLoggingMiddleware` emits one JSON line per request: `trace_id`, `store_id`, `endpoint`, `latency_ms`, `status_code`, `timestamp`.

**Health (`GET /health`):** Returns `version`, per-store `last_event_at`, `lag_seconds`, `feed_status`. `STALE_FEED` if last event &gt; 10 minutes ago; HTTP 503 if DB unavailable. Root `GET /` lists endpoint URLs for browser sanity.

**Verification scripts:** `scripts/validate_part_ab.py`, `scripts/validate_part_bc.py`, `scripts/verify_docker.py`, `pytest` (48 tests).

## 8. AI-Assisted Decisions

### Decision A: CCTV camera role assignment

- **What AI suggested:** Initial hypothesis—CAM 1 = ENTRY, CAM 2/3 = MAIN, CAM 4/5 = BILLING—based on filename order and floor-plan guess.
- **What I accepted/rejected:** **Rejected** after extracting sample frames and reading the Purplle F.O.H. plan. CAM 3 shows glass doors and BACKLIT display (ENTRY); CAM 1 is the skincare top wall; CAM 4 is back-office staff.
- **Why:** Wrong ENTRY camera would break entry-line logic and inflate or deflate `unique_visitors`. Verified mapping is canonical in `data/store_layout.json` and `docs/context/03b-store-layout-brigade-road.md`.

### Decision B: Funnel ENTRY counting with REENTRY

- **What AI suggested:** Session-count funnel (each `ENTRY`/`REENTRY` starts a session; count sessions per stage).
- **What I accepted/rejected:** **Rejected** for ENTRY stage—REENTRY created more ZONE_VISIT sessions than ENTRY visitors, breaking monotonic funnel tests. **Accepted** visitor-based counts per stage: ENTRY = unique visitors with `ENTRY`; later stages = visitors who reached that stage.
- **Why:** Matches spec (“REENTRY must not double-count visitor in ENTRY stage”) and `tests/test_funnel.py::test_funnel_monotonic_counts`. Code: `funnel_counts()` in `app/sessions.py`.

### Decision C: Ingest HTTP semantics for partial success

- **What AI suggested:** Either 207 Multi-Status or 200 with accepted/rejected tallies.
- **What I accepted/rejected:** **Accepted** 200 + body tallies; malformed events never fail the whole batch.
- **Why:** Simpler for `curl` and TestClient; pipeline can retry only failed indices. Documented in CHOICES.md Decision 3.

## 9. Implementation Notes & FAQ

Design choices for Re-ID, queue events, and conversion — how the committed pipeline and API behave end-to-end.

### 9.1 Cross-camera Re-ID

| Layer | Implementation |
|-------|----------------|
| **Online** | `pipeline/reid.py` — `CrossCameraRegistry` matches new floor tracks to entry-cam visitors within `REID_TIME_GAP_SEC` (120s) using HSV histogram correlation when `PIPELINE_REID_APPEARANCE=1`; merge only if the best score beats the runner-up by `REID_MIN_SCORE_GAP` (default 0.08) |
| **Post-pass** | Optional (`PIPELINE_REID_POST=1`) — unambiguous single-entry matches only |
| **Disable** | `python -m pipeline.detect --no-reid` |

**Committed run:** ~71 customer `visitor_id`s after online merge on five Brigade clips.

### 9.2 `BILLING_QUEUE_ABANDON`

| Source | Count |
|--------|-------|
| Committed `events.jsonl` | **2** (regen with `--no-pos-filter`) |
| Default pipeline + POS filter | May drop abandons correlated with a nearby transaction |
| `sample_events.jsonl` | 1 (CI) |

Emit logic: `BILLING_QUEUE_JOIN` after `BILLING_JOIN_MIN_SEC` in zone; `BILLING_QUEUE_ABANDON` on billing `ZONE_EXIT` only if `BILLING_ABANDON_MIN_SEC` elapsed since join (`pipeline/detect.py`). Optional cleanup: `pipeline/pos_filter.py`.

### 9.3 Conversion rate (one txn → one visitor)

**Definition:** `converted_visitors / unique_visitors` where each POS transaction converts **at most one** visitor — the session whose last billing event in `[T−5min, T]` is closest to `T` (`app/sessions.apply_pos_conversions()`).

**Assumptions:**

- POS rows have **no `customer_id`** — correlation uses billing-zone timestamps in a 5‑minute window before each transaction.
- Clip timestamps use **19:52 UTC** base (aligned to POS); CCTV on-screen clock ~**20:10** in `store_layout.json` metadata.
- Billing camera polygons and queue depth affect billing-stage detection.

**Verified (clean Docker):** `python scripts/ingest_events.py` → `unique_visitors=71`, `converted_visitors=1`, `conversion_rate=0.0141`, `abandonment_rate=0.25`; funnel ENTRY 71 → ZONE_VISIT 41 → BILLING_QUEUE 7 → PURCHASE 1.

### 9.4 Part E live dashboard (implemented)

| Environment | Dashboard URL |
|-------------|----------------|
| **Live (Render)** | https://purplle-round-2-hack.onrender.com/dashboard |
| **Local fallback** | http://localhost:8000/dashboard (`docker compose up` + `python scripts/ingest_events.py`) |

If Render is unavailable, reviewers can run the local path — same Part E UI and replay behaviour.

| Piece | Role |
|-------|------|
| `dashboard/static/index.html` | Web UI — metrics cards, funnel bars, replay progress |
| `app/dashboard.py` | Routes: page, `/dashboard/api/snapshot`, replay start/stop |
| `app/dashboard_replay.py` | Streams `data/events.jsonl` into `ingest_raw_events()` in batches |
| `dashboard/live.py` | CLI to open browser (`python dashboard/live.py`) |

**Live demo flow:** Click **Live replay** → clears events for `2026-04-10` → ingests ~12 events every 600 ms → **unique visitors**, **conversion %**, and funnel counts update on each poll (~500 ms during replay). On Render, use this after deploy if metrics are empty on first load.

Part E: metrics change in real time as the event stream flows. Local one-shot load: `python scripts/ingest_events.py`.

### 9.5 Operations & scale

| Topic | Note |
|-------|------|
| Timestamp base | `19:52 UTC` in layout for POS overlap; overlay `20:10` in metadata |
| Single store / day in POS | 24 transactions; 7-day baseline seeded on metrics read for `CONVERSION_DROP` |
| SQLite scale | Compute-on-read; at ~40 stores consider PostgreSQL or shard by `store_id` |
| `CAM_STAFF_BACK_01` | Staff events ingested; excluded in `customer_sessions()` |

---

*Last updated: submission — §9 documents pipeline behaviour for reviewers.*
