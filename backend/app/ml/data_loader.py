"""Per-symbol load + feature engineering, built on top of ml/ingest.py's parquet output."""
from pathlib import Path

import numpy as np
import pandas as pd

HISTORY_PATH = Path(__file__).resolve().parents[2] / "data" / "processed" / "nepse_history.parquet"

_history_df: pd.DataFrame | None = None
_history_mtime: float | None = None

ENGINEERED_COLS = [
    "log_return", "ma_5", "ma_10", "ma_20", "rsi_14",
    "volatility_20", "lag_return_1", "lag_return_2", "lag_return_3",
]


def _load_history() -> pd.DataFrame:
    """Cached read of the parquet, auto-reloaded when the file changes on disk, so a rebuilt dataset
    is picked up by a running server without a restart. A stat() per call is negligible next to the
    analysis work it feeds."""
    global _history_df, _history_mtime
    mtime = HISTORY_PATH.stat().st_mtime
    if _history_df is None or mtime != _history_mtime:
        _history_df = pd.read_parquet(HISTORY_PATH)
        _history_mtime = mtime
    return _history_df


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    avg_gain = delta.clip(lower=0).rolling(period).mean()
    avg_loss = -delta.clip(upper=0).rolling(period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def latest_close(symbol: str) -> float | None:
    """Most recent close price for a symbol, or None if the symbol isn't in the dataset. Cheap
    (no feature engineering) -- used for portfolio mark-to-market."""
    history = _load_history()
    rows = history[history["symbol"].str.upper() == symbol.upper()]
    if rows.empty:
        return None
    return float(rows.sort_values("date")["close"].iloc[-1])


def load_symbol(symbol: str) -> pd.DataFrame:
    history = _load_history()
    df = history[history["symbol"].str.upper() == symbol.upper()].sort_values("date").reset_index(drop=True)

    if df.empty:
        raise ValueError(f"Symbol '{symbol}' not found in dataset")

    df["log_return"] = np.log(df["close"] / df["close"].shift(1))
    df["ma_5"] = df["close"].rolling(5).mean()
    df["ma_10"] = df["close"].rolling(10).mean()
    df["ma_20"] = df["close"].rolling(20).mean()
    df["rsi_14"] = _rsi(df["close"])
    df["volatility_20"] = df["log_return"].rolling(20).std()
    df["lag_return_1"] = df["log_return"].shift(1)
    df["lag_return_2"] = df["log_return"].shift(2)
    df["lag_return_3"] = df["log_return"].shift(3)

    df = df.dropna(subset=ENGINEERED_COLS).reset_index(drop=True)

    return df
