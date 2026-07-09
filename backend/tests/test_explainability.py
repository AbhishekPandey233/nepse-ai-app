"""assert-based self-check for ml/explainability.py — run with: python tests/test_explainability.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ml.data_loader import load_symbol
from app.ml.explainability import explain_predictions
from app.ml.prediction import _feature_cols, _with_target, train_xgboost


def test_explain_predictions_real_symbol():
    df = load_symbol("nabil")
    result = train_xgboost(df)
    model = result["model"]

    # rebuild the same test-set feature frame train_xgboost used internally
    data = _with_target(df)
    feature_cols = _feature_cols(data)
    split_idx = int(len(data) * 0.8)
    X_test = data.iloc[split_idx:][feature_cols]

    explanation = explain_predictions(model, X_test)

    assert set(explanation.keys()) == {"per_row_shap", "feature_importance"}

    per_row_shap = explanation["per_row_shap"]
    assert len(per_row_shap) == len(X_test)
    assert all(isinstance(row, dict) for row in per_row_shap)
    assert set(per_row_shap[0].keys()) == set(feature_cols)
    assert all(isinstance(v, float) for v in per_row_shap[0].values())

    importance = explanation["feature_importance"]
    assert len(importance) == len(feature_cols)
    assert all(set(item.keys()) == {"feature", "mean_abs_shap"} for item in importance)
    assert {item["feature"] for item in importance} == set(feature_cols)

    values = [item["mean_abs_shap"] for item in importance]
    assert values == sorted(values, reverse=True), "feature_importance must be sorted descending"
    assert all(v >= 0 for v in values)

    print("test_explain_predictions_real_symbol passed. Top feature:", importance[0])


if __name__ == "__main__":
    test_explain_predictions_real_symbol()
