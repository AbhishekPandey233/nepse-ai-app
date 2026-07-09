"""assert-based self-check for routers/chat.py — run with: python tests/test_chat.py

Uses an in-memory fake Mongo cache (no real MongoDB required). The happy path calls the
real local Ollama instance if one is running; if not, that one assertion is skipped with
a printed note rather than failing the whole suite.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class FakeCollection:
    def __init__(self):
        self.docs = {}

    async def find_one(self, filt):
        return self.docs.get(filt["_id"])

    async def update_one(self, filt, update, upsert=False):
        self.docs[filt["_id"]] = update["$set"]


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
from app.utils.cache import build_cache_key  # noqa: E402


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
    test_404_when_nothing_cached()
    test_503_when_ollama_unreachable()
    test_happy_path_merges_cached_results_and_answers()
