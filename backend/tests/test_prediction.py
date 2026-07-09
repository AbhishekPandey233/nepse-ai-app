"""assert-based self-check for ml/prediction.py — run with: python tests/test_prediction.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ml.data_loader import load_symbol
from app.ml.prediction import train_xgboost


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


if __name__ == "__main__":
    test_train_xgboost_real_symbol()
