"""POST data/events.jsonl to running API."""

from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PATH = ROOT / "data" / "events.jsonl"
API = "http://127.0.0.1:8000/events/ingest"


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PATH
    events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    body = json.dumps({"events": events}).encode()
    req = urllib.request.Request(
        API,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        print(resp.read().decode())


if __name__ == "__main__":
    main()
