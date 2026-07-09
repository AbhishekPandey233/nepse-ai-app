"""assert-based self-check for the router + cache wiring — run with: python tests/test_routers.py

No real MongoDB is required: get_database() is monkeypatched with an in-memory fake so this
exercises the actual FastAPI routes (including anyio.to_thread.run_sync + real ml/ calls on
real NABIL data) and the cache-hit/cache-miss behavior, without needing a live Mongo instance.
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


import app.utils.cache as cache_module  # noqa: E402

_fake_db = FakeDB()  # single shared instance -- get_database() must keep returning the same one
cache_module.get_database = lambda: _fake_db  # cache.py bound its own name at import time; patch it directly

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.routers import efficiency, explainability, prediction, volatility  # noqa: E402


def _count_calls(module):
    original = module._compute
    calls = {"n": 0}

    def wrapped(ticker):
        calls["n"] += 1
        return original(ticker)

    module._compute = wrapped
    return calls


def test_routes_compute_once_then_serve_from_cache():
    with TestClient(app) as client:
        for module, path in [
            (efficiency, "/api/efficiency"),
            (volatility, "/api/volatility"),
            (prediction, "/api/predict"),
            (explainability, "/api/explain"),
        ]:
            calls = _count_calls(module)

            r1 = client.get(path, params={"ticker": "nabil"})
            assert r1.status_code == 200, r1.text
            body1 = r1.json()

            r2 = client.get(path, params={"ticker": "nabil"})
            assert r2.status_code == 200, r2.text
            body2 = r2.json()

            assert body1 == body2, f"{path}: cached response should match the original"
            assert calls["n"] == 1, f"{path}: second request should be served from cache, not recomputed"

            print(f"{path} passed (computed once, second call served from cache)")

        unknown = client.get("/api/efficiency", params={"ticker": "NOT_A_REAL_TICKER"})
        assert unknown.status_code == 404
        print("/api/efficiency unknown-ticker -> 404 passed")


if __name__ == "__main__":
    test_routes_compute_once_then_serve_from_cache()
