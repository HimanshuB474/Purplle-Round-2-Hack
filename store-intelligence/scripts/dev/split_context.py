"""One-off: split monolithic CONTEXT.md into docs/context/*.md (already done)."""
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SI_ROOT = REPO_ROOT / "store-intelligence"
src = (REPO_ROOT / "CONTEXT.md").read_text(encoding="utf-8")

parts = re.split(r"\n(?=## (?!#))", src)
header = parts[0]

sections = {}
for part in parts[1:]:
    m = re.match(r"## (.+?)\n", part)
    if m:
        sections[m.group(1).strip()] = part

mapping = {
    "00-overview.md": [
        "How to Use This Document",
        "Table of Contents",
        "1. Executive Summary",
        "7. Scoring Breakdown (100 + 10 bonus)",
        "8. Acceptance Gate (Mandatory — Must Pass Before Scoring)",
        "22. Key FAQs",
        "23. Contact & Timing",
    ],
    "01-architecture.md": [
        "2. System Architecture (What You Build)",
        "11. Suggested Repository Structure",
        "16. Business Questions → API Mapping",
    ],
    "02-event-schema.md": [
        "3. Event Schema (Required Output)",
        "Appendix B: Event Schema Validation Checklist",
    ],
    "03-data-inventory.md": ["4. Dataset (Official vs Local)"],
    "04-pos-and-business-logic.md": [
        "5. Known Edge Cases in Footage",
        "6. POS Correlation Logic",
        "13. Business Logic & Session Model",
        "Appendix D: pos_transactions.csv — Exact Derivation",
    ],
    "05-api-contracts.md": [
        "12. API Contracts — Complete Reference",
        "Appendix C: Structured Log Format",
    ],
    "06-detection-pipeline.md": [
        "14. Detection Pipeline Specification",
        "15. store_layout.json Schema",
    ],
    "07-production-and-ops.md": [
        "9. Production Readiness Requirements (Part C)",
    ],
    "08-ai-engineering.md": [
        "10. AI Engineering Requirements (Part D) — FULL SPEC",
    ],
    "09-testing.md": ["17. Mandatory Test Matrix"],
    "10-implementation-guide.md": [
        "18. Implementation Phases & Done Criteria",
        "19. Pre-Submit Verification",
        "20. Submission Checklist",
        "21. Post-Submission Follow-Up Prep",
        "Appendix A: Suggested Cursor Rules (derive from this doc)",
    ],
}

out_dir = SI_ROOT / "docs" / "context"
out_dir.mkdir(parents=True, exist_ok=True)

canonical = ""
if "### Canonical Project Decisions" in header:
    start = header.index("### Canonical Project Decisions")
    end = header.index("---", start)
    canonical = header[start:end]

titles = {
    "00-overview.md": "Overview & Scoring",
    "01-architecture.md": "Architecture & Repo Structure",
    "02-event-schema.md": "Event Schema",
    "03-data-inventory.md": "Data Inventory (POS, CCTV, Layout)",
    "04-pos-and-business-logic.md": "POS & Business Logic",
    "05-api-contracts.md": "API Contracts",
    "06-detection-pipeline.md": "Detection Pipeline & Store Layout",
    "07-production-and-ops.md": "Production Readiness (Part C)",
    "08-ai-engineering.md": "AI Engineering (Part D)",
    "09-testing.md": "Testing Requirements",
    "10-implementation-guide.md": "Implementation Guide & Submission",
}

for filename, keys in mapping.items():
    content = f"# {titles[filename]}\n\n> Part of [Project Context Index](./README.md)\n\n---\n\n"
    if filename == "00-overview.md":
        content += header.split("---")[0].strip() + "\n\n"
        if canonical:
            content += canonical.strip() + "\n\n---\n\n"
    for key in keys:
        if key in sections:
            content += sections[key].strip() + "\n\n"
    (out_dir / filename).write_text(content.strip() + "\n", encoding="utf-8")
    print(f"Wrote {filename}")

mapped_keys = {k for keys in mapping.values() for k in keys}
print("Unmapped:", set(sections) - mapped_keys)
