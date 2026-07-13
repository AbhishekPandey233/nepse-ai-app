"""Plain-language explanations of ml/ results via a locally-running Ollama model (no paid API)."""
import json

import httpx

from app.core.config import settings


class OllamaUnavailableError(RuntimeError):
    """Raised when the local Ollama server can't be reached."""


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
    "You are a financial analyst. Rules:\n"
    "- Use only the numbers above. Never invent numbers.\n"
    "- If a field named current_conditional_volatility_garch is present, that IS the current/"
    "latest volatility level. Always use it when asked about current volatility -- never a "
    "per-day feature column like volatility_20 found elsewhere in the data.\n"
    "- Max 4-6 sentences, plain English, no jargon.\n"
    "- If the question is specific, answer it directly. No preamble, no restating the question, "
    "no disclaimers about being an AI.\n"
    "- If the question is too broad or vague to answer precisely, you MUST respond in EXACTLY this "
    'format and nothing else: "With the data currently available, the following means: <grounded '
    'answer>" — filling the bracket with a real answer built from whatever relevant data IS present. '
    "Never say you cannot answer, never apologize, never list what data would be needed instead.\n\n"
    "Example 1:\n"
    "Q: What was the RMSE of the prediction model?\n"
    "A: The model's RMSE was 0.0096, meaning predictions were off by about 0.96 percentage points per "
    "day on average.\n\n"
    "Example 2:\n"
    "Q: Should I invest in this stock?\n"
    "A: With the data currently available, the following means: directional accuracy is 54%, barely "
    "better than a coin flip, so predictions are weak right now.\n"
)


def _build_prompt(results: dict, question: str | None) -> str:
    data = json.dumps(_trim_long_arrays(results), indent=2, default=str)

    if question:
        task = f"Now answer this question using ONLY the data above, following the rules exactly.\nQ: {question}\nA:"
    else:
        task = (
            "Now write a 4-6 sentence plain-English summary of these results for the investor, "
            "following the rules exactly.\nA:"
        )

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

    return response.json()["response"].strip()
