"""assert-based self-check for ml/prediction.py — run with: python tests/test_prediction.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ml.data_loader import load_symbol
from app.ml.prediction import build_sequences, train_lstm, train_xgboost


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

    print("test_train_xgboost_real_symbol passed:", metrics)


def test_build_sequences_shape():
    df = load_symbol("nabil")
    from app.ml.prediction import _with_target

    data = _with_target(df)
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


if __name__ == "__main__":
    test_train_xgboost_real_symbol()
    test_build_sequences_shape()
    test_train_lstm_real_symbol()
