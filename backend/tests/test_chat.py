"""assert-based self-check for routers/chat.py — run with: python tests/test_chat.py

Uses an in-memory fake Mongo cache (no real MongoDB required). The happy path calls the
real local Ollama instance if one is running; if not, that one assertion is skipped with
a printed note rather than failing the whole suite.
"""
import asyncio
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class _FakeCursor:
    def __init__(self, docs):
        self._docs = docs

    def __aiter__(self):
        self._it = iter(self._docs)
        return self

    async def __anext__(self):
        try:
            return next(self._it)
        except StopIteration:
            raise StopAsyncIteration


class FakeCollection:
    def __init__(self):
        self.docs = {}

    async def find_one(self, filt):
        return self.docs.get(filt["_id"])

    async def update_one(self, filt, update, upsert=False):
        self.docs[filt["_id"]] = update["$set"]

    def find(self, filt):
        rx = re.compile(filt["_id"]["$regex"])
        matched = [{**v, "_id": k} for k, v in self.docs.items() if rx.search(k)]
        return _FakeCursor(matched)


class FakeDB:
    def __init__(self):
        self._collections = {}

    def __getitem__(self, name):
        return self._collections.setdefault(name, FakeCollection())


_fake_db = FakeDB()

import app.utils.cache as cache_module  # noqa: E402

cache_module.get_database = lambda: _fake_db  # cache.py bound its own name at import time; patch it directly

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.routers import chat as chat_module  # noqa: E402
from app.ml.llm_explainer import OllamaUnavailableError  # noqa: E402
from app.routers.chat import _with_explicit_current_volatility  # noqa: E402
from app.utils.cache import build_cache_key, get_all_cached_for_ticker  # noqa: E402


def test_with_explicit_current_volatility_injects_matching_value():
    results = {"volatility": {"conditional_volatility": [0.01, 0.011, 0.012, 0.0126]}}
    enriched = _with_explicit_current_volatility(results)

    # must be the exact last element of the same array VolatilityPage.jsx reads for its
    # "Current Risk Level" box -- not some independently recomputed or differently-sourced value
    assert enriched["current_conditional_volatility_garch"] == 0.0126
    assert enriched["volatility"]["conditional_volatility"] == results["volatility"]["conditional_volatility"]
    print("test_with_explicit_current_volatility_injects_matching_value passed")


def test_with_explicit_current_volatility_noop_without_volatility_data():
    results = {"efficiency": {"verdict": "..."}}
    enriched = _with_explicit_current_volatility(results)

    assert "current_conditional_volatility_garch" not in enriched
    assert enriched == results
    print("test_with_explicit_current_volatility_noop_without_volatility_data passed")


def test_404_when_nothing_cached():
    with TestClient(app) as client:
        r = client.post("/api/explain-chat", json={"ticker": "NOCACHE"})
        assert r.status_code == 404
        assert "run the analysis" in r.json()["detail"].lower()
    print("test_404_when_nothing_cached passed")


def test_503_when_ollama_unreachable():
    key = f"efficiency:{build_cache_key('DUMMY')}"
    _fake_db["analysis_cache"].docs[key] = {"verdict": "some verdict"}

    original = chat_module.explain_results

    def boom(results, question=None):
        raise OllamaUnavailableError("Local AI model isn't running — start Ollama with `ollama serve`")

    chat_module.explain_results = boom
    try:
        with TestClient(app) as client:
            r = client.post("/api/explain-chat", json={"ticker": "DUMMY"})
            assert r.status_code == 503
            assert "ollama serve" in r.json()["detail"]
    finally:
        chat_module.explain_results = original
    print("test_503_when_ollama_unreachable passed")


def test_get_all_cached_for_ticker_merges_and_skips_non_context():
    suffix = build_cache_key("MULTI")
    docs = _fake_db["analysis_cache"].docs
    docs[f"efficiency:{suffix}"] = {"verdict": "eff"}
    docs[f"predict:{suffix}"] = {"metrics": {"rmse": 0.01}}
    docs[f"backtest:{suffix}:0.5"] = {"verdict": "bt", "n_trades": 3}  # cost-suffixed key still matched
    # these must NOT leak into chat context:
    docs[f"sections:{suffix}"] = {"risk_analysis": {}}
    docs[f"predict-compare:{suffix}"] = {"models": {}}  # 'predict' must not match 'predict-compare'

    bundle = asyncio.run(get_all_cached_for_ticker("MULTI"))

    assert set(bundle) == {"efficiency", "predict", "backtest"}, bundle
    assert bundle["backtest"]["n_trades"] == 3
    assert "_id" not in bundle["efficiency"]  # _id stripped like get_cached does
    print("test_get_all_cached_for_ticker_merges_and_skips_non_context passed")


def test_happy_path_merges_cached_results_and_answers():
    key_suffix = build_cache_key("DUMMY2")
    _fake_db["analysis_cache"].docs[f"efficiency:{key_suffix}"] = {
        "verdict": "Evidence AGAINST weak-form efficiency: significant autocorrelation."
    }
    _fake_db["analysis_cache"].docs[f"volatility:{key_suffix}"] = {"forecast": [0.01, 0.011]}

    captured = {}
    original = chat_module.explain_results

    def spy(results, question=None):
        captured["results"] = results
        captured["question"] = question
        return original(results, question)

    chat_module.explain_results = spy
    try:
        with TestClient(app) as client:
            r = client.post("/api/explain-chat", json={"ticker": "DUMMY2", "question": "Is this predictable?"})
            if r.status_code == 503:
                print("Ollama not reachable in this environment -- skipping live-answer assertion")
            else:
                assert r.status_code == 200, r.text
                assert isinstance(r.json()["answer"], str) and len(r.json()["answer"]) > 0

            # regardless of whether Ollama answered, the merge + wiring must be correct
            assert set(captured["results"].keys()) == {"efficiency", "volatility"}
            assert captured["question"] == "Is this predictable?"
    finally:
        chat_module.explain_results = original
    print("test_happy_path_merges_cached_results_and_answers passed")


if __name__ == "__main__":
    test_with_explicit_current_volatility_injects_matching_value()
    test_with_explicit_current_volatility_noop_without_volatility_data()
    test_404_when_nothing_cached()
    test_503_when_ollama_unreachable()
    test_get_all_cached_for_ticker_merges_and_skips_non_context()
    test_happy_path_merges_cached_results_and_answers()
