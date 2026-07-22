"""Offline precompute of the market-wide efficiency/volatility summary.

Picks the top-N symbols by total turnover from the parquet, runs build_market_summary over them
(slow -- GARCH + efficiency tests per symbol), and stores ONE overwritten document in MongoDB for
/api/market-summary to serve instantly.

Run from backend/:  python scripts/build_market_summary.py           (top 50 by turnover)
                    python scripts/build_market_summary.py --n 100   (wider universe)
"""
import argparse
import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.db import get_database
from app.ml.market_summary import build_market_summary
from app.utils.cache import MARKET_SUMMARY_COLLECTION, MARKET_SUMMARY_ID, PARQUET_PATH


def top_turnover_symbols(n: int) -> list[str]:
    """The n symbols with the highest total traded value -- the most economically relevant slice of
    the market to anchor a market-level claim on, and the ones with enough data to model."""
    df = pd.read_parquet(PARQUET_PATH, columns=["symbol", "turnover"])
    totals = df.groupby("symbol")["turnover"].sum().sort_values(ascending=False)
    return totals.head(n).index.tolist()


async def main(n: int) -> None:
    symbols = top_turnover_symbols(n)
    print(f"Building market summary for top {len(symbols)} symbols by turnover...")

    summary = build_market_summary(symbols)
    summary["generated_at"] = datetime.now(timezone.utc).isoformat()
    summary["symbol_universe"] = {"selection": "top_turnover", "requested": n, "resolved": len(symbols)}

    db = get_database()
    await db[MARKET_SUMMARY_COLLECTION].replace_one(
        {"_id": MARKET_SUMMARY_ID}, {"_id": MARKET_SUMMARY_ID, **summary}, upsert=True
    )

    print(
        f"Saved '{MARKET_SUMMARY_ID}': {summary['n_symbols_processed']} processed, "
        f"{summary['n_symbols_skipped']} skipped, {summary['pct_against_efficiency']}% show evidence "
        f"against weak-form efficiency, mean GARCH persistence "
        f"{summary['garch_persistence']['mean']}"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=50, help="number of top-turnover symbols (default 50)")
    args = parser.parse_args()
    asyncio.run(main(args.n))
