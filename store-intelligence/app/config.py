"""Application settings from environment."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{ROOT / 'data' / 'store_intelligence.db'}")
POS_CSV_PATH = Path(os.getenv("POS_CSV_PATH", ROOT / "data" / "pos_transactions.csv"))
STORE_LAYOUT_PATH = Path(os.getenv("STORE_LAYOUT_PATH", ROOT / "data" / "store_layout.json"))
API_VERSION = "1.0.0"
MAX_INGEST_BATCH = 500
CONVERSION_WINDOW_SECONDS = 300
STALE_FEED_SECONDS = 600
QUEUE_SPIKE_THRESHOLD = 3
QUEUE_SPIKE_MIN_SECONDS = 120
CONVERSION_DROP_PCT = 20.0
DEAD_ZONE_MINUTES = 30
HEATMAP_LOW_CONFIDENCE_SESSIONS = 20
