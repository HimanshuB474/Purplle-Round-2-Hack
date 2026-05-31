# Submission checklist

Use before sending the GitHub link. Gap analysis: [DESIGN.md §9](./DESIGN.md#9-known-gaps--reviewer-faq).

## Acceptance gate

| # | Requirement | Status |
|---|-------------|--------|
| 1 | `docker compose up` | ✅ Verified: 71 visitors, 1.41% conversion after ingest |
| 2 | `/metrics` valid | ✅ |
| 3 | Pipeline → `events.jsonl` | ✅ 299 events, all 8 types (3 abandons) |
| 4 | `DESIGN.md` + `CHOICES.md` | ✅ |
| 5 | Stable execution | ✅ 46 pytest tests |

## Validation (run from `store-intelligence/`)

```bash
pytest -q
python scripts/validate_part_ab.py   # 19/20 on committed events.jsonl; 20/20 after `python -m pipeline.detect` regen
python scripts/validate_part_bc.py   # expect 40/40
python scripts/verify_docker.py      # needs Docker
```

## Admin

- [ ] GitHub link submitted
- [ ] Reviewer invited on private repo
- [ ] Reviewer path: clone → `store-intelligence/` → Quick Start in README

## Not in git (local only)

- `CCTV Footage/*.mp4`, challenge PDFs/CSV/XLSX
- `*.db`, `.pytest_cache/`, `yolov8n.pt`
