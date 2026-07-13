"""SHAP explainability for the XGBoost prediction model (prediction.train_xgboost)."""
import numpy as np
import pandas as pd
import shap


def explain_predictions(model, X: pd.DataFrame) -> dict:
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X)
    base_value = float(np.asarray(explainer.expected_value).ravel()[0])

    feature_names = list(X.columns)

    per_row_shap = [
        {name: float(value) for name, value in zip(feature_names, row)}
        for row in shap_values
    ]

    # SHAP's core guarantee: base_value + sum(shap_values for a row) == the model's raw
    # prediction for that row. Verify it holds so a future slicing/aggregation/unit-conversion
    # bug in this function would fail loudly here instead of silently reaching the frontend.
    predictions = model.predict(X)
    reconstructed = base_value + shap_values.sum(axis=1)
    max_diff = float(np.abs(predictions - reconstructed).max())
    assert max_diff < 1e-4, (
        f"SHAP additivity check failed: base_value + sum(shap) differs from the model's own "
        f"prediction by up to {max_diff} across {len(X)} rows -- per-row SHAP values may be "
        "sliced, aggregated, or unit-converted incorrectly before being returned."
    )

    mean_abs_shap = np.abs(shap_values).mean(axis=0)
    feature_importance = sorted(
        (
            {"feature": name, "mean_abs_shap": float(value)}
            for name, value in zip(feature_names, mean_abs_shap)
        ),
        key=lambda item: item["mean_abs_shap"],
        reverse=True,
    )

    return {"per_row_shap": per_row_shap, "feature_importance": feature_importance, "base_value": base_value}
