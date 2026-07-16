"""POST /api/explain-chat."""
import logging

from anyio import to_thread
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.ml.data_loader import load_symbol
from app.ml.history_summary import summarize_history
from app.ml.llm_explainer import (
    OllamaUnavailableError,
    explain_prediction_factors,
    explain_results,
    generate_sectioned_explanation,
)
from app.utils.cache import (
    CACHE_COLLECTION,
    build_cache_key,
    get_all_cached_for_ticker,
    get_cached,
    set_cached,
)

router = APIRouter()
logger = logging.getLogger("nepse-ai")


def _with_explicit_current_volatility(results: dict) -> dict:
    """Inject an unambiguous, top-level 'current' GARCH volatility figure into the merged
    results dict before it reaches the LLM.

    Without this, the merged context can contain BOTH volatility.conditional_volatility (the
    fitted/rescaled GARCH figure -- what VolatilityPage.jsx's "Current Risk Level" box shows)
    AND explain.per_row_shap[...]["volatility_20"] (an unrelated raw rolling-std FEATURE column
    used as a model input). The two have confusingly similar names, and the local LLM was
    observed grabbing the wrong one when asked about "current volatility". Giving it one
    clearly-labeled scalar, sourced from the exact same array the frontend reads, removes the
    ambiguity instead of hoping better prompt wording fixes it.
    """
    volatility_result = results.get("volatility")
    if not volatility_result or not volatility_result.get("conditional_volatility"):
        return results

    # same array + same index (last element) that VolatilityPage.jsx reads for its
    # "Current Risk Level" box, so backend and frontend agree by construction as long as
    # this value is actually sane
    current_volatility = volatility_result["conditional_volatility"][-1]

    assert isinstance(current_volatility, (int, float)) and current_volatility >= 0, (
        f"current_conditional_volatility_garch looks invalid: {current_volatility!r}"
    )
    logger.info(
        "explain-chat: current_conditional_volatility_garch=%s (matches VolatilityPage's "
        "'Current Risk Level' box, both read from conditional_volatility[-1])",
        current_volatility,
    )

    return {**results, "current_conditional_volatility_garch": current_volatility}


class ChatRequest(BaseModel):
    ticker: str
    question: str | None = None


class ChatResponse(BaseModel):
    answer: str


@router.post("/api/explain-chat", response_model=ChatResponse)
async def explain_chat(payload: ChatRequest):
    # full cross-module bundle (efficiency, volatility, prediction, SHAP, history, backtest -- whichever
    # exist) so a question asked on any page can still reference every other module's real numbers
    results = await get_all_cached_for_ticker(payload.ticker)

    if not results:
        raise HTTPException(
            status_code=404,
            detail=f"No cached analysis found for '{payload.ticker}'. Run the analysis endpoints first.",
        )

    results = _with_explicit_current_volatility(results)

    try:
        answer = await to_thread.run_sync(explain_results, results, payload.question)
    except OllamaUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    return ChatResponse(answer=answer)


@router.get("/api/explain-chat/factors", response_model=ChatResponse)
async def explain_chat_factors(ticker: str):
    """Long-form, example-rich explanation of the top SHAP factors behind the latest prediction
    for `ticker` -- distinct from /api/explain-chat's concise Q&A style."""
    key_suffix = build_cache_key(ticker)

    predict_result = await get_cached(CACHE_COLLECTION, f"predict:{key_suffix}")
    explain_result = await get_cached(CACHE_COLLECTION, f"explain:{key_suffix}")

    if not predict_result or not explain_result:
        raise HTTPException(
            status_code=404,
            detail=f"No cached prediction/explainability analysis found for '{ticker}'. "
            "Run the analysis endpoints first.",
        )

    cache_key = f"factors:{key_suffix}"
    cached = await get_cached(CACHE_COLLECTION, cache_key)
    if cached is not None:
        return cached

    try:
        answer = await to_thread.run_sync(explain_prediction_factors, ticker, predict_result, explain_result)
    except OllamaUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    result = {"answer": answer}
    await set_cached(CACHE_COLLECTION, cache_key, result)
    return result


def _history_payload(ticker: str) -> dict:
    df = load_symbol(ticker)
    return {"close": df["close"].tolist(), "summary": summarize_history(df)}


@router.get("/api/explain-chat/sections")
async def explain_chat_sections(ticker: str):
    """Three distinct, non-overlapping explanation sections (Risk Analysis / Historical Trends /
    Future Outlook), each with deterministic key_points + an Ollama narrative grounded in its own facts."""
    key_suffix = build_cache_key(ticker)

    volatility = await get_cached(CACHE_COLLECTION, f"volatility:{key_suffix}")
    predict = await get_cached(CACHE_COLLECTION, f"predict:{key_suffix}")

    if not volatility or not predict:
        raise HTTPException(
            status_code=404,
            detail=f"No cached volatility/prediction analysis found for '{ticker}'. Run the analysis endpoints first.",
        )

    cache_key = f"sections:{key_suffix}"
    cached = await get_cached(CACHE_COLLECTION, cache_key)
    if cached is not None:
        return cached

    try:
        history = await to_thread.run_sync(_history_payload, ticker)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    results = {"volatility": volatility, "predict": predict}
    try:
        sections = await to_thread.run_sync(generate_sectioned_explanation, results, history)
    except OllamaUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    await set_cached(CACHE_COLLECTION, cache_key, sections)
    return sections
