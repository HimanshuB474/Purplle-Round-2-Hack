# Engineering Choices

> **Submission deliverable.** Updated through Phase 3 (May 2026).

---

## Decision 1: Detection Model Selection

### Context

Phase 3 must turn five Brigade CCTV clips (~2–2.5 min, 1080p, 25–29.97 fps) into schema-valid JSONL events: person boxes, stable tracks, entry/exit, zone dwell, staff vs customer, and billing queue depth. Billing occlusion and overlapping tracks at the glass doors are the highest-risk scenes.

### Options Considered

| Option | Pros | Cons |
|--------|------|------|
| **YOLOv8n + ByteTrack** | Fast on CPU/GPU; good person class; ByteTrack handles occlusions reasonably | Needs tuning for crowded entry; no built-in Re-ID across cameras |
| **RT-DETR + DeepSORT** | Strong accuracy on small objects | Heavier; slower for hackathon iteration on 5 full clips |
| **MediaPipe Pose** | Lightweight | Weak for crowd counting and queue depth |
| **VLM (GPT-4V / Claude vision) per frame** | Could label zones/staff semantically | Expensive, slow, non-deterministic timestamps; poor for 4k+ frames per clip |

### What AI Suggested

Use **YOLOv8n + ByteTrack** for the baseline pipeline, polygons from `store_layout.json` for zones, and optional VLM only to **propose** polygon coordinates from a single annotated frame—not for per-frame inference. AI also suggested classifying staff by uniform colour histogram in HSV space on upper-body crop.

### What I Chose

**YOLOv8n + ByteTrack**, **0.33 s sampling**, zone debounce, track-loss EXIT/REENTRY, global `VIS_####` IDs, timestamp base **19:52 UTC** (POS-aligned; overlay `20:10` in layout metadata).

### Why

~302 events in **~11 min** on CPU. All **8 event types** in `sample_events.jsonl`; live clip may omit `BILLING_QUEUE_ABANDON` after POS correlation filter. Staff via **HOG fallback** on CAM 4 (`32` staff-tagged events). Events emit `store_id: STORE_BLR_002`. Dwell threshold **30 s** per spec. **POS conversion ~10.7%** after ingest with honest billing-zone correlation.

### If I Used a VLM

- **Evaluation only:** single-frame camera-role prompt — used in Phase 1 to fix CAM3=ENTRY; not in runtime pipeline.

---

## Decision 2: Event Schema Design

### Context

Downstream API must answer metrics, funnel, heatmap, and anomalies without re-parsing video. Events are the contract between `pipeline/emit.py` and `POST /events/ingest`.

### Options Considered

| Approach | Pros | Cons |
|----------|------|------|
| **Flat 8-type catalogue (challenge schema)** | Matches rubric and `app/models.StoreEvent` | More emit logic in pipeline |
| **Hierarchical session document per visitor** | Fewer rows | Harder to ingest incrementally and dedupe |
| **Drop low-confidence events** | Cleaner metrics | Violates spec; hides detection failures |
| **Generic ZONE only (no BILLING_QUEUE_*)** | Simpler | Cannot compute `abandonment_rate` or queue-spike anomalies |

### What AI Suggested

Adopt the challenge’s eight types verbatim; never filter on `confidence`; use `BILLING_QUEUE_JOIN` with `metadata.queue_depth` and `BILLING_QUEUE_ABANDON` when a visitor leaves billing without a POS match within five minutes.

### What I Chose

**Full eight-type flat schema** in `app/models.py`, persisted as rows in SQLite. `sample_events.jsonl` (24 events) covers every type for CI. `zone_id` null only for ENTRY/EXIT/REENTRY. `session_seq` in metadata for debugging session boundaries.

### Why

`app/anomalies.detect_queue_spike()` depends on `queue_depth` on join events. `app/sessions.abandonment_rate()` depends on explicit `BILLING_QUEUE_ABANDON`. Funnel PURCHASE stage is derived from POS correlation, not a separate `PURCHASE` event type—keeping the stream aligned with physical CCTV evidence. Partial ingest validation per event (not whole-batch Pydantic) allows pipeline batches with a few bad rows without losing the whole clip.

---

## Decision 3: API Architecture Choice

### Context

Phase 2 acceptance gate: six REST endpoints, idempotent ingest, real computation (no hardcoded metrics), Docker-ready API. Must support `ST1008` and alias `STORE_BLR_002`.

### Options Considered

| Option | Pros | Cons |
|--------|------|------|
| **SQLite + compute-on-read** | Zero extra services; easy pytest with tmp DB; honest dynamic metrics | Heavier read path as event volume grows |
| **PostgreSQL + materialized views** | Fast dashboards at scale | Overkill for one store / hackathon Docker |
| **Redis cache of metrics** | Low latency reads | Invalidation complexity after ingest; two systems to fail |
| **207 Multi-Status on partial ingest** | HTTP-native partial success | Awkward for simple `curl` clients |

### What AI Suggested

SQLite for storage; compute metrics on GET; return **207** for partial ingest success; optional Redis later for 40-store scale.

### What I Chose

**SQLite** (`app/db.py`) with **compute-on-read** in `app/metrics.py`, `app/funnel.py`, `app/heatmap.py`, `app/anomalies.py`. Ingest returns **HTTP 200** with `{accepted, rejected, errors}`. Idempotency via primary key on `event_id`. Daily snapshots written on metrics read to support `CONVERSION_DROP` vs seven-day average in `app/anomalies.py`.

### Why

Meets “metrics change when events change” without a separate batch job. Tests use `tests/conftest.py` with a fresh SQLite file per test—no mocked math. For Brigade’s 24 POS rows and thousands of events per day, on-read is sufficient; first scale bottleneck at 40 stores would be **ingest write rate**, then read aggregation—documented in DESIGN.md §8. Rejected 207 because FastAPI TestClient and challenge examples expect JSON body tallies on 200; `tests/test_ingest.py` asserts partial success this way.

---

*Last updated: Phase 3 — staff HOG fallback, STORE_BLR_002 emit ID, 30 s dwell, POS abandon filter, structured ingest `event_count` logging.*
