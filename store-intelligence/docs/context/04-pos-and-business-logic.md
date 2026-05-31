# POS & Business Logic

> Part of [Project Context Index](./README.md)

---

## 5. Known Edge Cases in Footage

These are **intentionally included** — handling them is part of the challenge:

| Edge Case | Why It Matters |
|-----------|----------------|
| **Group entry** (2–4 people at once) | Must count individuals, not groups |
| **Staff movement** (uniform) | Must flag `is_staff=true` and exclude from customer metrics |
| **Re-entry** (step out and return) | Must emit `REENTRY`, not duplicate `ENTRY` |
| **Partial occlusion** | Graceful confidence degradation, not silent failure |
| **Billing queue buildup** | Queue depth + abandonment detection |
| **Empty store periods** (5–10 min) | API must handle zero traffic without crashing |
| **Camera angle overlap** | Cross-camera deduplication — no double-counting |

---

## 6. POS Correlation Logic

### 6.1 Official Schema (Target for API)

```csv
store_id, transaction_id, timestamp, basket_value_inr
STORE_BLR_002, TXN_00441, 2026-03-03T14:38:12Z, 1240.00
```

### 6.2 Conversion Rule

No `customer_id` in POS data — correlation is by **time window + store only**:

> A visitor in the billing zone in the **5-minute window before** a transaction timestamp counts as converted for that session.

Even though the local CSV contains `customer_name` and `customer_number`, **do not use them** for conversion matching — this mirrors the challenge constraint and avoids false positives from repeat/loyalty customers.

### 6.3 Applying to Brigade Bangalore Data

With **24 invoices** on **10 April 2026** between 12:15 and 21:40:

1. **Aggregate** line items by `invoice_number` → 24 transactions
2. **Parse timestamp:** `order_date` (`DD-MM-YYYY`) + `order_time` → ISO-8601 UTC
3. **Basket value:** `sum(total_amount)` per invoice (not `GMV` or `NMV`)
4. **Conversion window:** For each transaction at time `T`, find visitor sessions with a billing-zone event in `[T-5min, T]`
5. **Handle zero-value items:** Carry bags (`total_amount = 0`) appear in 7 line items across multiple invoices — include the invoice if other items have value; exclude pure-zero baskets
6. **Abandonment detection:** Visitors with `BILLING_QUEUE_JOIN` or billing-zone dwell but **no** matching transaction within 5 min → `BILLING_QUEUE_ABANDON`

### 6.4 Expected Conversion Baseline

| Metric | Approximate Value (from POS data) |
|--------|-----------------------------------|
| Total transactions | 24 |
| Transaction hours covered | 12:00 – 21:00 |
| Peak hour | 19:00 (5 transactions) |
| Avg basket | ₹1,430 |
| Max basket | ₹8,243 (24 items — likely family/group purchase) |

Your detection pipeline must produce enough `ENTRY` events and billing-zone visits to make a conversion rate in a plausible range when divided by 24 purchases. Exact visitor count comes from CCTV, not POS.

---

## 13. Business Logic & Session Model

### 13.1 Session Lifecycle

```
ENTRY → [zone + billing events] → EXIT
REENTRY after EXIT → same visitor_id (do not double-count in funnel)
Staff (is_staff=true) → excluded from all customer metrics
Group of 3 → 3 ENTRY events → 3 sessions
```

### 13.2 Conversion Algorithm

For each POS transaction at time `t`: find non-staff sessions with billing-zone event in `[t-5min, t]`. Mark converted. Never use customer_name/phone from CSV.

### 13.3 Zone Mapping (POS → store zones)

| dep_name | zone_id |
|----------|---------|
| makeup | MAKEUP |
| skin | SKIN |
| hair | HAIR |
| bath-and-body | BATH_BODY |
| personal-care | PERSONAL_CARE |
| fragrance | FRAGRANCE |
| (billing) | BILLING |

---

## Appendix D: pos_transactions.csv — Exact Derivation

**Source:** `Brigade_Bangalore_10_April_26 (1)bc6219c.csv`

```python
import pandas as pd

df = pd.read_csv("Brigade_Bangalore_10_April_26 (1)bc6219c.csv")
pos = (
    df.groupby("invoice_number")
    .agg(
        store_id=("store_id", "first"),
        timestamp=("order_date", "first"),  # combine with order_time
        basket_value_inr=("total_amount", "sum"),
    )
    .reset_index()
    .rename(columns={"invoice_number": "transaction_id"})
)
# Parse timestamp: DD-MM-YYYY + HH:MM:SS → ISO UTC
pos["timestamp"] = pd.to_datetime(
    df.groupby("invoice_number").apply(
        lambda g: g["order_date"].iloc[0] + " " + g["order_time"].iloc[0]
    ),
    format="%d-%m-%Y %H:%M:%S",
).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
pos[["store_id", "transaction_id", "timestamp", "basket_value_inr"]].to_csv(
    "data/pos_transactions.csv", index=False
)
```

**Expected row count:** 24

---

*Single source of truth — Purplle Tech Challenge 2026 Round 2. Sources: Problem Statement, Evaluation Framework, Brigade Bangalore POS analysis, local CCTV metadata. Use this file to implement end-to-end and to author Cursor rules.*
