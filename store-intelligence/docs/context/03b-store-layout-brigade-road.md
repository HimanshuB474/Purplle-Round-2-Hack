# Brigade Road Store Layout — Brigade Bangalore (ST1008)

> Part of [Project Context Index](./README.md)  
> **Source file:** `../../Brigade Road - Store layoutc5f5d56.xlsx`  
> **Extracted assets:** [`../../data/layout/`](../../data/layout/)

---

## 1. What the Excel File Actually Contains

The `.xlsx` is **not** a data table — it is a **visual floor-plan workbook** with embedded drawings.

| Property | Value |
|----------|-------|
| Sheets | 1 (`Sheet1`) |
| Structured cell data | **2 cells only** — `N4` = `"Revised"`, `N23` = `"Current"` |
| Embedded content | **2 pictures** + **34 text-box shapes** (brand labels) |
| Extracted image | `data/layout/image1.png` (128 KB) — side-by-side **Current** + **Revised** layouts |
| Drawing metadata | `data/layout/drawing1.xml` — brand label positions on Excel grid |

There are **no zone polygons, coordinates, or camera positions** in the spreadsheet. You must:
1. Use this doc for **semantic zones** (what exists in the store)
2. Draw **pixel polygons** on CCTV frames for `store_layout.json`
3. Align with POS `dep_name` categories from the sales CSV

---

## 2. Store Overview — F.O.H. (Front of House)

Purplle beauty retail format at **Brigade Road, Bangalore**. Rectangular floor plate with:

```
                    TOP WALL (Skincare / K-beauty shelf run)
    ┌──────────────────────────────────────────────────────────────┐
    │ EB  TFS  GV  DermDoc  Minimalist  Aqualogica  Lakme  Acc.   │
    │                                                              │
 E  │     [Fragrance/Nail Unit]    [MAKEUP UNIT]←→[MAKEUP UNIT]   │  C
 N  │              [NAIL GONDOLA]         (chairs)                 │  A
 T  │                                                              │  S
 R  │  Maybelline  Faces  Lakme  Colorbar  Swiss  NY Bae  Alps    │  H
 Y  │  (bottom wall — makeup / hair brands)                        │    C
    │                                              [PMU]  [55"LED] │  O
    │ Existing Glass                               ┌─────────────┐ │  U
    │ + BACKLIT                                    │ CASH COUNTER│ │  N
    └──────────────────────────────────────────────┴─────────────┴─┘  T
         ↑ LEFT                                              RIGHT ↑
       ENTRANCE                                            BILLING
```

### Customer flow (typical path)

1. **Enter** via glass doors (left) — past BACKLIT display
2. **Browse** top wall (skincare) or bottom wall (makeup/hair) — perimeter gondolas
3. **Trial / dwell** at central MAKEUP UNITS (seated consultation)
4. **Fragrance/Nail** island near front
5. **Queue** at CASH COUNTER (right wall) — POS transactions happen here
6. **Exit** back through entrance or side path

---

## 3. Two Layout Variants (Current vs Revised)

The PNG shows **two plans side-by-side** in one image. Excel labels them:

| Label | Excel cell | Description |
|-------|------------|-------------|
| **Current** | `N23` | Active shelf allocation at time of survey |
| **Revised** | `N4` | Planned / updated brand placement |

### 3.1 Top wall — Skincare / K-beauty (both layouts)

Runs along the **top** of the floor plan (far wall from entrance).

| Zone label | Current layout | Revised layout | POS `dep_name` |
|------------|----------------|----------------|----------------|
| EB / Korean | ✅ EB Korean | ✅ EB | skin |
| The Face Shop | ✅ TFS | ✅ TFS | skin |
| Good Vibes | ✅ GV | ✅ GV | skin |
| DermDoc | ✅ | ✅ | skin |
| Minimalist | ✅ | ✅ | skin |
| Aqualogica | ✅ | ✅ | skin |
| Lakme Skin | ✅ Lakme Skin | — | skin / makeup |
| Foxtale | — | ✅ | skin |
| Pilgrim | — | ✅ | skin |
| D&K | — | ✅ | skin |
| JC | — | ✅ | skin |
| Salm | — | ✅ | skin |
| Beauty Essentials | — | ✅ (combined label) | skin / bath-and-body |
| Accessories | ✅ (top-right) | ✅ (top-right) | personal-care / makeup |

### 3.2 Bottom wall — Makeup / Hair (both layouts)

Runs along the **bottom** of the floor plan (closer to entrance side).

| Zone label | Current layout | Revised layout | POS `dep_name` |
|------------|----------------|----------------|----------------|
| Maybelline | ✅ | ✅ | makeup |
| Faces Canada | ✅ Faces | ✅ Faces | makeup |
| Lakme | ✅ | ✅ | makeup |
| Colorbar + Sugar | ✅ Mars+ | ✅ Mars+ | makeup |
| Swiss Beauty + Renee | ✅ Swiss + Renee | ✅ Swiss + Renee | makeup |
| NY Bae | ✅ Nybae | ✅ Nybae | makeup |
| Alps Goodness | ✅ | ✅ | hair |
| Streax / L'Oreal | ✅ Lo'real | ✅ Lo'real | hair |
| Mens Care | — | ✅ | personal-care / bath-and-body |

