# Purplle Tech Challenge 2026 — Project Context

> **This file is the entry point.** Full documentation lives in split files under [`store-intelligence/docs/context/`](./store-intelligence/docs/context/README.md).

---

## Start Here

**[→ Project Context Index](./store-intelligence/docs/context/README.md)**

---

## What You're Building

End-to-end **Store Intelligence** system: CCTV → detection → events → API → dashboard.

**North star:** Offline store conversion rate = purchasers ÷ unique visitors.

---

## Canonical Decisions

| Decision | Value |
|----------|-------|
| Store ID | `ST1008` (acceptance gate examples may use `STORE_BLR_002` — alias in API when implemented) |
| Date | `2026-04-10` |
| Stack | Python 3.11+, FastAPI, SQLite/PostgreSQL |
| Conversion window | 5 min before POS timestamp |

---

## Doc Index (by implementation area)

| Doc | Purpose |
|-----|---------|
| [00-overview](./store-intelligence/docs/context/00-overview.md) | Scoring, acceptance gate, FAQs |
| [01-architecture](./store-intelligence/docs/context/01-architecture.md) | System stages, repo structure |
| [02-event-schema](./store-intelligence/docs/context/02-event-schema.md) | Event types, Pydantic models |
| [03-data-inventory](./store-intelligence/docs/context/03-data-inventory.md) | POS CSV, CCTV clips, layout |
| [03b-store-layout](./store-intelligence/docs/context/03b-store-layout-brigade-road.md) | Brigade Road floor plan, zones, cameras |
| [04-pos-business-logic](./store-intelligence/docs/context/04-pos-and-business-logic.md) | Conversion, sessions, zones |
| [05-api-contracts](./store-intelligence/docs/context/05-api-contracts.md) | All REST endpoints |
| [06-detection-pipeline](./store-intelligence/docs/context/06-detection-pipeline.md) | CV pipeline, store_layout.json |
| [07-production-ops](./store-intelligence/docs/context/07-production-and-ops.md) | Docker, logging, Part C |
| [08-ai-engineering](./store-intelligence/docs/context/08-ai-engineering.md) | DESIGN.md, CHOICES.md, prompts |
| [09-testing](./store-intelligence/docs/context/09-testing.md) | Mandatory test matrix |
| [10-implementation-guide](./store-intelligence/docs/context/10-implementation-guide.md) | Phases, submit checklist |

---

## Project Code

Implementation: [`store-intelligence/`](./store-intelligence/README.md). **Demo:** [live dashboard](https://purplle-round-2-hack.onrender.com/dashboard) · **fallback:** local Docker in README Quick Start

Large/local-only assets (gitignored): `CCTV Footage/` at repo root. Challenge PDFs, Brigade CSV/XLSX are **not** in git — derived artifacts live under `store-intelligence/data/`. See [store-intelligence/README.md](./store-intelligence/README.md).

One-off dev scripts (layout extraction, context split): [`store-intelligence/scripts/dev/`](./store-intelligence/scripts/dev/).

---

## Cursor Rules

Local only (not committed): [`.cursor/rules/`](./.cursor/rules/) — each rule references the relevant context doc.
