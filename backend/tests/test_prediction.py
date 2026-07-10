"""assert-based self-check for ml/prediction.py — run with: python tests/test_prediction.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from app.ml.data_loader import load_symbol
from app.ml.prediction import _metrics, build_sequences, feature_cols, train_lstm, train_xgboost, with_target


def test_train_xgboost_real_symbol():
    df = load_symbol("nabil")
    result = train_xgboost(df)

    n = len(df) - 1  # trailing row dropped for NaN target
    split_idx = int(n * 0.8)
    expected_test_len = n - split_idx
    assert len(result["predictions"]) == len(result["actual"]) == len(result["dates"]) == expected_test_len

    # dates must be the most recent 20% — never shuffled, time-ordered
    assert list(result["dates"]) == sorted(result["dates"]), "test set dates must stay in chronological order"
    assert result["dates"][0] == df["date"].iloc[split_idx].strftime("%Y-%m-%d")

    metrics = result["metrics"]
    assert metrics["rmse"] >= 0
    assert metrics["mae"] >= 0
    assert 0 <= metrics["directional_accuracy"] <= 100

    assert hasattr(result["model"], "predict"), "must return the trained model itself"

    forecast = result["next_day_forecast"]
    assert forecast["as_of_date"] == df["date"].iloc[-1].strftime("%Y-%m-%d")
    assert isinstance(forecast["predicted_return"], float)

    print("test_train_xgboost_real_symbol passed:", metrics)


def test_build_sequences_shape():
    df = load_symbol("nabil")
    from app.ml.prediction import with_target

    data = with_target(df)
    lookback = 10
    X, y, dates = build_sequences(data, lookback=lookback)

    assert X.shape[0] == len(data) - lookback + 1
    assert X.shape[1] == lookback
    assert X.shape[0] == len(y) == len(dates)

    # last window's target/date must match the last row's target/date directly
    assert y[-1] == data["target"].iloc[-1]
    assert dates[-1] == data["date"].iloc[-1]

    print("test_build_sequences_shape passed")


def test_train_lstm_real_symbol():
    df = load_symbol("nabil")
    lookback = 10
    result = train_lstm(df, lookback=lookback)

    n = len(df) - 1
    split_idx = int(n * 0.8)
    expected_test_len = (n - split_idx) - lookback + 1
    assert len(result["predictions"]) == len(result["actual"]) == len(result["dates"]) == expected_test_len

    assert list(result["dates"]) == sorted(result["dates"]), "test set dates must stay in chronological order"

    metrics = result["metrics"]
    assert metrics["rmse"] >= 0
    assert metrics["mae"] >= 0
    assert 0 <= metrics["directional_accuracy"] <= 100

    assert hasattr(result["model"], "predict"), "must return the trained model itself"

    print("test_train_lstm_real_symbol passed:", metrics)


def test_s_no_excluded_from_features():
    df = load_symbol("nabil")
    data = with_target(df)
    cols = feature_cols(data)

    assert "s_no" not in cols, "s_no is a per-day row index, not a market signal -- must never be a model input"
    print("test_s_no_excluded_from_features passed")


def _build_trending_series(n=300, seed=0):
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2024-01-01", periods=n)
    close = 100 + np.arange(n) * 0.3 + rng.normal(0, 0.05, n)  # steady uptrend, small noise

    df = pd.DataFrame({"date": dates, "symbol": "TREND", "close": close})
    df["log_return"] = np.log(df["close"] / df["close"].shift(1))
    df["ma_5"] = df["close"].rolling(5).mean()
    df["ma_10"] = df["close"].rolling(10).mean()
    df["lag_return_1"] = df["log_return"].shift(1)
    df["lag_return_2"] = df["log_return"].shift(2)
    df["s_no"] = range(1, n + 1)  # should be excluded as a feature regardless
    return df.dropna().reset_index(drop=True)


def test_directional_accuracy_on_trending_series():
    """Sanity check for the shift(-1) target logic: on a series that trends up nearly every
    day, next-day direction is trivially predictable, so directional accuracy must land well
    above 50%. If this ever comes out at/below 50%, the target/shift logic has regressed."""
    df = _build_trending_series()
    result = train_xgboost(df)

    accuracy = result["metrics"]["directional_accuracy"]
    assert accuracy > 90, f"expected well above 50% (near 100%) on a clean uptrend, got {accuracy}"
    print("test_directional_accuracy_on_trending_series passed:", accuracy)


def test_metrics_excludes_flat_days_from_directional_accuracy():
    """Flat/no-change days (actual == 0, common in thinly-traded NEPSE stocks) have no real
    direction to predict. np.sign(0) == 0 can never match a nonzero prediction, so counting
    them as automatic misses artificially deflates the metric -- they must be excluded."""
    actual = np.array([0.01, -0.01, 0.0, 0.0, 0.02])
    predictions = np.array([0.005, -0.02, 0.5, -0.5, -0.01])  # last one wrong, rest "correct"

    result = _metrics(actual, predictions)

    # only the 3 nonzero-actual rows count: 2 correct (indices 0, 1), 1 wrong (index 4)
    expected = 200 / 3
    assert abs(result["directional_accuracy"] - expected) < 1e-9, result["directional_accuracy"]
    print("test_metrics_excludes_flat_days_from_directional_accuracy passed")


if __name__ == "__main__":
    test_train_xgboost_real_symbol()
    test_build_sequences_shape()
    test_train_lstm_real_symbol()
    test_s_no_excluded_from_features()
    test_directional_accuracy_on_trending_series()
    test_metrics_excludes_flat_days_from_directional_accuracy()
