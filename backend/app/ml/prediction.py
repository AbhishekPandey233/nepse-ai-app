"""XGBoost + LSTM (AI) vs naive + ARIMA (traditional) next-day log-return prediction, on
data_loader.load_symbol() output. All four are scored on the identical time-ordered test split
so the comparison answers RQ3 (does AI-driven analysis outperform traditional approaches?)."""
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor

from app.ml.data_loader import load_symbol

NON_FEATURE_COLS = ("date", "symbol", "close", "target", "s_no")


def with_target(df: pd.DataFrame) -> pd.DataFrame:
    """Add the next-day log_return target column and drop the trailing NaN row."""
    data = df.copy()
    data["target"] = data["log_return"].shift(-1)
    return data.iloc[:-1].reset_index(drop=True)


def feature_cols(data: pd.DataFrame) -> list:
    return [c for c in data.columns if c not in NON_FEATURE_COLS and pd.api.types.is_numeric_dtype(data[c])]


def _metrics(actual, predictions) -> dict:
    actual, predictions = np.asarray(actual), np.asarray(predictions)

    nonzero = actual != 0
    directional_accuracy = (
        float((np.sign(predictions[nonzero]) == np.sign(actual[nonzero])).mean() * 100) if nonzero.any() else 0.0
    )

    return {
        "rmse": float(np.sqrt(mean_squared_error(actual, predictions))),
        "mae": float(mean_absolute_error(actual, predictions)),
        "directional_accuracy": directional_accuracy,
    }


def _test_split(df: pd.DataFrame) -> tuple:
    """The exact time-ordered test target/dates the XGBoost path predicts on, so every baseline
    is scored on identical (actual, date) pairs. Returns (returns, split_idx, actuals, dates).

    with_target() drops the trailing (target-less) row, then the split is 80/20 on what remains --
    identical boundary to train_xgboost. For a test row at index k the actual is next-day return
    returns[k+1] and the date is that row's own date, matching train_xgboost's test["target"]/["date"].
    """
    returns = df["log_return"].to_numpy(dtype=float)
    length = len(df)
    n = length - 1
    split_idx = int(n * 0.8)

    actuals = returns[split_idx + 1: length]
    dates = [d.strftime("%Y-%m-%d") for d in df["date"].iloc[split_idx: length - 1]]
    return returns, split_idx, actuals, dates


def predict_naive(df: pd.DataFrame) -> dict:
    """Naive persistence baseline (traditional, non-AI) on the same test split as train_xgboost.

    Two classic variants: 'persistence' (next return == today's return) and 'no_change' (next
    return == 0, i.e. a pure random walk in price). Reports the stronger of the two by RMSE as the
    headline naive comparator, with both metric sets kept under 'variants' for the write-up.
    """
    returns, split_idx, actuals, dates = _test_split(df)
    length = len(df)

    persistence = returns[split_idx: length - 1]
    no_change = np.zeros_like(actuals)

    variants = {
        "persistence": _metrics(actuals, persistence),
        "no_change": _metrics(actuals, no_change),
    }
    if variants["persistence"]["rmse"] <= variants["no_change"]["rmse"]:
        preds, variant = persistence, "persistence"
    else:
        preds, variant = no_change, "no_change"

    return {
        "predictions": np.asarray(preds).tolist(),
        "actual": actuals.tolist(),
        "dates": dates,
        "metrics": _metrics(actuals, preds),
        "variant": variant,
        "variants": variants,
    }


def predict_arima(df: pd.DataFrame, order: tuple = (1, 0, 1)) -> dict:
    """ARIMA baseline (traditional, non-AI) via statsmodels, on the same test split as train_xgboost.

    Rolling one-step-ahead forecast: fit ARIMA params once on the train returns, then walk the test
    window forecasting the next return and revealing the true value each step (append, no refit) --
    the standard honest way to score a time-series model out-of-sample.
    """
    import warnings

    from statsmodels.tsa.arima.model import ARIMA

    returns, split_idx, actuals, dates = _test_split(df)
    length = len(df)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = ARIMA(returns[: split_idx + 1], order=order).fit()
        preds = []
        for k in range(split_idx, length - 1):
            preds.append(float(res.forecast(1)[0]))
            if k < length - 2:
                res = res.append([returns[k + 1]], refit=False)

    preds = np.asarray(preds)
    return {
        "predictions": preds.tolist(),
        "actual": actuals.tolist(),
        "dates": dates,
        "metrics": _metrics(actuals, preds),
        "order": list(order),
    }


