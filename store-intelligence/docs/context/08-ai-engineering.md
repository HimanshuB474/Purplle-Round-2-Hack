# AI Engineering (Part D)

> Part of [Project Context Index](./README.md)  
> Submission templates live in [`../DESIGN.md`](../DESIGN.md) and [`../CHOICES.md`](../CHOICES.md).

---

## 10.1 Scoring Rubric for Part D (15 pts)

| Signal | Strong (full marks) | Weak (penalised) |
|--------|---------------------|------------------|
| **CHOICES.md** | 3 decisions with options considered, AI suggestion, your override + rationale | Generic filler, no personal reasoning |
| **DESIGN.md** | Clear architecture + 2–3 AI-assisted decisions with agree/disagree | Vague diagram, no AI section |
| **Test prompt blocks** | Every test file has `# PROMPT:` + `# CHANGES MADE:` showing iteration | Happy-path-only tests, no prompt history |
| **Detection model** | Model trade-offs documented; VLM prompts included if used | Unexplained default (e.g. "used YOLO because popular") |

---

## 10.2 Test File Prompt Block — REQUIRED FORMAT

Every file under `tests/` **must** start with this block:

```python
# PROMPT: <paste the exact prompt you gave the AI to generate this test file>
# CHANGES MADE: <what you edited, added, or rejected after AI generation — be specific>
#
# Example:
# PROMPT: "Write pytest tests for POST /events/ingest covering idempotency,
#          partial success on malformed events, and batch limit of 500."
# CHANGES MADE: Added test_ingest_duplicate_event_ids_returns_207_not_500;
#                fixed timestamp fixture to use 2026-04-10; removed AI's mock of
#                entire DB layer — replaced with in-memory SQLite fixture.
```

**Files requiring prompt blocks (minimum):**
- `tests/test_pipeline.py`
- `tests/test_metrics.py`
- `tests/test_funnel.py`
- `tests/test_anomalies.py`
- `tests/test_ingest.py`
- `tests/test_health.py`

---

## 10.3 DESIGN.md — REQUIRED OUTLINE (>250 words)

Create at `docs/DESIGN.md`. Use this exact section structure:

**Section 1 — Problem & North Star**
- Offline conversion rate for Apex Retail / Brigade Bangalore
- Why session-based analytics, not raw event counts

**Section 2 — System Overview**
- Pipeline diagram: CCTV → Detection → Event Stream → API → Dashboard
- Component list with one-line responsibility each

**Section 3 — Detection Pipeline Architecture**
- Model choice (detector, tracker, Re-ID approach)
- How entry/exit lines, zones, staff classification work
- Timestamp derivation: frame_index / fps + clip base time
- Cross-camera deduplication strategy

**Section 4 — Event Stream & Schema**
- Why this event_type catalogue
- How metadata fields (queue_depth, sku_zone, session_seq) are populated

**Section 5 — Intelligence API Architecture**
- Framework, storage, ingestion flow
- How metrics/funnel/anomalies are computed (real-time vs on-read)
- POS correlation: 5-minute billing window

**Section 6 — Deployment & Observability**
- docker compose services
- Structured logging fields
- Health check semantics

**Section 7 — AI-Assisted Decisions** ← REQUIRED SECTION TITLE

Document 2–3 decisions where an LLM influenced your design. For each:
- What AI suggested
- What you accepted or rejected
- Why

**Section 9 — Implementation Notes & FAQ** (in DESIGN.md)
- Operations and scale (e.g. multi-store)
- Re-ID, queue, and conversion behaviour

---

## 10.4 CHOICES.md — REQUIRED OUTLINE (>250 words)

Create at `docs/CHOICES.md`. **Exactly three decisions**, each using this template:

### Decision 1: Detection Model Selection

- **Context:** What problem this solves (people detection, tracking, staff vs customer)
- **Options Considered:** table with Option / Pros / Cons (YOLOv8+ByteTrack, RT-DETR+DeepSORT, MediaPipe, VLM)
- **What AI Suggested:** quote or paraphrase
- **What I Chose:** your final choice
- **Why:** specific to THIS store footage, not generic
- **If I Used a VLM:** prompt used + whether it worked

### Decision 2: Event Schema Design

- **Context:** Why structured events matter for downstream API
- **Options Considered:** flat vs hierarchical sessions; BILLING_QUEUE_* vs generic ZONE_ENTER; confidence filtering
- **What AI Suggested / What I Chose / Why**

### Decision 3: API Architecture Choice

- **Context:** Pick ONE — storage engine, real-time computation strategy, or idempotency approach
- **Options Considered:** SQLite+compute-on-read, PostgreSQL+materialized views, Redis cache
- **What AI Suggested / What I Chose / Why**

---

## 10.5 AI Usage Policy — Rewarded vs Penalised

| Rewarded | Penalised |
|----------|-----------|
| LLM evaluates detection model trade-offs → documented in CHOICES.md | Generic CHOICES.md with no personal reasoning |
| VLM for zone/staff classification → prompt in DESIGN.md | Tests only cover happy path |
| Iterate on detection based on AI feedback + your evaluation | Pipeline ignores all 7 edge cases |
| CHOICES.md shows where you **disagreed** with AI | CHOICES.md with no overrides or rationale |
| Prompt blocks show real iteration (CHANGES MADE is non-empty) | Hardcoded outputs / no real computation (score cap 50) |

---

## 10.6 Documentation Traceability Map

Update docs **as you code** — not at the end:

| Code Area | Update In |
|-----------|-----------|
| Model/tracker selection | CHOICES.md Decision 1 |
| Event types + metadata | CHOICES.md Decision 2 + DESIGN.md §4 |
| DB, caching, idempotency | CHOICES.md Decision 3 + DESIGN.md §5 |
| Zone polygons / camera mapping | DESIGN.md §3 + store_layout.json |
| VLM prompts (if any) | DESIGN.md §7 + CHOICES.md Decision 1 |
| Test generation | `# PROMPT:` block in each test file |
| Docker setup | DESIGN.md §6 + README.md |
| Implementation notes | DESIGN.md §9 |
