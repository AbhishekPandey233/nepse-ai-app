"""assert-based self-check for ml/market_summary.py — run with: python tests/test_market_summary.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ml.data_loader import load_symbol
from app.ml.market_summary import (
    _pearson,
    _summary_stats,
    build_market_summary,
    rolling_efficiency_vs_accuracy,
)


def test_summary_stats_basic():
    s = _summary_stats([1.0, 2.0, 3.0])
    assert s["n"] == 3
    assert s["mean"] == 2.0
    assert s["median"] == 2.0
    assert s["min"] == 1.0 and s["max"] == 3.0
    print("test_summary_stats_basic passed")


def test_summary_stats_empty():
    s = _summary_stats([])
    assert s["n"] == 0 and s["mean"] is None
    print("test_summary_stats_empty passed")


def test_build_market_summary_real_symbols():
    summary = build_market_summary(["nabil", "adbl", "NOTASYMBOL123"])

    assert summary["n_symbols_processed"] == 2, summary["n_symbols_processed"]
    assert summary["n_symbols_skipped"] == 1
    assert summary["skipped"][0]["symbol"] == "NOTASYMBOL123"

    assert 0 <= summary["pct_against_efficiency"] <= 100
    assert summary["n_against_efficiency"] <= summary["n_symbols_processed"]

    for key in ("adf_stat", "variance_ratio", "garch_persistence"):
        assert summary[key]["n"] == 2, key
        assert summary[key]["mean"] is not None

    assert summary["garch_persistence"]["mean"] >= 0

    assert len(summary["per_symbol"]) == 2
    assert {r["symbol"] for r in summary["per_symbol"]} == {"NABIL", "ADBL"}
    for row in summary["per_symbol"]:
        assert isinstance(row["against_efficiency"], bool)

    print("test_build_market_summary_real_symbols passed:",
          {"pct_against": summary["pct_against_efficiency"],
           "mean_persistence": round(summary["garch_persistence"]["mean"], 3)})


def test_pearson_basics():
    assert _pearson([1, 2, 3], [2, 4, 6]) > 0.999
    assert _pearson([1, 2, 3], [6, 4, 2]) < -0.999
    assert _pearson([1, 1, 1], [1, 2, 3]) is None
    assert _pearson([1, 2], [1, 2]) is None
    print("test_pearson_basics passed")


def test_rolling_efficiency_vs_accuracy_real_symbol():
    df = load_symbol("nabil")
    result = rolling_efficiency_vs_accuracy(df, window=30)

    assert result["window"] == 30
    assert result["n_windows"] > 0, "nabil's test period should be long enough for 30-day windows"

    s = result["series"]
    n = result["n_windows"]
    for key in ("dates", "directional_accuracy", "variance_ratio", "inefficiency", "volatility"):
        assert len(s[key]) == n, f"{key} length {len(s[key])} != n_windows {n}"

    for name, r in result["correlations"].items():
        assert r is None or (-1.0 <= r <= 1.0), f"{name}={r}"

    assert all(v is None or v >= 0 for v in s["volatility"])

    print("test_rolling_efficiency_vs_accuracy_real_symbol passed:", result["correlations"], "n=", n)


def test_rolling_returns_empty_when_window_too_large():
    df = load_symbol("nabil")
    result = rolling_efficiency_vs_accuracy(df, window=100000)
    assert result["n_windows"] == 0
    assert result["correlations"]["inefficiency_vs_accuracy"] is None
    assert "message" in result
    print("test_rolling_returns_empty_when_window_too_large passed")


if __name__ == "__main__":
    test_summary_stats_basic()
    test_summary_stats_empty()
    test_pearson_basics()
    test_build_market_summary_real_symbols()
    test_rolling_efficiency_vs_accuracy_real_symbol()
    test_rolling_returns_empty_when_window_too_large()
