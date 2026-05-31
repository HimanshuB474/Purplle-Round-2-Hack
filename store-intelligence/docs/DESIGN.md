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
| `docs/DESIGN.md`, `CHOICES.md` | Same + `docs/context/` (split from `CONTEXT.md`), `PRE-PHASE3-CHECKLIST.md` | Context index for development; not required for scoring |
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

**Outputs:** `data/events.jsonl` — **302 events**, **7 of 8** event types (see §9.2). Timestamps use `clip_base_timestamp` aligned to POS window (`19:52` UTC); on-screen CCTV overlay reads `~20:10` (documented recorder skew in `store_layout.json`).

**Visitor IDs:** `VIS_####` from `pipeline/tracker.new_visitor_id()` — a **monotonic counter** (`visitor_seq`) shared across clips in run order. Each new ByteTrack ID gets a new `VIS_####`. This is **not** cross-camera Re-ID (§9.1).

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

**POS correlation (`app/sessions.py` + `app/pos.py`):** Load `pos_transactions.csv`; for each transaction at time `T`, mark non-staff sessions with a billing-zone event in `[T−5min, T]` as `converted`. `unique_visitors` = distinct `visitor_id` with `ENTRY` (staff entries excluded). `abandonment_rate` = sessions with `BILLING_QUEUE_ABANDON` ÷ sessions that reached billing.

**Funnel:** Four stages—`ENTRY` → `ZONE_VISIT` → `BILLING_QUEUE` → `PURCHASE`. ENTRY counts **unique visitors**; later stages count visitors (subset of entrants) so REENTRY does not double ENTRY and counts stay monotonic. Implemented in `funnel_counts()`.

**Store alias:** `STORE_BLR_002` maps to canonical `ST1008` (`app/stores.py`) for acceptance-gate URLs.

## 7. Deployment & Observability

**Docker:** `docker-compose.yml` builds the API image, mounts `./data`, exposes port 8000, healthcheck on `/health`. CCTV clips stay at repo root (`../CCTV Footage/`) for pipeline runs on the host.

**Logging:** `RequestLoggingMiddleware` emits one JSON line per request: `trace_id`, `store_id`, `endpoint`, `latency_ms`, `status_code`, `timestamp`.

**Health (`GET /health`):** Returns `version`, per-store `last_event_at`, `lag_seconds`, `feed_status`. `STALE_FEED` if last event &gt; 10 minutes ago; HTTP 503 if DB unavailable. Root `GET /` lists endpoint URLs for browser sanity.

**Verification scripts:** `scripts/validate_part_ab.py`, `scripts/validate_part_bc.py`, `scripts/verify_docker.py`, `pytest` (40 tests, high `app/` coverage).

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

## 9. Known Gaps & Reviewer FAQ

These are **intentional v1 trade-offs**, documented for scoring transparency. They do not block the acceptance gate when `sample_events.jsonl` + committed `events.jsonl` + Docker API are used as intended.

### 9.1 No cross-camera Re-ID

| What we do | What we do **not** do |
|------------|------------------------|
| ByteTrack `track_id` per clip; new tracks → new `VIS_####` via shared `visitor_seq` in `pipeline/detect.py` | Embedding / appearance Re-ID to merge the same person across `CAM_ENTRY_01` → `CAM_FLOOR_*` |
| `ENTRY` on first customer detection for that track on the entry camera | Guarantee one `visitor_id` per physical shopper for the whole store visit |

**Impact:** Funnel and `unique_visitors` count **track identities**, not ground-truth humans. A shopper seen on CAM 3 (entry) and later on CAM 1 may appear as two visitors unless tracks are manually merged.

**Code:** `pipeline/tracker.py` (`new_visitor_id`), `pipeline/detect.py` (`visitor_seq` passed across clips). **Next step:** OSNet / CLIP Re-ID graph across cameras; document failure cases in follow-up video.

### 9.2 `BILLING_QUEUE_ABANDON` absent from `events.jsonl`

| File | Events | `BILLING_QUEUE_ABANDON` |
|------|--------|-------------------------|
| `data/events.jsonl` (pipeline output, committed) | 302 | **0** — removed or never emitted after POS filter |
| `data/sample_events.jsonl` (CI / schema demo) | 24 | **1** — all **8** types present |

**Why:** `pipeline/pos_filter.filter_false_billing_abandons()` drops `BILLING_QUEUE_ABANDON` when the visitor had billing-zone activity in the **5-minute window before** a POS transaction (`app/pos.conversion_window_start`). On Brigade 2026-04-10, correlated abandons were treated as false positives (converted shoppers leaving the queue).

**API impact:** `abandonment_rate` from pipeline-only ingest may be **0**; queue-spike anomalies still use `BILLING_QUEUE_JOIN` + `metadata.queue_depth`. Validators use `sample_events.jsonl` where abandon coverage is required (`tests/test_pipeline.py`, `validate_part_ab.py`).

**Code:** `pipeline/pos_filter.py`, `app/sessions.abandonment_rate()`.

### 9.3 Conversion rate is a heuristic (not ground truth)

**Definition (implemented):** `converted_visitors / unique_visitors` where conversion = non-staff session with billing-zone evidence in `[T−5min, T]` for some POS row on that date (`app/sessions.apply_pos_conversions()` + `app/pos.py`).

**Caveats:**

- POS has **no `customer_id`** — time + zone proxy only; multiple visitors near one txn can correlate incorrectly.
- Clip timestamps aligned to **19:52 UTC** base; CCTV on-screen clock ~**20:10** (metadata in `store_layout.json`).
- Billing camera coverage and queue polygons affect whether “billing presence” is detected.

**Impact:** Reported conversion (~10% after full ingest in dev) is **honest to our rules**, not a claim of match to Purplle’s hidden evaluation labels.

### 9.4 Part E live dashboard (implemented)

**URL:** `http://localhost:8000/dashboard` (same port as API; included in Docker image).

| Piece | Role |
|-------|------|
| `dashboard/static/index.html` | Web UI — metrics cards, funnel bars, replay progress |
| `app/dashboard.py` | Routes: page, `/dashboard/api/snapshot`, replay start/stop |
| `app/dashboard_replay.py` | Streams `data/events.jsonl` into `ingest_raw_events()` in batches |
| `dashboard/live.py` | CLI to open browser (`python dashboard/live.py`) |

**Live demo flow:** Click **Live replay** → clears events for `2026-04-10` (optional reset) → ingests ~12 events every 600 ms → **unique visitors**, **conversion %**, and funnel counts update on each poll (~500 ms during replay).

This satisfies Part E: metrics change in real time as the event stream flows, without batch-only `scripts/ingest_events.py` (though that script still works for one-shot ingest).

### 9.5 Other limitations (brief)

| Topic | Note |
|-------|------|
| Timestamp base | `19:52 UTC` in layout for POS overlap; overlay `20:10` in metadata |
| Single store / day in POS | 24 transactions; 7-day baseline seeded on metrics read for `CONVERSION_DROP` |
| SQLite scale | First bottleneck ~40 stores → PostgreSQL or shard by `store_id` |
| `CAM_STAFF_BACK_01` | Staff events ingested; excluded in `customer_sessions()` |

**Follow-up video:** Demo `apply_pos_conversions()`, `unique_visitors_with_entry()`, `funnel_counts()`, CHOICES Decision 1 (camera map), and §9.1–9.2 above with real `event_type` counts.

---

*Last updated: submission — gaps §9.1–9.4 explicit for reviewers.*
