"""assert-based self-check for ml/prediction.py — run with: python tests/test_prediction.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from app.ml.data_loader import load_symbol
from app.ml.prediction import (
    _metrics,
    build_sequences,
    combine_model_comparison,
    feature_cols,
    predict_arima,
    predict_naive,
    train_lstm,
    train_xgboost,
    with_target,
)


def test_train_xgboost_real_symbol():
    df = load_symbol("nabil")
    result = train_xgboost(df)

    n = len(df) - 1
    split_idx = int(n * 0.8)
    expected_test_len = n - split_idx
    assert len(result["predictions"]) == len(result["actual"]) == len(result["dates"]) == expected_test_len

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
    close = 100 + np.arange(n) * 0.3 + rng.normal(0, 0.05, n)

    df = pd.DataFrame({"date": dates, "symbol": "TREND", "close": close})
    df["log_return"] = np.log(df["close"] / df["close"].shift(1))
    df["ma_5"] = df["close"].rolling(5).mean()
    df["ma_10"] = df["close"].rolling(10).mean()
    df["lag_return_1"] = df["log_return"].shift(1)
    df["lag_return_2"] = df["log_return"].shift(2)
    df["s_no"] = range(1, n + 1)
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


def test_baselines_share_xgboost_test_split():
    """Naive and ARIMA must be scored on the EXACT same held-out actuals/dates as XGBoost, or the
    RQ3 comparison isn't apples-to-apples. This is the property the whole comparison hinges on."""
    df = load_symbol("nabil")
    xgb = train_xgboost(df)
    naive = predict_naive(df)
    arima = predict_arima(df)

    for baseline, name in [(naive, "naive"), (arima, "arima")]:
        assert baseline["dates"] == xgb["dates"], f"{name} dates diverge from xgboost"
        assert baseline["actual"] == xgb["actual"], f"{name} actuals diverge from xgboost"
        assert len(baseline["predictions"]) == len(baseline["actual"])
        m = baseline["metrics"]
        assert m["rmse"] >= 0 and m["mae"] >= 0 and 0 <= m["directional_accuracy"] <= 100

    assert naive["variant"] in ("persistence", "no_change")
    assert set(naive["variants"]) == {"persistence", "no_change"}
    print("test_baselines_share_xgboost_test_split passed:",
          {"naive": naive["metrics"]["rmse"], "arima": arima["metrics"]["rmse"], "xgb": xgb["metrics"]["rmse"]})


def test_predict_naive_persistence_beats_nothing_on_trend():
    """On a clean uptrend, next-day direction is near-perfectly predictable, so the naive
    persistence baseline's directional accuracy must be high -- a guard on the alignment math."""
    df = _build_trending_series()
    naive = predict_naive(df)
    assert naive["metrics"]["directional_accuracy"] > 90, naive["metrics"]
    print("test_predict_naive_persistence_beats_nothing_on_trend passed:", naive["metrics"])


def test_combine_model_comparison_returns_all_four():
    result = combine_model_comparison("nabil")
    assert result["ticker"] == "NABIL"
    assert set(result["models"]) == {"naive", "arima", "xgboost", "lstm"}
    for name in ("naive", "arima", "xgboost"):
        assert "metrics" in result["models"][name], name
    print("test_combine_model_comparison_returns_all_four passed")


def test_metrics_excludes_flat_days_from_directional_accuracy():
    """Flat/no-change days (actual == 0, common in thinly-traded NEPSE stocks) have no real
    direction to predict. np.sign(0) == 0 can never match a nonzero prediction, so counting
    them as automatic misses artificially deflates the metric -- they must be excluded."""
    actual = np.array([0.01, -0.01, 0.0, 0.0, 0.02])
    predictions = np.array([0.005, -0.02, 0.5, -0.5, -0.01])

    result = _metrics(actual, predictions)

    expected = 200 / 3
    assert abs(result["directional_accuracy"] - expected) < 1e-9, result["directional_accuracy"]
    print("test_metrics_excludes_flat_days_from_directional_accuracy passed")


if __name__ == "__main__":
    test_train_xgboost_real_symbol()
    test_build_sequences_shape()
    test_train_lstm_real_symbol()
    test_s_no_excluded_from_features()
    test_directional_accuracy_on_trending_series()
    test_baselines_share_xgboost_test_split()
    test_predict_naive_persistence_beats_nothing_on_trend()
    test_combine_model_comparison_returns_all_four()
    test_metrics_excludes_flat_days_from_directional_accuracy()
