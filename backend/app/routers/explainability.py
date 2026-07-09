from anyio import to_thread
from fastapi import APIRouter, HTTPException

from app.ml.data_loader import load_symbol
from app.ml.explainability import explain_predictions
from app.ml.prediction import feature_cols, train_xgboost, with_target
from app.utils.cache import CACHE_COLLECTION, build_cache_key, get_cached, set_cached

router = APIRouter()


def _compute(ticker: str) -> dict:
    df = load_symbol(ticker)
    model = train_xgboost(df)["model"]  # only the cached predict endpoint persists this; retrain here

    data = with_target(df)
    cols = feature_cols(data)
    split_idx = int(len(data) * 0.8)
    X_test = data.iloc[split_idx:][cols]

    return explain_predictions(model, X_test)


@router.get("/api/explain")
async def get_explanation(ticker: str):
    key = f"explain:{build_cache_key(ticker)}"

    cached = await get_cached(CACHE_COLLECTION, key)
    if cached is not None:
        return cached

    try:
        result = await to_thread.run_sync(_compute, ticker)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    await set_cached(CACHE_COLLECTION, key, result)
    return result
