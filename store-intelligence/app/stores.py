"""Store ID normalization — ST1008 and STORE_BLR_002 alias."""

from fastapi import HTTPException

KNOWN_STORES = frozenset({"ST1008", "STORE_BLR_002"})

_ALIASES = {
    "ST1008": "ST1008",
    "STORE_BLR_002": "ST1008",
}


def canonical_store_id(store_id: str) -> str:
    if store_id not in KNOWN_STORES:
        raise HTTPException(status_code=404, detail={"error": "store_not_found", "store_id": store_id})
    return _ALIASES[store_id]


def normalize_event_store_id(store_id: str) -> str:
    return _ALIASES.get(store_id, store_id)
