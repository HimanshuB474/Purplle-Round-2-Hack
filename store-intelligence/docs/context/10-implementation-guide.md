# Implementation Guide & Submission

> Part of [Project Context Index](./README.md)

---

## 18. Implementation Phases & Done Criteria

Execute in order. Do **not** skip Phase 2 — passing acceptance gate early de-risks submission.

### Phase 1: Data Foundation

| Task | Output | Done When |
|------|--------|-----------|
| Aggregate POS CSV | `data/pos_transactions.csv` (24 rows) | Validates against Section 6 schema |
| Author store layout | `data/store_layout.json` | All 5 cameras mapped with roles + zones |
| Define Pydantic models | `app/models.py` | Event + all API response models validate |
| Sample events | `data/sample_events.jsonl` | ≥20 valid events covering all 8 event types |

### Phase 2: Intelligence API (acceptance gate)

| Task | Output | Done When |
|------|--------|-----------|
| FastAPI scaffold | `app/main.py` | All 6 endpoints respond |
| Ingest + dedup | `app/ingestion.py` | Idempotent, partial success works |
| Sessions + metrics + funnel | `app/sessions.py`, `metrics.py`, `funnel.py` | Edge cases pass (Section 17.2–17.3) |
| POS correlation | `app/pos.py` | 24 transactions load; conversion logic works |
| Heatmap + anomalies + health | respective modules | All response schemas match Section 12 |
| Docker | `docker-compose.yml` | `docker compose up` → API on port 8000 |
| README | 5 commands max | Clone → up → ingest → metrics |

**Gate check:** `GET /stores/ST1008/metrics` returns valid JSON; `POST /events/ingest` no 5xx.

### Phase 3: Detection Pipeline

| Task | Output | Done When |
|------|--------|-----------|
| Person detect + track | `pipeline/detect.py`, `tracker.py` | Runs on all 5 clips without crash |
| Zone + entry logic | `pipeline/zones.py` | ENTRY/EXIT/ZONE_* events emitted |
| Staff classification | `pipeline/staff.py` | `is_staff` populated |
| Event emission | `pipeline/emit.py`, `run.sh` | `data/events.jsonl` validates against schema |
| Edge cases | group entry, re-entry, low confidence | Document handling in CHOICES.md |

### Phase 4: Integration + Production

| Task | Output | Done When |
|------|--------|-----------|
| Pipeline → API ingest | README instructions | Full clip → events → metrics updates |
| Structured logging | `logging_config.py` | trace_id, store_id, endpoint, latency_ms logged |
| Test suite | `tests/*` | >70% coverage; all Section 17 cases pass |
| Prompt blocks | top of each test file | PROMPT + CHANGES MADE filled in |

### Phase 5: Documentation (Part D — do alongside coding)

| Task | Output | Done When |
|------|--------|-----------|
| DESIGN.md | `docs/DESIGN.md` | >250 words; §7 AI-Assisted Decisions filled |
| CHOICES.md | `docs/CHOICES.md` | 3 decisions with AI suggestion + your choice |
| Traceability | code ↔ docs | Section 10.6 map complete |

### Phase 6: Bonus (optional)

| Task | Done When |
|------|-----------|
| Live dashboard | Metric updates as events stream in |
| README notes dashboard URL | Reviewer can reproduce |

---

## 19. Pre-Submit Verification

Run this checklist manually before git push:

```bash
# 1. Clean start
docker compose down -v && docker compose up -d --build

# 2. Health
curl http://localhost:8000/health

# 3. Ingest pipeline output
curl -X POST http://localhost:8000/events/ingest -H "Content-Type: application/json" -d @data/events.jsonl

# 4. All endpoints
curl http://localhost:8000/stores/ST1008/metrics
curl http://localhost:8000/stores/ST1008/funnel
curl http://localhost:8000/stores/ST1008/heatmap
curl http://localhost:8000/stores/ST1008/anomalies

# 5. Tests + coverage
pytest --cov=app --cov-report=term-missing

# 6. Docs word count
wc -w docs/DESIGN.md docs/CHOICES.md   # each >250

# 7. Prompt blocks present
grep -l "PROMPT:" tests/test_*.py
```

**Integrity self-check (avoid score cap at 50):**
- [ ] Metrics change when different events are ingested
- [ ] Conversion rate derives from real POS + event correlation
- [ ] No hardcoded visitor counts in source
- [ ] Detection pipeline actually reads video files

---

## 20. Submission Checklist

- [ ] Git repository link (private; invite reviewer handle from challenge email)
- [ ] `docker compose up` confirmed on clean machine
- [ ] `README.md` — detection pipeline instructions
- [ ] `DESIGN.md` — includes "AI-Assisted Decisions" section
- [ ] `CHOICES.md` — model selection, schema design, one API decision
- [ ] Prompt blocks at top of each test file
- [ ] (Optional) Dashboard URL in README for Part E bonus

---

## 21. Post-Submission Follow-Up Prep

Record within **48 hours** — 5 questions, 30 min async video, ~2 min per answer.

**Prepare while building (write notes in DESIGN.md §8):**

| Likely Question Theme | What to Document Now |
|-----------------------|----------------------|
| Detection model struggles | What failed on billing occlusion; what you tried next |
| visitor_id / Re-ID edge cases | Same door, 3-second gap between different people |
| Scale at 40 stores | First bottleneck (DB writes? funnel compute? ingest lag?) |
| VLM vs rule-based zones | Exact prompt if used; why kept/rejected |
| Funnel accuracy trade-offs | How REENTRY dedup works in your code |

Generic answers fail — every answer must reference **your** CHOICES.md decisions and **your** function names.

---

## Appendix A: Suggested Cursor Rules (derive from this doc)

When creating `.cursor/rules/*.mdc`, split by concern:

| Rule File | `globs` | Key Instructions |
|-----------|---------|------------------|
| `project-context.mdc` | `alwaysApply: true` | North star metric; canonical IDs (ST1008); read CONTEXT.md |
| `event-schema.mdc` | `pipeline/**/*.py`, `app/models.py` | 8 event types; never drop low-confidence; UUID event_id |
| `api-contracts.mdc` | `app/**/*.py` | Section 12 response shapes; 503 on DB down; no stack traces |
| `business-logic.mdc` | `app/metrics.py`, `funnel.py`, `pos.py` | 5-min conversion window; exclude is_staff; session-based funnel |
| `tests-and-docs.mdc` | `tests/**`, `docs/**` | PROMPT/CHANGES blocks; >70% coverage; DESIGN.md + CHOICES.md templates |
| `data-layer.mdc` | `data/**`, `pipeline/run.sh` | POS aggregation; store_layout.json; 2026-04-10 timestamps |

---
