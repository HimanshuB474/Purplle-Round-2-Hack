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

**YOLOv8n + ByteTrack**, **0.5 s sampling** (`PIPELINE_SAMPLE_SEC`), zone debounce, track-loss EXIT/REENTRY, sequential `VIS_####` IDs (**not** cross-camera Re-ID — see [Limitations](#known-limitations-submission-transparency)), timestamp base **19:52 UTC** (POS-aligned; overlay `20:10` in layout metadata).

### Why

~302 events in **~11 min** on CPU. All **8 event types** in `sample_events.jsonl`; committed `events.jsonl` has **7 types** (no `BILLING_QUEUE_ABANDON` after `pipeline/pos_filter.py`). Staff via **HOG fallback** on CAM 4 (`32` staff-tagged events). Events emit `store_id: STORE_BLR_002`. Dwell threshold **30 s** per spec. **POS conversion ~10.7%** after ingest — heuristic per §Limitations below.

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

Meets “metrics change when events change” without a separate batch job. Tests use `tests/conftest.py` with a fresh SQLite file per test—no mocked math. For Brigade’s 24 POS rows and thousands of events per day, on-read is sufficient; first scale bottleneck at 40 stores would be **ingest write rate**, then read aggregation—documented in DESIGN.md §9.5. Rejected 207 because FastAPI TestClient and challenge examples expect JSON body tallies on 200; `tests/test_ingest.py` asserts partial success this way.

---

## Known limitations (submission transparency)

Aligned with [DESIGN.md §9](./DESIGN.md#9-known-gaps--reviewer-faq). Stated here so CHOICES alone answers “what did you knowingly not solve?”

### L1 — No cross-camera Re-ID

- **Choice:** One `visitor_id` per ByteTrack track; `visitor_seq` increments across clips in processing order (`VIS_0001`, `VIS_0002`, …).
- **Rejected:** Appearance embeddings to link CAM 3 entry with CAM 1/2 floor tracks.
- **Reviewer:** Do not expect a single `visitor_id` to follow one person across all five clips.

### L2 — `BILLING_QUEUE_ABANDON` only in `sample_events.jsonl`

- **Choice:** Post-pipeline `filter_false_billing_abandons()` removes abandons when POS correlation says the visitor converted within the 5‑min window.
- **Result:** `data/events.jsonl` = 302 events, **0** abandons; `data/sample_events.jsonl` = all 8 types for schema/CI.
- **Reviewer:** Validate abandon handling against **sample** file; use pipeline file for volume/realistic ingest.

### L3 — Conversion rate is time–zone heuristic

- **Choice:** Match POS timestamp to billing-zone events in `[T−5min, T]`; never join on customer name/phone from Brigade CSV.
- **Caveat:** May disagree with hidden evaluation labels; we report metrics consistent with **our** documented rules in `app/sessions.py`.

### L4 — Part E dashboard (web UI + replay)

- **Choice:** Single-page dashboard at `/dashboard` with polling snapshot API; background replay of `events.jsonl` via shared `ingest_raw_events()`.
- **Rejected:** Separate Node frontend or second container — keeps `docker compose up` one-service.
- **Reviewer:** Open `/dashboard` → **Live replay** → watch unique visitors and conversion rate climb.

---

*Last updated: submission — limitations L1–L4 explicit for reviewers.*