def train_xgboost(df: pd.DataFrame) -> dict:
    data = with_target(df)
    cols = feature_cols(data)

    split_idx = int(len(data) * 0.8)
    train, test = data.iloc[:split_idx], data.iloc[split_idx:]

    X_train, y_train = train[cols], train["target"]
    X_test, y_test = test[cols], test["target"]

    model = XGBRegressor(objective="reg:squarederror", random_state=42)
    model.fit(X_train, y_train)

    predictions = model.predict(X_test)

    last_row = df.iloc[[-1]][cols]
    next_day_return = float(model.predict(last_row)[0])

    return {
        "model": model,
        "predictions": predictions.tolist(),
        "actual": y_test.tolist(),
        "dates": [d.strftime("%Y-%m-%d") for d in test["date"]],
        "metrics": _metrics(y_test, predictions),
        "next_day_forecast": {
            "as_of_date": df["date"].iloc[-1].strftime("%Y-%m-%d"),
            "predicted_return": next_day_return,
        },
    }


def build_sequences(data: pd.DataFrame, lookback: int = 10) -> tuple:
    """Slide a `lookback`-day window over `data` (output of with_target) into a 3D
    (samples, timesteps, features) array. Each window of rows [i-lookback+1 .. i]
    predicts the target sitting on row i (next-day log_return as of that day)."""
    cols = feature_cols(data)
    feature_df = data[cols].ffill().bfill().fillna(0)
    features = feature_df.to_numpy(dtype=float)
    targets = data["target"].to_numpy(dtype=float)
    dates = data["date"].reset_index(drop=True)

    X, y, seq_dates = [], [], []
    for i in range(lookback - 1, len(data)):
        X.append(features[i - lookback + 1: i + 1])
        y.append(targets[i])
        seq_dates.append(dates.iloc[i])

    return np.array(X), np.array(y), seq_dates


def train_lstm(df: pd.DataFrame, lookback: int = 10) -> dict:
    from tensorflow.keras.layers import LSTM, Dense
    from tensorflow.keras.models import Sequential

    data = with_target(df)
    split_idx = int(len(data) * 0.8)
    train_df = data.iloc[:split_idx].reset_index(drop=True)
    test_df = data.iloc[split_idx:].reset_index(drop=True)

    X_train, y_train, _ = build_sequences(train_df, lookback)
    X_test, y_test, test_dates = build_sequences(test_df, lookback)

    n_features = X_train.shape[2]
    scaler = StandardScaler().fit(X_train.reshape(-1, n_features))
    X_train = scaler.transform(X_train.reshape(-1, n_features)).reshape(X_train.shape)
    X_test = scaler.transform(X_test.reshape(-1, n_features)).reshape(X_test.shape)

    model = Sequential([
        LSTM(32, input_shape=(lookback, n_features)),
        Dense(1),
    ])
    model.compile(optimizer="adam", loss="mse")
    model.fit(X_train, y_train, epochs=20, batch_size=32, verbose=0)

    predictions = model.predict(X_test, verbose=0).flatten()

    return {
        "model": model,
        "predictions": predictions.tolist(),
        "actual": y_test.tolist(),
        "dates": [d.strftime("%Y-%m-%d") for d in test_dates],
        "metrics": _metrics(y_test, predictions),
    }


def _strip_model(result: dict) -> dict:
    return {k: v for k, v in result.items() if k != "model"}


def combine_model_comparison(symbol: str) -> dict:
    """Run all four models -- naive + ARIMA (traditional) and XGBoost + LSTM (AI) -- on the same
    symbol and same test split, returning every metric set together for one side-by-side table (RQ3).

    LSTM is guarded: if TensorFlow is unavailable or fails, the traditional-vs-XGBoost comparison
    still returns rather than 500ing the whole endpoint.
    """
    df = load_symbol(symbol)

    models = {
        "naive": predict_naive(df),
        "arima": predict_arima(df),
        "xgboost": _strip_model(train_xgboost(df)),
    }
    try:
        models["lstm"] = _strip_model(train_lstm(df))
    except Exception as exc:
        models["lstm"] = {"error": str(exc)}

    return {"ticker": symbol.upper(), "models": models}
