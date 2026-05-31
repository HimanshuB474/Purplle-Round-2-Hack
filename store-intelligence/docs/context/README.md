# Project Context — Index

> **Single source of truth** for the Purplle Tech Challenge 2026 Round 2 implementation.  
> Read docs in order when building; reference individual files via Cursor rules.

---

## Quick Start

| I want to… | Read |
|------------|------|
| Understand the challenge & scoring | [00-overview.md](./00-overview.md) |
| See what to build (4 stages) | [01-architecture.md](./01-architecture.md) |
| Implement event emission | [02-event-schema.md](./02-event-schema.md) |
| Understand local POS + CCTV data | [03-data-inventory.md](./03-data-inventory.md) |
| Understand store floor plan & zones | [03b-store-layout-brigade-road.md](./03b-store-layout-brigade-road.md) |
| Build conversion / funnel logic | [04-pos-and-business-logic.md](./04-pos-and-business-logic.md) |
| Implement API endpoints | [05-api-contracts.md](./05-api-contracts.md) |
| Build the CV pipeline | [06-detection-pipeline.md](./06-detection-pipeline.md) |
| Docker, logging, idempotency | [07-production-and-ops.md](./07-production-and-ops.md) |
| Write DESIGN.md, CHOICES.md, test prompts | [08-ai-engineering.md](./08-ai-engineering.md) |
| Write pytest tests | [09-testing.md](./09-testing.md) |
| Follow build order & submit | [10-implementation-guide.md](./10-implementation-guide.md) |

---

## Canonical Decisions (lock early)

| Decision | Value |
|----------|-------|
| Store ID | `ST1008` (alias `STORE_BLR_002` optional) |
| Reference date | `2026-04-10` |
| Conversion window | 5 minutes before POS transaction |
| Billing zone | `BILLING` |
| POS basket field | `sum(total_amount)` per invoice |

---

## Document Map

```
docs/context/
├── README.md                      ← you are here
├── 00-overview.md                 Challenge summary, scoring, acceptance gate
├── 01-architecture.md             4-stage system, repo layout
├── 02-event-schema.md             8 event types, Pydantic models, validation
├── 03-data-inventory.md           POS deep dive, CCTV metadata, gaps
├── 03b-store-layout-brigade-road.md  Floor plan analysis (extracted from Excel)
├── 04-pos-and-business-logic.md   Conversion, sessions, zone mapping
├── 05-api-contracts.md            All 6 endpoints + error/log formats
├── 06-detection-pipeline.md       Pipeline steps, store_layout.json
├── 07-production-and-ops.md       Part C: Docker, logging, tests
├── 08-ai-engineering.md           Part D: DESIGN/CHOICES templates, prompt blocks
├── 09-testing.md                  Mandatory test matrix
└── 10-implementation-guide.md     Phases, pre-submit, cursor rules appendix
```

---

## Submission Deliverables (outside this folder)

| File | Template in |
|------|-------------|
| `docs/DESIGN.md` | [08-ai-engineering.md §10.3](./08-ai-engineering.md) |
| `docs/CHOICES.md` | [08-ai-engineering.md §10.4](./08-ai-engineering.md) |
| Test `# PROMPT:` blocks | [08-ai-engineering.md §10.2](./08-ai-engineering.md) |

---

## Implementation Order

1. [Phase 1 — Data](./10-implementation-guide.md#phase-1-data-foundation)
2. [Phase 2 — API (acceptance gate)](./10-implementation-guide.md#phase-2-intelligence-api-acceptance-gate)
3. [Phase 3 — Detection pipeline](./10-implementation-guide.md#phase-3-detection-pipeline)
4. [Phase 4 — Integration + tests](./10-implementation-guide.md#phase-4-integration--production)
5. [Phase 5 — Docs (Part D)](./10-implementation-guide.md#phase-5-documentation-part-d--do-alongside-coding)
6. [Phase 6 — Dashboard bonus (optional)](./10-implementation-guide.md#phase-6-bonus-optional)

---

*Split from root `CONTEXT.md`. Raw assets live in `../../` (CCTV, POS CSV, PDFs).*
