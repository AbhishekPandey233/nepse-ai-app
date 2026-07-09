"""Per-symbol load + feature engineering, built on top of ml/ingest.py's parquet output."""
from pathlib import Path

import numpy as np
import pandas as pd

HISTORY_PATH = Path(__file__).resolve().parents[2] / "data" / "processed" / "nepse_history.parquet"

_history_df: pd.DataFrame | None = None  # module-level cache, populated on first load

ENGINEERED_COLS = [
    "log_return", "ma_5", "ma_10", "ma_20", "rsi_14",
    "volatility_20", "lag_return_1", "lag_return_2", "lag_return_3",
]


def _load_history() -> pd.DataFrame:
    global _history_df
    if _history_df is None:
        _history_df = pd.read_parquet(HISTORY_PATH)
    return _history_df


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    avg_gain = delta.clip(lower=0).rolling(period).mean()
    avg_loss = -delta.clip(upper=0).rolling(period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


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
    # vwap, 120_days, 180_days, 52_weeks_high, 52_weeks_low already present from ingest.py

    df = df.dropna(subset=ENGINEERED_COLS).reset_index(drop=True)

    return df
