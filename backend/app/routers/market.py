"""GET /api/market-summary -- serves the precomputed market-wide summary document (read-only)."""
from fastapi import APIRouter, HTTPException

from app.utils.cache import MARKET_SUMMARY_COLLECTION, MARKET_SUMMARY_ID, get_cached

router = APIRouter()


@router.get("/api/market-summary")
async def get_market_summary():
    summary = await get_cached(MARKET_SUMMARY_COLLECTION, MARKET_SUMMARY_ID)
    if summary is None:
        raise HTTPException(
            status_code=404,
            detail="Market summary not built yet. Run scripts/build_market_summary.py first.",
        )
    return summary