**Note:** POS CSV top brands align with bottom wall — **Faces Canada (32 lines), Good Vibes (14), NY Bae (10), Maybelline (3)**.

### 3.3 Central fixtures (both layouts)

| Fixture | Location | Detection / analytics use |
|---------|----------|----------------------------|
| **Fragrance / Nail Unit** | Central-front, ~2594 mm from entrance | `FRAGRANCE` zone; nail = personal-care |
| **MAKEUP UNIT × 2** | Central, back-to-back with **CHAIR** | High dwell; trial makeup → `MAKEUP` zone |
| **NAIL GONDOLA** | Near makeup units | `PERSONAL_CARE` sub-zone |
| **PMU unit** | Bottom-right corner | Staff/service area — likely `is_staff` |
| **55" LED PANEL** | Right wall | Digital signage — not a shopping zone |
| **CASH COUNTER** | Right wall, mid-height | **`BILLING`** zone — POS correlation target |

---

## 4. Key Dimensions (from floor plan, in mm)

Useful for scale reference when mapping CCTV pixels to real distances:

| Measurement | mm |
|-------------|-----|
| Entrance → Fragrance/Nail unit | 2594 |
| Fragrance unit width | 500 |
| Fragrance → Makeup units | 1347 |
| Makeup units → Cash counter zone | 2000 |
| Top wall → centre aisle | 1110 |
| Centre aisle width | 900 |
| Centre → bottom wall | 1110 |
| **Total floor depth (centre)** | **3120** |
| Top wall → cash counter (vertical) | 710 |
| Cash counter → bottom wall | 1210 |
| **Total floor depth (right / billing side)** | **4020** |

---

## 5. Semantic Zone Model for `store_layout.json`

Map physical areas to **`zone_id`** values used in detection events and heatmap API.

| zone_id | Physical area | POS `dep_name` | Example brands on plan |
|---------|---------------|----------------|------------------------|
| `ENTRY` | Glass door threshold + BACKLIT | — | — |
| `SKIN_TOP_WALL` | Top perimeter shelf run | `skin` | GV, DermDoc, Minimalist, Aqualogica, TFS |
| `MAKEUP_BOTTOM_WALL` | Bottom perimeter shelf run | `makeup` | Maybelline, Faces, Lakme, NY Bae |
| `HAIR_BOTTOM_WALL` | Bottom wall hair section | `hair` | Alps Goodness, Streax/L'Oreal |
| `MAKEUP_TRIAL` | Central MAKEUP UNITS + chairs | `makeup` | Seated trial — high dwell |
| `FRAGRANCE_NAIL` | Fragrance/Nail island | `fragrance`, `personal-care` | Central gondola |
| `ACCESSORIES` | Top-right accessories bay | `personal-care`, `makeup` | Accessories label |
| `MENS_CARE` | Mens Care bay (Revised only) | `personal-care`, `bath-and-body` | Revised layout |
| `BILLING` | CASH COUNTER + queue | — | POS transactions |
| `STAFF_PMU` | PMU + counter staff area | — | Exclude via `is_staff` |

### Simplified zone IDs (if you prefer fewer zones for heatmap)

| Simplified ID | Merges |
|---------------|--------|
| `SKIN` | SKIN_TOP_WALL |
| `MAKEUP` | MAKEUP_BOTTOM_WALL + MAKEUP_TRIAL |
| `HAIR` | HAIR_BOTTOM_WALL |
| `FRAGRANCE` | FRAGRANCE_NAIL |
| `PERSONAL_CARE` | ACCESSORIES + MENS_CARE + nail |
| `BILLING` | CASH COUNTER |

Use **simplified IDs** if camera resolution cannot distinguish individual brand bays.

---

## 6. CCTV Camera Mapping — VERIFIED (2026-05-31)

Frame analysis from `data/layout/cctv_samples/` and annotated polygons in `data/layout/cctv_annotated/`.

| Source file | camera_id | Role | Verified view | Floor plan match |
|-------------|-----------|------|---------------|------------------|
| **CAM 3.mp4** | `CAM_ENTRY_01` | **ENTRY** | Glass doors (top), BACKLIT Purplle sunscreen stand, yellow gondola, entrance threshold | Entrance left + BACKLIT |
| **CAM 1.mp4** | `CAM_FLOOR_SKIN_01` | **MAIN** | Skincare top wall: Farmstay, TFS, Good Vibes, DermDoc, Minimalist, Aqualogica; fragrance island; trial chair | Top wall SKIN |
| **CAM 2.mp4** | `CAM_FLOOR_MAKEUP_01` | **MAIN** | Makeup/hair bottom wall: Alps Goodness, Swiss Beauty, Lakme, Faces, Maybelline; vanity station with chair | Bottom wall + trial units |
| **CAM 5.mp4** | `CAM_BILLING_01` | **BILLING** | Cash counter (laptops, scanners), queue floor, ACCESSORIES display, staff at billing | CASH COUNTER right wall |
| **CAM 4.mp4** | `CAM_STAFF_BACK_01` | **STAFF** | Back-office/storage: inventory boxes, water dispenser, staff bags/helmets — **NOT retail floor** | Back of house (exclude from funnel) |

