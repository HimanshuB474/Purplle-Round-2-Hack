# Detection Pipeline & Store Layout

> Part of [Project Context Index](./README.md)

---

## 14. Detection Pipeline Specification

### 14.1 Processing Steps

1. Load clip → frames at native FPS (25 or 29.97)
2. Detect persons (YOLO/MediaPipe/etc.)
3. Track (ByteTrack/DeepSORT)
4. Classify staff → `is_staff`
5. Assign `visitor_id` at ENTRY; handle REENTRY
6. Line-cross → ENTRY/EXIT
7. Polygon → ZONE_ENTER/EXIT/DWELL (emit ZONE_DWELL every 30s)
8. Billing queue → BILLING_QUEUE_JOIN/ABANDON
9. Emit JSONL with UUID `event_id`, ISO timestamp

### 14.2 Timestamp

`timestamp = clip_base_timestamp + (frame_number / fps)` — base per camera in `store_layout.json` (verified overlay: **2026-04-10T20:10:00Z**).

### 14.3 CLI

```bash
./pipeline/run.sh
python pipeline/detect.py --clip "../CCTV Footage/CAM 3.mp4" --camera CAM_ENTRY_01 --store ST1008
curl -X POST localhost:8000/events/ingest -d @data/events.json
```

Clip paths in `store_layout.json` are relative to the `store-intelligence/` project root (`../CCTV Footage/`).

---

## 15. store_layout.json Schema

**Canonical file:** `data/store_layout.json` (do not duplicate stale inline JSON in docs).  
**Full floor plan analysis:** [03b-store-layout-brigade-road.md](./03b-store-layout-brigade-road.md)  
**Extracted image:** `data/layout/image1.png` (Current + Revised layouts)

The Excel file has **no cell-based coordinates** — only an embedded PNG + brand text labels. Zone polygons were traced on CCTV sample frames (1920×1080) and verified 2026-05-31.

### Physical zones (Brigade Road F.O.H.)

| zone_id | Area on plan |
|---------|--------------|
| `ENTRY` | Glass doors + BACKLIT (left) |
| `SKIN` | Top wall — GV, DermDoc, Minimalist, Aqualogica, TFS, etc. |
| `MAKEUP` | Bottom wall + central MAKEUP UNITS with chairs |
| `HAIR` | Alps Goodness, Streax/L'Oreal on bottom wall |
| `FRAGRANCE` | Central Fragrance/Nail island |
| `PERSONAL_CARE` | Accessories, nail gondola, Mens Care |
| `BILLING` | CASH COUNTER (right wall) — POS correlation |

### Verified camera mapping (2026-05-31)

| Clip | camera_id | role | Notes |
|------|-----------|------|-------|
| CAM 3.mp4 | CAM_ENTRY_01 | **ENTRY** | Glass doors, BACKLIT display; `entry_line` defined |
| CAM 1.mp4 | CAM_FLOOR_SKIN_01 | **MAIN** | Skincare top wall |
| CAM 2.mp4 | CAM_FLOOR_MAKEUP_01 | **MAIN** | Makeup/hair bottom wall + trial |
| CAM 5.mp4 | CAM_BILLING_01 | **BILLING** | Cash counter — use for conversion correlation |
| CAM 4.mp4 | CAM_STAFF_BACK_01 | **STAFF** | Back office — **exclude from customer metrics** |

Corrections vs initial hypothesis: CAM 1 is **not** ENTRY; CAM 3 is ENTRY; CAM 4 is staff/back, not billing.

### Cross-camera notes

| Pair | Handling |
|------|----------|
| CAM 3 (entry) → CAM 1 (skin) | Dedupe via Re-ID; do not double ENTRY count |
| CAM 1 ↔ CAM 2 | Same visitor may appear on both floor angles |
| CAM 5 billing ↔ CAM 1/2 | Use BILLING polygon only for queue/conversion events |

---
