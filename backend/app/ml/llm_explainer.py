"""Plain-language explanations of ml/ results via a locally-running Ollama model (no paid API)."""
import json
import math
import re

import httpx

from app.core.config import settings


class OllamaUnavailableError(RuntimeError):
    """Raised when the local Ollama server can't be reached."""


def _use_rupees(text: str) -> str:
    """NEPSE prices are Nepalese Rupees, but the local model habitually defaults to '$'/'dollars'.
    Deterministic fix on the model's output (more reliable than prompt wording alone)."""
    text = re.sub(r"\$\s?(?=\d)", "Rs ", text)  # "$419" / "$ 419" -> "Rs 419"
    text = re.sub(r"\bdollars\b", "rupees", text, flags=re.IGNORECASE)
    text = re.sub(r"\bdollar\b", "rupee", text, flags=re.IGNORECASE)
    return text


def _ollama_generate(prompt: str, timeout: int = 120) -> str:
    """Single Ollama /api/generate call. Shared by the newer explainers (explain_results and
    explain_prediction_factors predate it and keep their own inline calls)."""
    try:
        response = httpx.post(
            f"{settings.OLLAMA_HOST}/api/generate",
            json={"model": settings.OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=timeout,
        )
        response.raise_for_status()
    except httpx.TransportError as exc:
        raise OllamaUnavailableError(
            "Local AI model isn't running — start Ollama with `ollama serve`"
        ) from exc
    return _use_rupees(response.json()["response"].strip())


def _trim_long_arrays(obj, max_items: int = 6):
    """Truncate long arrays (e.g. per-day dates/actual/predictions, 100+ entries) before
    they're rendered into the prompt. In testing, leaving these full-length reliably made
    the local 3B model grab a random noisy value instead of the labeled scalar metric it
    was asked about; trimming them fixed it."""
    if isinstance(obj, dict):
        return {k: _trim_long_arrays(v, max_items) for k, v in obj.items()}
    if isinstance(obj, list) and len(obj) > max_items:
        head, tail = obj[:3], obj[-3:]
        return [*head, f"... ({len(obj) - 6} more values omitted) ...", *tail]
    return obj


PROMPT_RULES = (
    "You are a knowledgeable financial analyst chatting with an investor about this stock. Use the "
    "data above as context.\n"
    "- If a field named current_conditional_volatility_garch is present, that IS the current/"
    "latest volatility level. Always use it when asked about current volatility -- never a "
    "per-day feature column like volatility_20 found elsewhere in the data.\n"
    "- Otherwise, answer naturally and conversationally, however long or short the question calls "
    "for -- no fixed length, no fixed format. Use your own general financial knowledge freely to "
    "add context beyond the data above.\n"
)


def _summarize_bundle(results: dict) -> dict:
    """Shrink a full cross-module cache bundle (from get_all_cached_for_ticker) to just the fields
    worth handing a small local model. Full per-day SHAP/prediction/volatility arrays reliably slow
    down and confuse a 3B model; here each module is reduced to its headline numbers. Any key that
    isn't a known module (e.g. a single-module dict, or the injected current_conditional_volatility_
    garch scalar) is passed through untouched, so single-page callers and tests are unaffected.
    """
    if not isinstance(results, dict):
        return results

    out = dict(results)

    if isinstance(out.get("predict"), dict):
        p = out["predict"]
        dates = p.get("dates") or []
        out["predict"] = {
            "metrics": p.get("metrics"),
            "next_day_forecast": p.get("next_day_forecast"),
            "test_period": {"from": dates[0], "to": dates[-1]} if dates else None,
        }

    if isinstance(out.get("explain"), dict):
        e = out["explain"]
        out["explain"] = {
            "base_value": e.get("base_value"),
            "top_factors_latest_prediction": [
                {"feature": f["feature"], "shap_value": f["shap_value"], "direction": f["direction"]}
                for f in _top_factors(e, top_n=5)
            ],
        }

    if isinstance(out.get("volatility"), dict):
        v = out["volatility"]
        cv = v.get("conditional_volatility") or []
        out["volatility"] = {
            "params": v.get("params"),
            "current_conditional_volatility": cv[-1] if cv else None,
            "max_conditional_volatility": max(cv) if cv else None,
            "forecast": (v.get("forecast") or [])[:5],
        }

    if isinstance(out.get("history"), dict):
        out["history"] = {"summary": out["history"].get("summary")}  # drop the full close/date arrays

    if isinstance(out.get("backtest"), dict):
        b = out["backtest"]
        out["backtest"] = {
            k: b.get(k)
            for k in ("strategy_total_return", "buy_hold_total_return", "n_trades",
                      "transaction_cost_pct", "outperformed", "verdict")
        }

    # efficiency is already compact (adf/ljung_box/variance_ratio/verdict) -- left as-is
    return out


def _build_prompt(results: dict, question: str | None) -> str:
    data = json.dumps(_trim_long_arrays(_summarize_bundle(results)), indent=2, default=str)

    if question:
        task = f"Q: {question}\nA:"
    else:
        task = "Write a natural-language summary of these results for the investor.\nA:"

    return f"DATA:\n{data}\n\n{PROMPT_RULES}\n{task}"


def explain_results(results: dict, question: str | None = None) -> str:
    prompt = _build_prompt(results, question)

    try:
        response = httpx.post(
            f"{settings.OLLAMA_HOST}/api/generate",
            json={"model": settings.OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=60,
        )
        response.raise_for_status()
    except httpx.TransportError as exc:
        raise OllamaUnavailableError(
            "Local AI model isn't running — start Ollama with `ollama serve`"
        ) from exc

    return _use_rupees(response.json()["response"].strip())


# ── explain_prediction_factors: a long-form, example-rich explanation mode ──────────────────
# Distinct from explain_results (above): deliberately longer (5+ paragraphs), grounded in each
# top SHAP factor's exact value, with plain-language analogies for a complete beginner.

FEATURE_GLOSSARY = {
    "s_no": "the row's position in that day's exchange listing (not a market signal)",
    "conf": "a confidence/certainty score reported for that day's trade",
    "open": "the stock's opening price for the day",
    "high": "the highest price reached during the day",
    "low": "the lowest price reached during the day",
    "vwap": "the volume-weighted average price for the day",
    "vol": "the number of shares traded that day",
    "prev_close": "the previous trading day's closing price",
    "turnover": "the total value (NPR) of shares traded that day",
    "trans": "the number of individual trades executed that day",
    "diff": "the change in price from the previous close",
    "range": "the difference between the day's high and low price",
    "diff_pct": "the percentage change in price from the previous close",
    "range_pct": "the day's trading range as a percentage of price",
    "vwap_pct": "how far the closing price sits from the volume-weighted average price",
    "120_days": "the 120-day rolling average price -- a medium-term price trend",
    "180_days": "the 180-day rolling average price -- a longer-term price trend",
    "52_weeks_high": "the highest price over the past 52 weeks",
    "52_weeks_low": "the lowest price over the past 52 weeks",
    "ltp": "the last traded price for the day",
    "close_ltp": "the difference between the closing price and the last traded price",
    "close_ltp_pct": "the percentage difference between closing price and last traded price",
    "log_return": "that day's price return -- how much the price moved",
    "ma_5": "the 5-day moving average price -- a short-term price trend indicator",
    "ma_10": "the 10-day moving average price -- a short-term price trend indicator",
    "ma_20": "the 20-day moving average price -- a medium-term price trend indicator",
    "rsi_14": (
        "the 14-day Relative Strength Index, a momentum indicator showing if a stock looks "
        "overbought (too many recent buyers) or oversold (too many recent sellers)"
    ),
    "volatility_20": "the rolling 20-day volatility -- how much the price has been swinging recently",
    "lag_return_1": "the stock's return (price change) from 1 trading day ago",
    "lag_return_2": "the stock's return (price change) from 2 trading days ago",
    "lag_return_3": "the stock's return (price change) from 3 trading days ago",
}


def _top_factors(explain_result: dict, top_n: int = 3) -> list:
    per_row_shap = explain_result.get("per_row_shap") or []
    if not per_row_shap:
        return []

    last_row = per_row_shap[-1]
    top = sorted(last_row.items(), key=lambda kv: abs(kv[1]), reverse=True)[:top_n]

    return [
        {
            "feature": name,
            "meaning": FEATURE_GLOSSARY.get(name, "a statistical trading indicator"),
            "shap_value": value,
            "direction": "UP" if value >= 0 else "DOWN",
        }
        for name, value in top
    ]


def _build_detailed_factors_prompt(ticker: str, predict_result: dict, explain_result: dict) -> str:
    factors = _top_factors(explain_result)
    factor_blocks = "\n".join(
        f"Factor {i}: {f['feature']}\n"
        f"  Meaning: {f['meaning']}\n"
        f"  Exact SHAP value: {f['shap_value']}\n"
        f"  Direction pushed: {f['direction']}"
        for i, f in enumerate(factors, 1)
    )

    metrics = predict_result.get("metrics", {})
    forecast = predict_result.get("next_day_forecast", {})
    base_value = explain_result.get("base_value")

    predicted_return = forecast.get("predicted_return")
    forecast_pct = round((math.exp(predicted_return) - 1) * 100, 3) if predicted_return is not None else None

    return (
        "You are a patient financial educator explaining a stock prediction model's reasoning to "
        "someone with NO finance background.\n\n"
        f"FACTS ABOUT {ticker} (use ONLY these numbers, never invent any):\n"
        f"Model base value (starting estimate before any factors): {base_value}\n"
        f"Next-day forecast, as a percentage return: {forecast_pct}% (as of {forecast.get('as_of_date')})\n"
        f"Model accuracy -- RMSE: {metrics.get('rmse')}, MAE: {metrics.get('mae')}, "
        f"Directional accuracy: {metrics.get('directional_accuracy')}%\n\n"
        f"Top {len(factors)} factors behind the latest prediction, in order of importance:\n"
        f"{factor_blocks}\n\n"
        "Rules:\n"
        "- Write AT LEAST 5 full paragraphs (300-450 words). Comprehensive, not a short summary.\n"
        "- Copy each Factor's exact SHAP value EXACTLY as given above when you mention it -- do not "
        "swap values between factors.\n"
        "- Discuss each factor in its own paragraph, in order: what it measures (use the Meaning "
        "given), its exact SHAP value, and whether it pushed the prediction UP or DOWN.\n"
        "- Give a simple real-world analogy for at least 2 of the factors.\n"
        "- Explain what base_value means (the model's starting-point estimate before any specific "
        "factor is applied) and how the factors adjust it up or down from there.\n"
        "- Dedicate one paragraph to the next-day forecast. You MUST state the exact "
        f"{forecast_pct}% figure given above verbatim in that paragraph -- it IS available, never "
        "say it is unknown or unavailable.\n"
        "- Explain the accuracy metrics (RMSE, MAE, directional accuracy) in plain terms with one "
        "real-world analogy (e.g. a weather forecaster's track record).\n"
        '- No jargon without explaining it. No AI disclaimers. No "I hope this helps" filler.\n\n'
        "Write the full explanation now."
    )


def explain_prediction_factors(ticker: str, predict_result: dict, explain_result: dict) -> str:
    """Long-form, example-rich explanation of what drove the latest SHAP-based prediction for
    `ticker`. Distinct from explain_results (Phase 19's concise chat Q&A) -- deliberately longer,
    more educational, grounded in each factor's exact number, with real-world analogies."""
    prompt = _build_detailed_factors_prompt(ticker, predict_result, explain_result)

    try:
        response = httpx.post(
            f"{settings.OLLAMA_HOST}/api/generate",
            json={"model": settings.OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=120,
        )
        response.raise_for_status()
    except httpx.TransportError as exc:
        raise OllamaUnavailableError(
            "Local AI model isn't running — start Ollama with `ollama serve`"
        ) from exc

    return _use_rupees(response.json()["response"].strip())


# ── generate_sectioned_explanation: three separate, non-overlapping sections ─────────────────────
# Risk Analysis / Historical Trends / Future Outlook. Each section's key_points are computed
# deterministically (guaranteed-correct numbers -- the small local model is unreliable with raw
# figures) and only the prose narrative is generated by Ollama, from a prompt that sees ONLY that
# section's own facts, so the three narratives can't drift into each other's territory.

_SECTION_STYLE = (
    "Write 2-4 sentences of plain English for a beginner. Use ONLY the facts above; never invent "
    "numbers. All prices are in Nepalese Rupees (write 'Rs.'), never dollars or '$'. No jargon "
    "without explaining it, no disclaimers about being an AI, no filler."
)


def _pct_return(log_return: float) -> float:
    return (math.exp(log_return) - 1) * 100


def _max_drawdown_pct(closes: list) -> float:
    """Worst peak-to-trough decline over the series, as a (negative) percentage."""
    peak = closes[0]
    worst = 0.0
    for c in closes:
        peak = max(peak, c)
        worst = min(worst, (c - peak) / peak)
    return worst * 100


def _risk_section(results: dict, history: dict) -> dict:
    vol = results["volatility"]["conditional_volatility"]
    current = vol[-1]
    below = sum(1 for v in vol if v <= current)
    top_pct = round(100 - below / len(vol) * 100)
    max_vol = max(vol)

    closes = history["close"]
    max_dd = _max_drawdown_pct(closes)
    worst_day = history["summary"]["top_losses"][0]

    key_points = [
        f"Current volatility is in the top {top_pct}% of this stock's own history",
        f"Worst peak-to-trough drawdown over the period: {max_dd:.1f}%",
        f"Largest single-day drop: {worst_day['return_pct']:.1f}% on {worst_day['date']}",
    ]
    facts = (
        f"Current volatility percentile: top {top_pct}% of history (higher = more turbulent than usual).\n"
        f"Highest volatility ever seen: {max_vol:.5f}; current: {current:.5f}.\n"
        f"Worst peak-to-trough drawdown: {max_dd:.1f}%.\n"
        f"Largest single-day loss: {worst_day['return_pct']:.1f}% on {worst_day['date']}.\n"
    )
    prompt = (
        f"FACTS (risk & downside):\n{facts}\n"
        "Explain ONLY the stock's current risk level and downside exposure. Do NOT describe the "
        "overall price history or any future forecast.\n" + _SECTION_STYLE
    )
    return {"key_points": key_points, "narrative": _ollama_generate(prompt)}


def _trends_section(history: dict) -> dict:
    s = history["summary"]
    top_gain = s["top_gains"][0]
    top_loss = s["top_losses"][0]

    key_points = [
        f"Overall {s['overall_return_pct']:+.1f}% from {s['period_start']} to {s['period_end']}",
        f"Peak close {s['highest_close']['price']:.0f} on {s['highest_close']['date']}; "
        f"trough {s['lowest_close']['price']:.0f} on {s['lowest_close']['date']}",
        f"Biggest up day {top_gain['return_pct']:+.1f}% ({top_gain['date']}); "
        f"biggest down day {top_loss['return_pct']:+.1f}% ({top_loss['date']})",
        f"{len(s['high_volatility_periods'])} distinct high-volatility stretch(es) over the period",
    ]
    facts = (
        f"Period: {s['period_start']} to {s['period_end']}.\n"
        f"Overall price change: {s['overall_return_pct']:+.1f}%.\n"
        f"Highest close {s['highest_close']['price']:.0f} on {s['highest_close']['date']}; "
        f"lowest close {s['lowest_close']['price']:.0f} on {s['lowest_close']['date']}.\n"
        f"Biggest single-day gain {top_gain['return_pct']:+.1f}% on {top_gain['date']}; "
        f"biggest single-day loss {top_loss['return_pct']:+.1f}% on {top_loss['date']}.\n"
        f"Number of high-volatility stretches: {len(s['high_volatility_periods'])}.\n"
    )
    prompt = (
        f"FACTS (past price history):\n{facts}\n"
        "Explain ONLY the stock's past price history: its overall direction and its most notable "
        "past moves. Do NOT discuss the current risk level or any future forecast.\n" + _SECTION_STYLE
    )
    return {"key_points": key_points, "narrative": _ollama_generate(prompt)}


def _outlook_section(results: dict) -> dict:
    predict = results["predict"]
    forecast = predict.get("next_day_forecast", {})
    metrics = predict.get("metrics", {})

    forecast_pct = _pct_return(forecast["predicted_return"]) if forecast.get("predicted_return") is not None else None
    da = metrics.get("directional_accuracy")
    rmse = metrics.get("rmse")

    key_points = [
        f"Next-day model forecast: {forecast_pct:+.2f}% (as of {forecast.get('as_of_date')})"
        if forecast_pct is not None
        else "Next-day forecast unavailable",
        f"Model directional accuracy on held-out data: {da:.1f}%" if da is not None else "Accuracy unavailable",
        "This is a pattern-based estimate from historical data, not a guarantee",
    ]
    facts = (
        f"Next-day forecast: {forecast_pct:+.3f}% (as of {forecast.get('as_of_date')}).\n"
        f"Model directional accuracy on unseen data: {da:.1f}% (50% would be a coin flip).\n"
        f"Typical daily error (RMSE): {rmse}.\n"
    )
    prompt = (
        f"FACTS (model forecast & its track record):\n{facts}\n"
        "Explain ONLY what the model's forward-looking forecast suggests. You MUST state that it is "
        "based on patterns in historical data and is not a guarantee, and you MUST mention the "
        f"directional accuracy ({da:.1f}%) so the confidence is not overstated. Do NOT re-describe "
        "the past price history or the current volatility level.\n" + _SECTION_STYLE
    )
    return {"key_points": key_points, "narrative": _ollama_generate(prompt)}


def generate_sectioned_explanation(results: dict, history: dict) -> dict:
    """Three distinct, non-overlapping explanation sections for the analysis pages.

    Each section carries deterministic key_points (correct by construction) plus an Ollama-generated
    narrative grounded only in that section's own facts. `results` needs 'volatility' and 'predict';
    `history` is the /api/history payload ('close' series + 'summary').
    """
    return {
        "risk_analysis": _risk_section(results, history),
        "historical_trends": _trends_section(history),
        "future_outlook": _outlook_section(results),
    }
