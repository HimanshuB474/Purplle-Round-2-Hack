"""Pipeline tuning — see docs/CHOICES.md Decision 1."""

from __future__ import annotations

import os

# Person class in COCO / YOLO
PERSON_CLASS_ID = 0
DETECT_CONF = float(os.getenv("PIPELINE_CONF", "0.35"))
DETECT_CONF_STAFF_CAM = float(os.getenv("PIPELINE_CONF_STAFF", "0.15"))
SAMPLE_INTERVAL_SEC = float(os.getenv("PIPELINE_SAMPLE_SEC", "0.33"))
DWELL_EMIT_SEC = float(os.getenv("PIPELINE_DWELL_SEC", "30.0"))
DWELL_EMIT_SEC_SHORT_CLIP = float(os.getenv("PIPELINE_DWELL_SHORT", "30.0"))
SHORT_CLIP_MAX_SEC = 180.0
ZONE_EXIT_MISS_FRAMES = 3
TRACK_GONE_FRAMES = 4  # sampled frames missing -> EXIT (customer left FOV)
ENTRY_LINE_MARGIN_PX = 15
MAX_FRAMES = int(os.getenv("PIPELINE_MAX_FRAMES", "0"))  # 0 = no limit
YOLO_MODEL = os.getenv("PIPELINE_YOLO_MODEL", "yolov8n.pt")
# Event store_id in JSONL (API alias); canonical DB key remains ST1008 after ingest normalize
EVENT_STORE_ID = os.getenv("PIPELINE_EVENT_STORE_ID", "STORE_BLR_002")
