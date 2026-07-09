"""POST /api/explain-chat."""
from anyio import to_thread
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.ml.llm_explainer import OllamaUnavailableError, explain_results
from app.utils.cache import CACHE_COLLECTION, build_cache_key, get_cached

router = APIRouter()

# same prefixes routers/efficiency.py, volatility.py, prediction.py, explainability.py cache under
RESULT_PREFIXES = ("efficiency", "volatility", "predict", "explain")


class ChatRequest(BaseModel):
    ticker: str
    question: str | None = None


class ChatResponse(BaseModel):
    answer: str


@router.post("/api/explain-chat", response_model=ChatResponse)
async def explain_chat(payload: ChatRequest):
    key_suffix = build_cache_key(payload.ticker)

    results = {}
    for prefix in RESULT_PREFIXES:
        cached = await get_cached(CACHE_COLLECTION, f"{prefix}:{key_suffix}")
        if cached is not None:
            results[prefix] = cached

    if not results:
        raise HTTPException(
            status_code=404,
            detail=f"No cached analysis found for '{payload.ticker}'. Run the analysis endpoints first.",
        )

    try:
        answer = await to_thread.run_sync(explain_results, results, payload.question)
    except OllamaUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    return ChatResponse(answer=answer)
