# Overview & Scoring

> Part of [Project Context Index](./README.md)

---

# Purplle Tech Challenge 2026 — Round 2: Project Context

> **Purpose:** **Single source of truth** for the entire implementation — challenge requirements, local data, API contracts, business logic, and AI-engineering deliverables. Use this document to derive Cursor rules (`.cursor/rules/*.mdc`) and to drive end-to-end implementation without re-reading the PDFs.

## How to Use These Docs

| Audience | Usage |
|----------|-------|
| **You (developer)** | Start at [README.md](./README.md), then follow [10-implementation-guide.md](./10-implementation-guide.md) phases |
| **Cursor rules** | See [`.cursor/rules/`](../../../.cursor/rules/) — each rule points to a context doc |
| **DESIGN.md / CHOICES.md** | Templates in [08-ai-engineering.md](./08-ai-engineering.md); fill [`../DESIGN.md`](../DESIGN.md) and [`../CHOICES.md`](../CHOICES.md) |
| **Tests** | Implement every case in [09-testing.md](./09-testing.md) |
| **Self-check before submit** | [10-implementation-guide.md §19–20](./10-implementation-guide.md) |

### Canonical Project Decisions (lock these early)

| Decision | Recommended Value | Rationale |
|----------|-------------------|-----------|
| **Primary store ID** | `ST1008` | Matches local POS + CCTV data; alias `STORE_BLR_002` in docs if needed for acceptance gate example URL |
| **API store route ID** | `ST1008` | Use consistently in events, POS, and `/stores/ST1008/*` — OR support both IDs mapping to same store |
| **Reference date** | `2026-04-10` | POS + CCTV alignment |
| **Timezone** | UTC (`Z` suffix) | All timestamps ISO-8601 UTC |
| **Language** | Python 3.11+ | FastAPI scoring harness compatibility |
| **API framework** | FastAPI | Recommended by problem statement |
| **Storage** | SQLite (dev) / PostgreSQL (prod-ready) | Document choice in CHOICES.md |
| **POS basket field** | `sum(total_amount)` per invoice | Not GMV/NMV |
| **Conversion window** | 5 minutes before transaction | Per problem statement |
| **Billing zone ID** | `BILLING` | Required for funnel stage 3 + POS correlation |

---

## Document Index

See [README.md](./README.md) for the full map. Key files:

| # | Doc | Topic |
|---|-----|-------|
| 01 | [architecture](./01-architecture.md) | System stages, repo layout |
| 02 | [event-schema](./02-event-schema.md) | 8 event types, validation |
| 03 | [data-inventory](./03-data-inventory.md) | POS, CCTV, layout |
| 04 | [pos-business-logic](./04-pos-and-business-logic.md) | Conversion, sessions |
| 05 | [api-contracts](./05-api-contracts.md) | REST endpoints |
| 06 | [detection-pipeline](./06-detection-pipeline.md) | CV pipeline |
| 07 | [production-ops](./07-production-and-ops.md) | Docker, logging |
| 08 | [ai-engineering](./08-ai-engineering.md) | Part D deliverables |
| 09 | [testing](./09-testing.md) | Test matrix |
| 10 | [implementation-guide](./10-implementation-guide.md) | Build order, submit |

---

## 1. Executive Summary

You are building an **end-to-end Store Intelligence system** for **Apex Retail** — a specialty retail chain with 40 physical stores but no offline analytics (unlike their mature online channel).

**Input:** Raw anonymised CCTV footage  
**Output:** A containerised **Store Intelligence API** with live metrics  
**North Star Metric:** **Offline Store Conversion Rate**

```
Conversion Rate = Visitors who completed a purchase ÷ Total unique visitors (session window)
```

This is **not** a model-building-only exercise. You must design and implement the full pipeline:

```
📹 Raw CCTV → 🔍 Detection Layer → ⚡ Event Stream → 🧠 Intelligence API → 📊 Live Dashboard
```

| Attribute | Detail |
|-----------|--------|
| Format | Take-home, work independently within the window |
| AI Policy | Fully open-book — all AI tools permitted and **expected** |
| Submission | Git repo + `DESIGN.md` + `CHOICES.md` |
| Scoring | Automated tests + contextual follow-up video (5 questions, 30 min async) |
| Window | 48 hours from dataset download confirmation email |

---

## 7. Scoring Breakdown (100 + 10 bonus)

| Part | Dimension | Points |
|------|-----------|--------|
| **A** | Entry/exit count accuracy vs ground truth | 10 |
| **A** | Staff exclusion, re-entry, group handling | 10 |
| **A** | Schema compliance and event quality | 10 |
| **B** | API endpoint correctness (held-out event set) | 20 |
| **B** | Funnel accuracy and session deduplication | 10 |
| **B** | Anomaly detection correctness | 5 |
| **C** | Containerisation + README (acceptance gate) | 5 |
| **C** | Structured logs + health endpoint | 5 |
| **C** | Test coverage and edge case handling | 10 |
| **D** | AI usage depth (prompts, DESIGN.md, CHOICES.md) | 15 |
| **E** | Live dashboard bonus | +10 |
| | **Total (without bonus)** | **100** |

### Evaluation Philosophy (from Assessment Framework)

- **Functional correctness** over theoretical completeness
- **Engineering judgment** over model complexity
- **Clarity of reasoning** over volume of implementation
- Perfect detection is **not** expected — reasonable assumptions and edge-case handling matter more

### Score Interpretation

| Score | Interpretation |
|-------|----------------|
| 85+ | Strong candidate |
| 70–85 | Suitable for interview |
| 60–70 | Above average |

**Integrity caps:** Hardcoded outputs, non-varying outputs, or lack of real computation → score capped at **50**.

---

## 8. Acceptance Gate (Mandatory — Must Pass Before Scoring)

| # | Requirement |
|---|-------------|
| 1 | `docker compose up` starts the API (no manual steps beyond git clone) |
| 2 | README explains how to run detection pipeline against clips |
| 3 | `POST /events/ingest` accepts events without 5xx |
| 4 | `GET /stores/ST1008/metrics` returns valid JSON (also accept `STORE_BLR_002` if aliased) |
| 5 | `DESIGN.md` and `CHOICES.md` exist and are non-trivial (>250 words each) |

Failure → 12-hour fix window before scoring begins.

---

## 22. Key FAQs

| Question | Answer |
|----------|--------|
| Must use Python? | No, but recommended. FastAPI has best scoring harness coverage. |
| Which detection model? | Your choice — reasoning matters, not the specific model. |
| Can use VLM? | Yes — document in DESIGN.md. |
| Storage engine? | Your choice (SQLite fine). Document in CHOICES.md. |
| Imperfect detection OK? | Yes — handle uncertainty and edge cases well. |
| Batch vs streaming? | Batch OK; real-time/simulated needed for dashboard bonus. |
| Can't finish all parts? | Parts A + B weighted most heavily. |

### README — Required Commands (≤5)

Document exactly these steps:

```bash
git clone <repo> && cd store-intelligence
docker compose up -d --build
python pipeline/run.sh                    # process CCTV → data/events.jsonl
curl -X POST localhost:8000/events/ingest -H "Content-Type: application/json" -d "{\"events\": $(cat data/events.jsonl | jq -s '.')}"
curl http://localhost:8000/stores/ST1008/metrics
```

---

## 23. Contact & Timing

- **Questions:** hiring-challenge@[company].com
- **Response SLA:** 4 hours (10am–7pm IST, Mon–Sat)
- **48-hour window** starts at dataset download confirmation email timestamp

---
