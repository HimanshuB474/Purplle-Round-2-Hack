# Submission checklist

Use before sending the GitHub link. Architecture notes: [DESIGN.md §9](./DESIGN.md#9-implementation-notes--faq).

## Acceptance gate

| # | Requirement | Status |
|---|-------------|--------|
| 1 | `docker compose up` | ✅ Verified: 71 visitors, 1.41% conversion after ingest |
| 2 | `/metrics` valid | ✅ |
| 3 | Pipeline → `events.jsonl` | ✅ 390 events, all 8 types (2 abandons; dwell-gated join/abandon) |
| 4 | `DESIGN.md` + `CHOICES.md` | ✅ |
| 5 | Stable execution | ✅ 48 pytest tests |

## Validation (run from `store-intelligence/`)

```bash
pytest -q
python scripts/validate_part_ab.py   # expect 20/20
python scripts/validate_part_bc.py   # expect 40/40
python scripts/verify_docker.py      # needs Docker
```

## Not in git (local only)

- `CCTV Footage/*.mp4`, challenge PDFs/CSV/XLSX
- `*.db`, `.pytest_cache/`, `yolov8n.pt`
