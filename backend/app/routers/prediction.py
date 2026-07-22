from anyio import to_thread
from fastapi import APIRouter, HTTPException

from app.ml.backtest import run_backtest
from app.ml.data_loader import load_symbol
from app.ml.market_summary import rolling_efficiency_vs_accuracy
from app.ml.prediction import combine_model_comparison, train_xgboost
from app.utils.cache import CACHE_COLLECTION, build_cache_key, get_cached, set_cached

router = APIRouter()


def _strip_model(result: dict) -> dict:
    return {k: v for k, v in result.items() if k != "model"}


def _compute(ticker: str) -> dict:
    df = load_symbol(ticker)
    return _strip_model(train_xgboost(df))


def _compute_backtest(ticker: str, transaction_cost: float) -> dict:
    df = load_symbol(ticker)
    predictions = _strip_model(train_xgboost(df))
    return run_backtest(df, predictions, transaction_cost_pct=transaction_cost)


def _compute_rolling_impact(ticker: str, window: int) -> dict:
    df = load_symbol(ticker)
    return rolling_efficiency_vs_accuracy(df, window=window)


@router.get("/api/predict")
async def get_prediction(ticker: str):
    key = f"predict:{build_cache_key(ticker)}"

    cached = await get_cached(CACHE_COLLECTION, key)
    if cached is not None:
        return cached

    try:
        result = await to_thread.run_sync(_compute, ticker)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    await set_cached(CACHE_COLLECTION, key, result)
    return result


@router.get("/api/predict/compare")
async def compare_models(ticker: str):
    """Naive + ARIMA (traditional) vs XGBoost + LSTM (AI), same test split, for RQ3."""
    key = f"predict-compare:{build_cache_key(ticker)}"

    cached = await get_cached(CACHE_COLLECTION, key)
    if cached is not None:
        return cached

    try:
        result = await to_thread.run_sync(combine_model_comparison, ticker)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    await set_cached(CACHE_COLLECTION, key, result)
    return result


@router.get("/api/predict/backtest")
async def backtest(ticker: str, transaction_cost: float = 0.5):
    """Cumulative return of a long/flat strategy on the model's signal vs buy-and-hold, net of costs."""
    key = f"backtest:{build_cache_key(ticker)}:{transaction_cost}"

    cached = await get_cached(CACHE_COLLECTION, key)
    if cached is not None:
        return cached

    try:
        result = await to_thread.run_sync(_compute_backtest, ticker, transaction_cost)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    await set_cached(CACHE_COLLECTION, key, result)
    return result


@router.get("/api/predict/rolling-impact")
async def rolling_impact(ticker: str, window: int = 60):
    """Rolling-window correlation of prediction accuracy against market inefficiency & volatility."""
    key = f"rolling-impact:{build_cache_key(ticker)}:{window}"

    cached = await get_cached(CACHE_COLLECTION, key)
    if cached is not None:
        return cached

    try:
        result = await to_thread.run_sync(_compute_rolling_impact, ticker, window)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    await set_cached(CACHE_COLLECTION, key, result)
    return result
