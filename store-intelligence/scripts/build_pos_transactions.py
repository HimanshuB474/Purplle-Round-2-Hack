"""Build pos_transactions.csv from Brigade Bangalore line-item CSV."""
from pathlib import Path

import pandas as pd

ROOT = Path(r"d:\purple hack")
SRC = ROOT / "Brigade_Bangalore_10_April_26 (1)bc6219c.csv"
OUT = ROOT / "store-intelligence" / "data" / "pos_transactions.csv"

df = pd.read_csv(SRC)

times = df.groupby("invoice_number").apply(
    lambda g: f"{g['order_date'].iloc[0]} {g['order_time'].iloc[0]}"
)

pos = (
    df.groupby("invoice_number")
    .agg(
        store_id=("store_id", "first"),
        basket_value_inr=("total_amount", "sum"),
    )
    .reset_index()
    .rename(columns={"invoice_number": "transaction_id"})
)

pos["timestamp"] = pd.to_datetime(times.values, format="%d-%m-%Y %H:%M:%S").strftime(
    "%Y-%m-%dT%H:%M:%SZ"
)

pos["basket_value_inr"] = pos["basket_value_inr"].round(2)
pos = pos[["store_id", "transaction_id", "timestamp", "basket_value_inr"]].sort_values(
    "timestamp"
)
OUT.parent.mkdir(parents=True, exist_ok=True)
pos.to_csv(OUT, index=False)

print(f"Wrote {len(pos)} transactions to {OUT}")
print(f"Time range: {pos['timestamp'].min()} -> {pos['timestamp'].max()}")
print(f"Total revenue: {pos['basket_value_inr'].sum():.2f} INR")
print(pos.head(3).to_string(index=False))
