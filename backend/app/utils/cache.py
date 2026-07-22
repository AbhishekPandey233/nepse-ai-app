"""Mongo-backed cache for ml/ results, keyed by ticker + source parquet's last-modified time."""
import re
from pathlib import Path

from app.core.db import get_database

CACHE_COLLECTION = "analysis_cache"
MARKET_SUMMARY_COLLECTION = "market_summary"
MARKET_SUMMARY_ID = "latest"
PARQUET_PATH = Path(__file__).resolve().parents[2] / "data" / "processed" / "nepse_history.parquet"

CHAT_CONTEXT_PREFIXES = ("efficiency", "volatility", "predict", "explain", "history", "backtest")


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


async def get_all_cached_for_ticker(ticker: str) -> dict:
    """Every cached raw result for `ticker` (this parquet version), keyed by module name, so the
    chat can answer cross-module questions regardless of which page they were asked from. Modules
    with nothing cached yet are simply absent -- never an error.

    `predict` matches only `predict:...`, not `predict-compare:...`, because the alternation is
    followed by a literal colon; `backtest` matches despite its trailing `:cost` since the pattern
    is a prefix (no end anchor).
    """
    key_suffix = build_cache_key(ticker)
    pattern = f"^({'|'.join(CHAT_CONTEXT_PREFIXES)}):{re.escape(key_suffix)}"

    bundle = {}
    cursor = get_database()[CACHE_COLLECTION].find({"_id": {"$regex": pattern}})
    async for doc in cursor:
        module = doc["_id"].split(":", 1)[0]
        doc.pop("_id", None)
        bundle[module] = doc
    return bundle
