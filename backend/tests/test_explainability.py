"""assert-based self-check for ml/explainability.py — run with: python tests/test_explainability.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ml.data_loader import load_symbol
from app.ml.explainability import explain_predictions
from app.ml.prediction import feature_cols as get_feature_cols
from app.ml.prediction import train_xgboost, with_target


def test_explain_predictions_real_symbol():
    df = load_symbol("nabil")
    result = train_xgboost(df)
    model = result["model"]

    # rebuild the same test-set feature frame train_xgboost used internally
    data = with_target(df)
    cols = get_feature_cols(data)
    split_idx = int(len(data) * 0.8)
    X_test = data.iloc[split_idx:][cols]

    explanation = explain_predictions(model, X_test)

    assert set(explanation.keys()) == {"per_row_shap", "feature_importance", "base_value"}
    assert isinstance(explanation["base_value"], float)

    per_row_shap = explanation["per_row_shap"]
    assert len(per_row_shap) == len(X_test)
    assert all(isinstance(row, dict) for row in per_row_shap)
    assert set(per_row_shap[0].keys()) == set(cols)
    assert all(isinstance(v, float) for v in per_row_shap[0].values())

    importance = explanation["feature_importance"]
    assert len(importance) == len(cols)
    assert all(set(item.keys()) == {"feature", "mean_abs_shap"} for item in importance)
    assert {item["feature"] for item in importance} == set(cols)

    values = [item["mean_abs_shap"] for item in importance]
    assert values == sorted(values, reverse=True), "feature_importance must be sorted descending"
    assert all(v >= 0 for v in values)

    print("test_explain_predictions_real_symbol passed. Top feature:", importance[0])


def test_shap_additivity_real_row():
    """Spot-check base_value + sum(shap_values) against the model's own prediction for a
    specific real row (NABIL, 2026-07-06), printing both so the match is visible directly."""
    df = load_symbol("nabil")
    result = train_xgboost(df)
    model = result["model"]

    data = with_target(df)
    cols = get_feature_cols(data)
    split_idx = int(len(data) * 0.8)
    test = data.iloc[split_idx:]
    X_test = test[cols]

    target_date = "2026-07-06"
    dates = test["date"].dt.strftime("%Y-%m-%d").tolist()
    assert target_date in dates, f"{target_date} not in this symbol's test period"
    pos = dates.index(target_date)

    explanation = explain_predictions(model, X_test)
    row_shap = explanation["per_row_shap"][pos]
    base_value = explanation["base_value"]

    model_prediction = float(model.predict(X_test.iloc[[pos]])[0])
    reconstructed = base_value + sum(row_shap.values())

    print(f"NABIL {target_date}: model prediction = {model_prediction}")
    print(f"NABIL {target_date}: base_value + sum(shap) = {reconstructed}")
    print(f"NABIL {target_date}: difference = {abs(model_prediction - reconstructed)}")

    assert abs(model_prediction - reconstructed) < 1e-4, "SHAP values don't reconstruct the model's prediction"
    print("test_shap_additivity_real_row passed")


if __name__ == "__main__":
    test_explain_predictions_real_symbol()
    test_shap_additivity_real_row()
