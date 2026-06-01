# Data Inventory (POS, CCTV, Layout)

> Part of [Project Context Index](./README.md)

---

## 4. Dataset (Official vs Local)

### 4.1 Official Challenge Dataset (from problem statement)

The ZIP archive should contain:

| Asset | Description |
|-------|-------------|
| **CCTV clips** | 5 stores × 3 camera angles × 20 min each (Entry, Main floor, Billing) |
| **`store_layout.json`** | Zone definitions, camera coverage, open hours per store |
| **`pos_transactions.csv`** | `store_id, transaction_id, timestamp, basket_value_inr` |
| **`sample_events.jsonl`** | 200 example events for schema validation |
| **`assertions.py`** | 10 example test assertions (not full scoring suite) |

**Video specs:** 1080p, 15fps, face-blurred, no audio, varied lighting

### 4.2 Local Workspace Inventory

| File / Folder | Status | Notes |
|---------------|--------|-------|
| `CCTV Footage/CAM 1.mp4` – `CAM 5.mp4` | ✅ Present | 5 clips, ~2–2.5 min each — see [Section 4.4](#44-local-cctv-footage-inventory) |
| `Brigade Road - Store layoutc5f5d56.xlsx` | ✅ Analyzed | **Visual floor plan** — see [03b-store-layout-brigade-road.md](./03b-store-layout-brigade-road.md); extracted PNG at `data/layout/image1.png` |
| `Brigade_Bangalore_10_April_26 (1)bc6219c.csv` | ✅ Present | **Line-item POS data** — see [Section 4.3](#43-brigade-bangalore-pos-data-deep-dive) |
| `store_layout.json` | ✅ Present | Verified cameras + zones — `store-intelligence/data/store_layout.json` |
| `pos_transactions.csv` | ✅ Present | 24 rows — `store-intelligence/data/pos_transactions.csv` |
| `assertions.py` | ✅ Present | Example API checks — `pytest assertions.py` |

**Pipeline output:** `data/events.jsonl` generated from clips (acceptance gate). Camera roles and polygons: [`data/store_layout.json`](../data/store_layout.json).

---

### 4.3 Brigade Bangalore POS Data Deep Dive

**File:** `Brigade_Bangalore_10_April_26 (1)bc6219c.csv`

This is **item-level (SKU-level) retail POS data**, not a pre-aggregated transaction feed. Each row is one product line within an order. You must aggregate to invoice/order level before feeding the API.

#### 4.3.1 Dataset Summary

| Metric | Value |
|--------|-------|
| **Granularity** | Line item (SKU) |
| **Total rows** | 101 |
| **Unique orders** | 24 (`order_id`) |
| **Unique invoices** | 24 (`invoice_number`) — 1:1 with orders |
| **Columns** | 39 |
| **Store** | `ST1008` — Brigade_Bangalore, Bangalore |
| **Date** | Single day: **10-04-2026** |
| **Time window** | **12:15:05 – 21:39:55** (~9.5 hours) |
| **Line items per order** | Min 1 · Max 24 · Mean 4.2 |
| **Total units sold (`qty`)** | 117 |
| **Line-item revenue (`total_amount` sum)** | ₹34,331.71 |
| **Invoice-level revenue (sum per invoice)** | ₹34,331.71 across 24 transactions |
| **Basket value range** | ₹149 – ₹8,243 (mean ₹1,430 · median ₹856) |
| **Returns** | None (`return_id` empty on all rows) |
| **Invoice type** | All `sales` |

#### 4.3.2 All 39 Columns — Grouped by Purpose

**Transaction & invoice identifiers**

| Column | Type | Nulls | Unique | Description |
|--------|------|-------|--------|-------------|
| `order_id` | int | 0 | 24 | Internal order ID — groups line items |
| `invoice_number` | str | 0 | 24 | Invoice/receipt ID (e.g. `ML0426KAP0001324`) — use as `transaction_id` |
| `invoice_type` | str | 0 | 1 | Always `sales` |
| `return_id` | float | 101 | 0 | Empty — no returns in this dataset |

**Temporal**

| Column | Type | Nulls | Unique | Description |
|--------|------|-------|--------|-------------|
| `order_date` | str | 0 | 1 | `DD-MM-YYYY` format — `10-04-2026` |
| `order_time` | str | 0 | 24 | `HH:MM:SS` — one timestamp per invoice |
| `week_assigned` | float | 101 | 0 | Empty — not populated |

**Store location**

| Column | Type | Nulls | Unique | Description |
|--------|------|-------|--------|-------------|
| `store_id` | str | 0 | 1 | `ST1008` |
| `store_name` | str | 0 | 1 | `Brigade_Bangalore` |
| `city` | str | 0 | 1 | `Bangalore` |

**Customer (present locally — do NOT use for conversion correlation per challenge rules)**

| Column | Type | Nulls | Unique | Description |
|--------|------|-------|--------|-------------|
| `customer_name` | str | 0 | 19 | 19.8% are `"Guest "` — walk-in/anonymous |
| `customer_number` | int | 0 | 21 | Phone numbers; 6 rows use placeholder `1000000000` |

> **Important:** The official challenge POS schema has **no customer identity**. Conversion must be correlated by **store + time window only**, not by matching phone/name. Treat customer fields as metadata you should **not** rely on for the scoring API.

**Product / catalog (useful for zone & heatmap enrichment)**

| Column | Type | Nulls | Unique | Description |
|--------|------|-------|--------|-------------|
| `sku` | str | 0 | 83 | Product SKU code |
| `product_id` | int | 0 | 83 | Internal product ID |
| `ean` | float | 0 | 18 | Barcode (scientific notation in CSV) |
| `product_name` | str | 0 | 83 | Full product description |
| `brand_name` | str | 0 | 22 | e.g. Faces Canada (32 lines), Good Vibes (14) |
| `dep_name` | str | 0 | 6 | **Department = proxy for store zone** |
| `sub_category` | str | 0 | 41 | Finer category (Sheet Mask, Lipstick, etc.) |
| `brand_type` | str | 0 | 14 | PB (Private Brand), L'Oreal, HUL, etc. |
| `hsn_code` | int | 0 | 18 | Tax classification code |
| `qty` | int | 0 | 4 | Quantity purchased (1–7 per line) |

**Department breakdown (`dep_name`) — maps to store zones**

| Department | Line Items | Share |
|------------|-----------|-------|
| makeup | 54 | 53.5% |
| skin | 27 | 26.7% |
| bath-and-body | 9 | 8.9% |
| hair | 6 | 5.9% |
| personal-care | 4 | 4.0% |
| fragrance | 1 | 1.0% |

Top sub-categories: Sheet Mask (14), Lipstick (10), Body & Massage Oil (7), Makeup Remover (6), Foundation (5).

**Sales staff (potential staff-detection validation signal)**

| Column | Type | Nulls | Unique | Description |
|--------|------|-------|--------|-------------|
| `salesperson_id` | int | 0 | 6 | Numeric staff ID |
| `employee_code` | str | 7 | 5 | e.g. `CL2727`, `CL2063` |
| `salesperson_name` | str | 7 | 5 | 5 active staff on this day |

| Employee Code | Name | Line Items |
|---------------|------|------------|
| CL2727 | Zufishan Khazra | 42 |
| CL2063 | kasthuri v | 19 |
| CL2680 | Priya v | 13 |
| CL1997 | Shashikala . | 12 |
| CL2541 | Naziya Begum | 8 |

7 rows have empty `employee_code`/`salesperson_name` — all are **zero-value carry bags** at billing.

**Pricing & revenue**

| Column | Type | Description |
|--------|------|-------------|
| `GMV` | int | Gross merchandise value (pre-discount list price × qty) |
| `NMV` | float | Net merchandise value (after item-level discounts) |
| `total_amount` | float | **Actual paid amount per line** — use for basket aggregation |
| `amt_without_gwp` | float | Amount excluding gift-with-purchase items |
| `coupon_amount` | float | Coupon discount applied |
| `item_promotion` | float | Promotional discount per line |
| `pb_eb_sale` | float | Private brand / exclusive brand sale flag amount |
| `taxable_amt` | float | Pre-tax amount |
| `tax_amt` | float | Tax amount |
| `tax` | int | Tax rate % (5 or 18) |
| `tax_m` | float | Tax multiplier (1.05 or 1.18) |

**Promotions & discounts**

| Column | Type | Nulls | Unique | Description |
|--------|------|-------|--------|-------------|
| `offer_name` | str | 28 | 9 | Active on 73/101 rows (72%) |
| `coupon_code` | str | 98 | 1 | Only 3 rows — e.g. `MAR2620` |
| `discount_code` | str | 98 | 1 | Same 3 rows as coupon |

Top offers: Buy 2 Get 1 Faces/Ny Bae (35 lines), Buy 2 Get 2 Sheet Mask (13), Buy 2 Get 1 PB (9).

#### 4.3.3 Hourly Transaction Pattern

Invoices by hour (useful for validating detection pipeline traffic vs purchases):

| Hour | Invoices |
|------|----------|
| 12:00 | 2 |
| 13:00 | 2 |
| 14:00 | 1 |
| 15:00 | 3 |
| 16:00 | 3 |
| 17:00 | 2 |
| 18:00 | 3 |
| 19:00 | 5 (peak) |
| 20:00 | 1 |
| 21:00 | 2 |

Peak billing activity at **19:00** (5 transactions). Quietest mid-afternoon (**14:00** — 1 transaction).

#### 4.3.4 Data Quirks & Edge Cases

| Quirk | Count | Impact on Pipeline |
|-------|-------|-------------------|
| **Zero-value carry bags** | 7 rows (`total_amount = 0`) | Exclude from revenue metrics; still count as a billing-zone visit |
| **Guest customers** | 20 rows (5 unique orders) | Reinforces time-window correlation — no reliable customer ID |
| **Placeholder phone `1000000000`** | 6 rows | Anonymous walk-ins — ignore for identity |
| **GWP / free items** | Several (`Purplle GWP`, pouches at ₹1) | Use `total_amount`, not `GMV`, for basket value |
| **Multi-qty lines** | Up to qty=7 (sheet masks) | One row can represent multiple units |
| **Heavy promotions** | 72% of lines discounted | `GMV` ≠ `total_amount` — always aggregate on `total_amount` |
| **Missing staff on carry bags** | 7 rows | Billing events without assigned salesperson |

#### 4.3.5 Deriving Official `pos_transactions.csv`

Aggregate line items → one row per invoice:

```python
# Pseudocode
group by invoice_number:
    store_id        = "ST1008"  # or map to "STORE_BLR_002" for API
    transaction_id  = invoice_number
    timestamp       = ISO-8601(order_date + order_time)  # e.g. 2026-04-10T12:42:18Z
    basket_value_inr = sum(total_amount)
```

**Example derived output (top transactions):**

| store_id | transaction_id | timestamp | basket_value_inr |
|----------|----------------|-----------|------------------|
| ST1008 | ML0426KAP0001324 | 2026-04-10T12:42:18Z | 8243.23 |
| ST1008 | ML0426KAP0001399 | 2026-04-10T19:21:55Z | 3467.18 |
| ST1008 | ML0426KAP0001353 | 2026-04-10T16:45:32Z | 3076.98 |
| ST1008 | ML0426KAP0001393 | 2026-04-10T19:02:09Z | 2295.96 |
| ST1008 | ML0426KAP0001384 | 2026-04-10T18:41:51Z | 2064.07 |

**Store ID mapping:** Local data uses `ST1008`; challenge examples use `STORE_BLR_002`. Pick one canonical ID and use it consistently across events, POS, and API routes.

#### 4.3.6 Features Useful Beyond Basic Conversion

| Local Feature | Potential Use in Store Intelligence |
|---------------|-------------------------------------|
| `dep_name` / `sub_category` | Enrich `metadata.sku_zone` in detection events; validate heatmap zone dwell vs actual purchases |
| `brand_name` / `brand_type` | Category-level conversion analysis (PB vs exclusive brands) |
| `salesperson_name` | Cross-reference with CCTV staff detection at billing counter |
| `offer_name` | Explain conversion spikes/drops in anomaly detection |
| `qty` | Basket size metrics beyond transaction count |
| Hourly invoice distribution | Sanity-check visitor funnel vs purchase timing |
| `GMV` vs `total_amount` | Discount depth analytics (optional, not required for scoring) |

---

### 4.4 Local CCTV Footage Inventory — VERIFIED

| File | camera_id | Role | Duration | FPS | Verified content |
|------|-----------|------|----------|-----|------------------|
| `CAM 3.mp4` | `CAM_ENTRY_01` | **ENTRY** | ~148s | 29.97 | Glass doors, BACKLIT display, yellow gondola |
| `CAM 1.mp4` | `CAM_FLOOR_SKIN_01` | **MAIN** | ~140s | 29.97 | Skincare top wall (GV, DermDoc, Minimalist, Aqualogica) |
| `CAM 2.mp4` | `CAM_FLOOR_MAKEUP_01` | **MAIN** | ~126s | 29.97 | Makeup/hair wall (Maybelline, Faces, Lakme, Alps Goodness) |
| `CAM 5.mp4` | `CAM_BILLING_01` | **BILLING** | ~139s | 25.00 | Cash counter, queue, scanners/laptops |
| `CAM 4.mp4` | `CAM_STAFF_BACK_01` | **STAFF** | ~146s | 25.00 | Back-office storage — exclude from customer metrics |

**On-screen timestamp:** 10/04/2026 ~20:10–20:11 (evening, aligns with POS peak hour 19:00).

**Full analysis:** [03b-store-layout-brigade-road.md §6](./03b-store-layout-brigade-road.md#6-cctv-camera-mapping--verified-2026-05-31)

**Annotated frames:** `store-intelligence/data/layout/cctv_annotated/`

---
