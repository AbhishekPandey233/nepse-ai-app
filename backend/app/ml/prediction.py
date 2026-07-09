"""XGBoost baseline + LSTM comparison for next-day log-return prediction, on data_loader.load_symbol() output."""
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor

NON_FEATURE_COLS = ("date", "symbol", "close", "target")


def _with_target(df: pd.DataFrame) -> pd.DataFrame:
    """Add the next-day log_return target column and drop the trailing NaN row."""
    data = df.copy()
    data["target"] = data["log_return"].shift(-1)
    return data.iloc[:-1].reset_index(drop=True)


def _feature_cols(data: pd.DataFrame) -> list:
    return [c for c in data.columns if c not in NON_FEATURE_COLS and pd.api.types.is_numeric_dtype(data[c])]


def _metrics(actual, predictions) -> dict:
    actual, predictions = np.asarray(actual), np.asarray(predictions)
    return {
        "rmse": float(np.sqrt(mean_squared_error(actual, predictions))),
        "mae": float(mean_absolute_error(actual, predictions)),
        "directional_accuracy": float((np.sign(predictions) == np.sign(actual)).mean() * 100),
    }


def train_xgboost(df: pd.DataFrame) -> dict:
    data = _with_target(df)
    feature_cols = _feature_cols(data)

    split_idx = int(len(data) * 0.8)
    train, test = data.iloc[:split_idx], data.iloc[split_idx:]

    X_train, y_train = train[feature_cols], train["target"]
    X_test, y_test = test[feature_cols], test["target"]

    model = XGBRegressor(objective="reg:squarederror", random_state=42)
    model.fit(X_train, y_train)

    predictions = model.predict(X_test)

    return {
        "model": model,
        "predictions": predictions.tolist(),
        "actual": y_test.tolist(),
        "dates": [d.strftime("%Y-%m-%d") for d in test["date"]],
        "metrics": _metrics(y_test, predictions),
    }


def build_sequences(data: pd.DataFrame, lookback: int = 10) -> tuple:
    """Slide a `lookback`-day window over `data` (output of _with_target) into a 3D
    (samples, timesteps, features) array. Each window of rows [i-lookback+1 .. i]
    predicts the target sitting on row i (next-day log_return as of that day)."""
    feature_cols = _feature_cols(data)
    # ponytail: some raw columns (conf, ltp, close_ltp...) are legitimately blank in the source
    # CSVs on some days; XGBoost handles NaN natively but the LSTM can't, so impute here only.
    feature_df = data[feature_cols].ffill().bfill().fillna(0)
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

    data = _with_target(df)
    split_idx = int(len(data) * 0.8)  # same split point/proportion as train_xgboost
    train_df = data.iloc[:split_idx].reset_index(drop=True)
    test_df = data.iloc[split_idx:].reset_index(drop=True)

    X_train, y_train, _ = build_sequences(train_df, lookback)
    X_test, y_test, test_dates = build_sequences(test_df, lookback)

    n_features = X_train.shape[2]
    scaler = StandardScaler().fit(X_train.reshape(-1, n_features))  # fit on train only, avoid leakage
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
