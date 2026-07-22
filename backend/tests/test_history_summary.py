"""assert-based self-check for ml/history_summary.py — run with: python tests/test_history_summary.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from app.ml.data_loader import load_symbol
from app.ml.history_summary import summarize_history


def _build_synthetic_history():
    dates = pd.bdate_range("2024-01-01", periods=100)
    close = np.full(100, 100.0)
    close[50] = 130.0
    close[51] = 100.0
    close[30] = 80.0

    df = pd.DataFrame({"date": dates, "close": close})
    df["log_return"] = np.log(df["close"] / df["close"].shift(1))
    df["volatility_20"] = df["log_return"].rolling(20).std()
    return df.dropna().reset_index(drop=True)


def test_summarize_history_synthetic():
    df = _build_synthetic_history()
    summary = summarize_history(df)

    assert summary["highest_close"]["price"] == 130.0
    assert summary["highest_close"]["date"] == df.loc[df["close"].idxmax(), "date"].strftime("%Y-%m-%d")
    assert summary["lowest_close"]["price"] == 80.0

    assert summary["top_gains"][0]["return_pct"] > 0
    assert summary["top_losses"][0]["return_pct"] < 0

    assert len(summary["top_gains"]) == 3
    assert len(summary["top_losses"]) == 3

    for period in summary["high_volatility_periods"]:
        assert period["start"] <= period["end"]

    print("test_summarize_history_synthetic passed:", summary["highest_close"], summary["lowest_close"])


def test_summarize_history_real_symbol():
    df = load_symbol("nabil")
    summary = summarize_history(df)

    for key in (
        "period_start", "period_end", "overall_return_pct", "highest_close", "lowest_close",
        "top_gains", "top_losses", "high_volatility_periods", "high_volatility_threshold",
    ):
        assert key in summary

    assert summary["highest_close"]["price"] >= summary["lowest_close"]["price"]
    assert len(summary["top_gains"]) == 3
    assert len(summary["top_losses"]) == 3
    assert isinstance(summary["high_volatility_periods"], list)
    assert summary["high_volatility_threshold"] > 0

    print("test_summarize_history_real_symbol passed:", summary["overall_return_pct"], "% over the period")


if __name__ == "__main__":
    test_summarize_history_synthetic()
    test_summarize_history_real_symbol()
