from anyio import to_thread
from fastapi import APIRouter, HTTPException

from app.ml.data_loader import load_symbol
from app.ml.prediction import train_xgboost
from app.utils.cache import CACHE_COLLECTION, build_cache_key, get_cached, set_cached

router = APIRouter()


def _compute(ticker: str) -> dict:
    df = load_symbol(ticker)
    result = train_xgboost(df)
    return {k: v for k, v in result.items() if k != "model"}  # model object isn't JSON/Mongo-serializable


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
