#!/usr/bin/env bash
# Process all CCTV clips -> data/events.jsonl (see data/store_layout.json)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
python -m pipeline.detect --layout data/store_layout.json --output data/events.jsonl --root "$ROOT"
