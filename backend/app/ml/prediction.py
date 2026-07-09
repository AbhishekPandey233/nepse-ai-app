"""XGBoost baseline for next-day log-return prediction, on data_loader.load_symbol() output."""
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error
from xgboost import XGBRegressor

NON_FEATURE_COLS = ("date", "symbol", "close", "target")


def train_xgboost(df: pd.DataFrame) -> dict:
    data = df.copy()
    data["target"] = data["log_return"].shift(-1)  # next-day log_return
    data = data.iloc[:-1]  # drop trailing row whose target is NaN

    feature_cols = [
        c for c in data.columns
        if c not in NON_FEATURE_COLS and pd.api.types.is_numeric_dtype(data[c])
    ]

    split_idx = int(len(data) * 0.8)
    train, test = data.iloc[:split_idx], data.iloc[split_idx:]

    X_train, y_train = train[feature_cols], train["target"]
    X_test, y_test = test[feature_cols], test["target"]

    model = XGBRegressor(objective="reg:squarederror", random_state=42)
    model.fit(X_train, y_train)

    predictions = model.predict(X_test)

    rmse = float(np.sqrt(mean_squared_error(y_test, predictions)))
    mae = float(mean_absolute_error(y_test, predictions))
    directional_accuracy = float((np.sign(predictions) == np.sign(y_test)).mean() * 100)

    return {
        "model": model,
        "predictions": predictions.tolist(),
        "actual": y_test.tolist(),
        "dates": [d.strftime("%Y-%m-%d") for d in test["date"]],
        "metrics": {
            "rmse": rmse,
            "mae": mae,
            "directional_accuracy": directional_accuracy,
        },
    }
