"""Plain-language explanations of ml/ results via a locally-running Ollama model (no paid API)."""
import json

import httpx

from app.core.config import settings


class OllamaUnavailableError(RuntimeError):
    """Raised when the local Ollama server can't be reached."""


def _build_prompt(results: dict, question: str | None) -> str:
    data = json.dumps(results, indent=2, default=str)

    instructions = (
        "You are a financial analysis assistant explaining NEPSE stock market analysis results "
        "to a non-technical investor. Use ONLY the numbers in the DATA below - do not invent "
        "any figures or make claims the data doesn't support. Write in plain English, no jargon."
    )

    if question:
        task = f"Answer this question directly, using only the data: {question}"
    else:
        task = "Write a 2-4 sentence plain-English summary of these results for the investor."

    return f"{instructions}\n\nDATA:\n{data}\n\n{task}"


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
