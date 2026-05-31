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
| — | `scripts/` (ingest, validate, verify), `scripts/dev/` (layout one-offs), `assertions.py`, `dashboard/live.py` (stub), `requirements-api.txt`, `Dockerfile` | Ops/validation; Part E dashboard not implemented |
| — | Repo root: `CONTEXT.md`, Brigade CSV/XLSX/PDFs, `CCTV Footage/` | Footage **gitignored** (~650 MB); paths in `data/store_layout.json` point to `../CCTV Footage/` |

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
                                    (optional) live dashboard
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

**Outputs:** `data/events.jsonl` (~280+ events, all 8 types). Timestamps use `clip_base_timestamp` aligned to POS window (`19:52` UTC); on-screen CCTV overlay reads `~20:10` (documented recorder skew in `store_layout.json`).

**Cross-camera:** `visitor_id` assigned per clip (`VIS_{cam}_{track_id}_{suffix}`); no embedding Re-ID across cameras in v1.

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

**Verification scripts:** `scripts/validate_project.py`, `scripts/verify_phase2.py`, `pytest` (22 tests, ~90% `app/` coverage).

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

## 9. Known Limitations & Future Work

| Limitation | Mitigation / next step |
|------------|------------------------|
| Cross-camera Re-ID | Global `VIS_####` IDs assigned in clip order across cameras; ENTRY on first customer detection per track |
| Timestamp base | `19:52 UTC` in layout for POS overlap; overlay `20:10` preserved as metadata |
| Single store, single day in POS | Snapshots table seeds 7-day baseline; more days as pipeline replays |
| Sample events ≠ full clip coverage | Conversion rate 0 until real billing timestamps align with POS windows |
| SQLite write throughput | First bottleneck at ~40 stores; would shard by `store_id` or move to PostgreSQL |
| Re-ID across CAM 3 → CAM 1 | Planned ByteTrack + optional embedding; document failures in follow-up video |
| `CAM_STAFF_BACK_01` | Events ingested but excluded in `customer_sessions()` |

**Follow-up video notes:** Be ready to demo `apply_pos_conversions()`, `unique_visitors_with_entry()`, and show CHOICES.md camera correction with `data/layout/cctv_annotated/` frames.

---

*Last updated: Phase 3 complete — pipeline emits `data/events.jsonl` from CCTV.*
