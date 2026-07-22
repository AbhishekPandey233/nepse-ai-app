"""assert-based self-check for ml/backtest.py — run with: python tests/test_backtest.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from app.ml.backtest import run_backtest


def test_zero_cost_always_long_equals_buy_and_hold():
    """With no costs and an always-long signal, the strategy is buy-and-hold by construction."""
    predictions = {"predictions": [1.0, 1.0, 1.0], "actual": [0.01, -0.02, 0.03], "dates": ["d1", "d2", "d3"]}
    r = run_backtest(None, predictions, transaction_cost_pct=0.0)

    assert abs(r["strategy_total_return"] - r["buy_hold_total_return"]) < 1e-12
    assert r["n_trades"] == 1
    assert r["outperformed"] is False
    print("test_zero_cost_always_long_equals_buy_and_hold passed")


def test_costs_drag_always_long_below_buy_and_hold():
    predictions = {"predictions": [1.0, 1.0, 1.0], "actual": [0.01, -0.02, 0.03], "dates": ["d1", "d2", "d3"]}
    r = run_backtest(None, predictions, transaction_cost_pct=0.5)

    assert r["strategy_total_return"] < r["buy_hold_total_return"]
    assert r["n_trades"] == 1
    assert "did not outperform" in r["verdict"]
    print("test_costs_drag_always_long_below_buy_and_hold passed")


def test_perfect_signal_beats_buy_and_hold():
    """Long only on up-days, flat on down-days: must beat buy-and-hold, which eats the down-days."""
    actual = [0.02, -0.01, 0.03, -0.02]
    predicted = [1.0, -1.0, 1.0, -1.0]
    predictions = {"predictions": predicted, "actual": actual, "dates": ["d1", "d2", "d3", "d4"]}
    r = run_backtest(None, predictions, transaction_cost_pct=0.1)

    assert r["strategy_total_return"] > r["buy_hold_total_return"]
    assert r["outperformed"] is True
    assert "outperformed" in r["verdict"]

    market = np.exp(np.asarray(actual)) - 1.0
    expected_bh = float(np.cumprod(1 + market)[-1] - 1)
    assert abs(r["buy_hold_total_return"] - expected_bh) < 1e-12
    print("test_perfect_signal_beats_buy_and_hold passed")


def test_series_lengths_match_dates():
    predictions = {"predictions": [1.0, -1.0, 1.0], "actual": [0.01, 0.02, -0.01], "dates": ["a", "b", "c"]}
    r = run_backtest(None, predictions)
    assert len(r["strategy_cumulative"]) == len(r["buy_hold_cumulative"]) == len(r["dates"]) == 3
    print("test_series_lengths_match_dates passed")


if __name__ == "__main__":
    test_zero_cost_always_long_equals_buy_and_hold()
    test_costs_drag_always_long_below_buy_and_hold()
    test_perfect_signal_beats_buy_and_hold()
    test_series_lengths_match_dates()