### Important corrections vs initial hypothesis

| Initial guess | Actual (verified) |
|---------------|-------------------|
| CAM 1 = ENTRY | CAM 1 = **SKIN floor** (interior skincare wall) |
| CAM 3 = MAIN | CAM 3 = **ENTRY** (glass doors visible) |
| CAM 4 = BILLING | CAM 4 = **STAFF back office** (not billing) |
| CAM 5 = secondary billing | CAM 5 = **primary BILLING** (cash counter) |

### Clip metadata (all cameras)

| Property | Value |
|----------|-------|
| Resolution | 1920×1080 |
| Date on overlay | **10/04/2026 ~20:10–20:11** (aligns with POS evening peak) |
| Duration | ~125–148 seconds per clip |
| FPS | CAM 1–3: 29.97 · CAM 4–5: 25.00 |
| `clip_base_timestamp` | `2026-04-10T20:10:00Z` (from on-screen timestamp) |

### Cross-camera overlap

| Overlap | Handling |
|---------|----------|
| CAM 3 (entry) → CAM 1 (skin floor) | Customer entering is seen on ENTRY then SKIN — dedupe via Re-ID; do not double ENTRY count |
| CAM 1 ↔ CAM 2 | Both cover main floor from different angles (top wall vs bottom wall) — same visitor may appear on both |
| CAM 5 billing ↔ CAM 1/2 | Billing camera also sees nearby skin shelves — use BILLING polygon only for conversion correlation |
| CAM 4 staff room | All events `is_staff=true` or exclude camera entirely from customer metrics |

### Generated assets

| Path | Description |
|------|-------------|
| `data/store_layout.json` | Full camera + zone polygon config |
| `data/layout/cctv_samples/` | Raw mid/early/late frames per camera |
| `data/layout/cctv_annotated/` | Zone polygons drawn on frames |
| `scripts/annotate_zones.py` | Regenerate annotated frames |

```bash
python store-intelligence/scripts/annotate_zones.py
```

---

## 7. Brand Labels from Excel Drawing (machine-extracted)

39 text shapes parsed from `drawing1.xml` — duplicated for Current + Revised rows:

```
Top wall:    Salm, TFS, GV, DermDoc, Minimalist, Aqualogica, Foxtale, JC,
             EB, Pilgrim, D&K, Accessories, Beauty Essentials
Bottom wall: Maybelline, Faces, Lakme, Mars+, Nybae, Alps Goodness,
             Lo'real, Swiss + Renee, Mens Care
```

Use these as **`metadata.sku_zone`** hints when detection can infer brand bay from position.

---

## 8. POS ↔ Layout Cross-Validation

Brigade POS CSV (`dep_name`) vs floor plan:

| POS `dep_name` | Share | Floor plan location |
|----------------|-------|---------------------|
| makeup (54%) | 53.5% | Bottom wall + central trial units |
| skin (27) | 26.7% | Top wall |
| bath-and-body (9) | 8.9% | Scattered; Beauty Essentials bay |
| hair (6) | 5.9% | Alps Goodness / Streax on bottom wall |
| personal-care (4) | 4.0% | Accessories, nail, mens care |
| fragrance (1) | 1.0% | Fragrance/Nail island |

Top POS brands on **bottom wall**: Faces Canada, Good Vibes (also top wall), NY Bae, Maybelline — consistent with makeup-dominant sales.

---

## 9. Implementation Checklist

- [ ] Open each CCTV clip; confirm camera role against Section 6
- [ ] Choose **Current** or **Revised** layout (document in CHOICES.md)
- [ ] Draw polygons on 1920×1080 frames for each zone in Section 5
- [x] Define entry line on ENTRY camera at glass door threshold (`entry_line` in `store_layout.json`)
- [ ] Define BILLING polygon around cash counter on billing camera
- [ ] Save as `data/store_layout.json`
- [ ] Reference floor plan image at `data/layout/image1.png` while tracing zones

---

## 10. Files in `data/layout/`

| File | Description |
|------|-------------|
| `image1.png` | Extracted floor plan (Current + Revised side-by-side) |
| `drawing1.xml` | Raw Excel drawing with brand text anchors |
| `README.md` | Asset index |

Regenerate extraction: `python scripts/dev/analyze_store_layout.py`
