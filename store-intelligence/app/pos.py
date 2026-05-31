"""POS transaction loading — see docs/context/04-pos-and-business-logic.md"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from functools import lru_cache
from pathlib import Path

import pandas as pd

from app.config import CONVERSION_WINDOW_SECONDS, POS_CSV_PATH


@dataclass(frozen=True)
class PosTransaction:
    store_id: str
    transaction_id: str
    timestamp: datetime
    basket_value_inr: float


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)


@lru_cache(maxsize=1)
def load_pos_transactions(csv_path: str | None = None) -> tuple[PosTransaction, ...]:
    path = Path(csv_path) if csv_path else POS_CSV_PATH
    if not path.exists():
        return ()
    df = pd.read_csv(path)
    rows: list[PosTransaction] = []
    for _, row in df.iterrows():
        rows.append(
            PosTransaction(
                store_id=str(row["store_id"]),
                transaction_id=str(row["transaction_id"]),
                timestamp=_parse_timestamp(str(row["timestamp"])),
                basket_value_inr=float(row["basket_value_inr"]),
            )
        )
    return tuple(rows)


def get_transactions_for_store_date(
    store_id: str, target_date: date, csv_path: str | None = None
) -> list[PosTransaction]:
    return [
        txn
        for txn in load_pos_transactions(csv_path)
        if txn.store_id == store_id and txn.timestamp.date() == target_date
    ]


def conversion_window_start(txn_time: datetime) -> datetime:
    return txn_time - timedelta(seconds=CONVERSION_WINDOW_SECONDS)
