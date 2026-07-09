"""Mongo-backed cache for ml/ results, keyed by ticker + source parquet's last-modified time."""
from pathlib import Path

from app.core.db import get_database

CACHE_COLLECTION = "analysis_cache"
PARQUET_PATH = Path(__file__).resolve().parents[2] / "data" / "processed" / "nepse_history.parquet"


def build_cache_key(ticker: str) -> str:
    mtime = PARQUET_PATH.stat().st_mtime
    return f"{ticker.upper()}:{mtime}"


async def get_cached(collection_name: str, key: str) -> dict | None:
    doc = await get_database()[collection_name].find_one({"_id": key})
    if doc is None:
        return None
    doc.pop("_id", None)
    return doc


async def set_cached(collection_name: str, key: str, value: dict) -> None:
    await get_database()[collection_name].update_one({"_id": key}, {"$set": value}, upsert=True)
