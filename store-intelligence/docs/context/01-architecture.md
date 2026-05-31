# Architecture & Repo Structure

> Part of [Project Context Index](./README.md)

---

## 2. System Architecture (What You Build)

### Stage 1 — Detection Layer (30 pts)

Process CCTV clips to produce structured behavioural events.

**Your choices:** YOLOv8/v9, RT-DETR, MediaPipe, ByteTrack, DeepSORT, Re-ID models, VLMs for zone/staff classification, etc.

**Responsibilities:**
- Detect people
- Track movement across frames/cameras
- Determine direction (entry vs exit)
- Assign per-session `visitor_id` (Re-ID token)
- Classify staff vs customers
- Handle edge cases (groups, re-entry, occlusion, empty periods)

**Output:** Structured events (see schema below)

---

### Stage 2 — Event Stream

Define event schema and emit events from detection into an ingest pipeline.

**Constraint:** Schema must support all analytics queries in the API layer.

---

### Stage 3 — Intelligence API (35 pts)

REST API that ingests events, computes real-time metrics, detects anomalies.

**Must run via:** `docker compose up` (no manual steps beyond git clone)

| Endpoint | Purpose | Key Requirements |
|----------|---------|------------------|
| `POST /events/ingest` | Accept batches (≤500 events) | Idempotent by `event_id`; partial success on malformed events; structured errors |
| `GET /stores/{id}/metrics` | Today's analytics | Unique visitors, conversion rate, avg dwell per zone, queue depth, abandonment rate; exclude `is_staff=true`; handle zero-purchase stores; real-time |
| `GET /stores/{id}/funnel` | Conversion funnel | Entry → Zone Visit → Billing Queue → Purchase; session-based; no double-counting on re-entry |
| `GET /stores/{id}/heatmap` | Zone visit frequency + avg dwell | Normalised 0–100; `data_confidence` flag if <20 sessions |
| `GET /stores/{id}/anomalies` | Active anomalies | Queue spike, conversion drop vs 7-day avg, dead zone; severity INFO/WARN/CRITICAL; `suggested_action` per anomaly |
| `GET /health` | Service status | Last event timestamp per store; `STALE_FEED` warning if >10 min lag |

---

### Stage 4 — Live Dashboard (+10 bonus pts)

Show **at least one metric updating in real time** as events flow from the detection layer.

- Terminal dashboard (rich/curses) is acceptable
- Web UI scores higher
- Proves pipeline + API are genuinely connected (not just batch replay)

---

## 11. Suggested Repository Structure

```
/store-intelligence/
├── data/
│   ├── pos_transactions.csv       # Derived from Brigade CSV (24 rows)
│   ├── store_layout.json          # Zone + camera definitions
│   └── sample_events.jsonl        # Optional: schema validation examples
├── pipeline/
│   ├── detect.py                  # Main detection + tracking script
│   ├── tracker.py                 # Re-ID / tracking logic
│   ├── zones.py                   # Zone polygon / line-crossing logic
│   ├── emit.py                    # Event schema + JSONL emission
│   ├── staff.py                   # Staff classification (uniform/heuristic)
│   └── run.sh                     # One command: all clips → events.jsonl
├── app/
│   ├── main.py                    # FastAPI entrypoint + routes
│   ├── models.py                  # Pydantic event + API response schemas
│   ├── ingestion.py               # Ingest, validate, dedup by event_id
│   ├── sessions.py                # Session builder from event stream
│   ├── metrics.py                 # /metrics computation
│   ├── funnel.py                  # /funnel session logic
│   ├── heatmap.py                 # /heatmap normalization
│   ├── anomalies.py               # Anomaly detection rules
│   ├── health.py                  # /health + STALE_FEED
│   ├── pos.py                     # POS load + conversion correlation
│   ├── db.py                      # Database connection + migrations
│   └── logging_config.py          # Structured JSON logging
├── dashboard/
│   └── live.py                    # Optional: terminal or web live metric
├── tests/
│   ├── conftest.py                # Fixtures: test DB, sample events
│   ├── test_ingest.py             # PROMPT block required
│   ├── test_metrics.py
│   ├── test_funnel.py
│   ├── test_anomalies.py
│   ├── test_pipeline.py
│   └── test_health.py
├── docs/
│   ├── DESIGN.md                  # >250 words, AI-Assisted Decisions section
│   └── CHOICES.md                 # 3 decisions, >250 words
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── pyproject.toml                 # Optional: pytest + coverage config
└── README.md                      # ≤5 commands to run everything
```

Structure is a **suggestion** — deviation is fine if explained in `DESIGN.md`.

---

## 16. Business Questions → API Mapping

| Business Question | Where Your System Answers |
|-------------------|---------------------------|
| How many customers visited today and how many bought? | Detection accuracy + `/metrics` `conversion_rate` |
| Where in the store are we losing customers? | `/funnel` drop-off % by stage |
| Which product zones get attention but not sales? | `/heatmap` dwell vs `/funnel` billing stage |
| Is there a queue building right now? | `/anomalies` `BILLING_QUEUE_SPIKE` |
| Is conversion worse than usual today? | `/anomalies` `CONVERSION_DROP` |
| Is any camera or store feed stale? | `/health` `STALE_FEED` warning |

---
