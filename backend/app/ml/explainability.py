"""SHAP explainability for the XGBoost prediction model (prediction.train_xgboost)."""
import numpy as np
import pandas as pd
import shap


def explain_predictions(model, X: pd.DataFrame) -> dict:
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X)

    feature_names = list(X.columns)

    per_row_shap = [
        {name: float(value) for name, value in zip(feature_names, row)}
        for row in shap_values
    ]

    mean_abs_shap = np.abs(shap_values).mean(axis=0)
    feature_importance = sorted(
        (
            {"feature": name, "mean_abs_shap": float(value)}
            for name, value in zip(feature_names, mean_abs_shap)
        ),
        key=lambda item: item["mean_abs_shap"],
        reverse=True,
    )

    return {"per_row_shap": per_row_shap, "feature_importance": feature_importance}
