"""assert-based self-check for ml/data_loader.py — run with: python tests/test_data_loader.py"""
import math
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ml import data_loader


CLOSES = [100 + i * 0.7 for i in range(30)]


def _build_history() -> pd.DataFrame:
    # irregular gaps (not just weekends) to prove returns use consecutive rows, not consecutive calendar days
    dates = pd.bdate_range("2024-01-01", periods=40)
    dates = dates.delete([5, 6, 7, 20, 21])[:30]  # drop a few extra days to create bigger gaps
    closes = CLOSES

    test_symbol = pd.DataFrame({
        "date": dates,
        "symbol": "TEST",
        "close": closes,
        "vwap": [c * 0.99 for c in closes],
        "120_days": [c * 1.01 for c in closes],
        "180_days": [c * 1.02 for c in closes],
        "52_weeks_high": [max(closes)] * 30,
        "52_weeks_low": [min(closes)] * 30,
    })
    other_symbol = test_symbol.copy()
    other_symbol["symbol"] = "OTHER"
    return pd.concat([test_symbol, other_symbol], ignore_index=True)


def test_load_symbol():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "nepse_history.parquet"
        _build_history().to_parquet(path, index=False)

        data_loader.HISTORY_PATH = path
        data_loader._history_df = None  # reset module-level cache

        df = data_loader.load_symbol("test")  # lowercase, checks case-insensitive match

        assert df["date"].is_monotonic_increasing, "must be sorted by date ascending"
        assert df[data_loader.ENGINEERED_COLS].isna().sum().sum() == 0, "leading NaN rows should be dropped"

        # compare against the original 30-row close series (not df["close"], which has had
        # leading warmup rows dropped and no longer holds the full rolling-window history)
        expected_log_return = math.log(CLOSES[-1] / CLOSES[-2])
        assert math.isclose(df["log_return"].iloc[-1], expected_log_return), "log return must use consecutive rows"

        assert math.isclose(df["ma_5"].iloc[-1], np.mean(CLOSES[-5:]))
        assert math.isclose(df["ma_20"].iloc[-1], np.mean(CLOSES[-20:]))

        assert math.isclose(df["lag_return_1"].iloc[-1], df["log_return"].iloc[-2])
        assert math.isclose(df["lag_return_2"].iloc[-1], df["log_return"].iloc[-3])

        # vwap/120_days/etc must be passed through untouched, not recomputed
        assert math.isclose(df["vwap"].iloc[-1], CLOSES[-1] * 0.99)

        assert set(df["symbol"]) == {"TEST"}, "must not leak rows from other symbols"

        try:
            data_loader.load_symbol("NOPE")
            raise AssertionError("expected ValueError for unknown symbol")
        except ValueError:
            pass

    print("test_load_symbol passed")


if __name__ == "__main__":
    test_load_symbol()
