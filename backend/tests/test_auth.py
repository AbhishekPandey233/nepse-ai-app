"""assert-based self-check for auth (security.py + routers/auth.py) — run with: python tests/test_auth.py

Uses an in-memory fake Mongo collection (no real MongoDB required) so this runs anywhere.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class FakeUsersCollection:
    def __init__(self):
        self.docs = []

    async def find_one(self, filt):
        for d in self.docs:
            if all(d.get(k) == v for k, v in filt.items()):
                return d
        return None

    async def insert_one(self, doc):
        self.docs.append(doc)


class FakeDB:
    def __init__(self):
        self._collections = {}

    def __getitem__(self, name):
        return self._collections.setdefault(name, FakeUsersCollection())


_fake_db = FakeDB()

import app.routers.auth as auth_module

auth_module.get_database = lambda: _fake_db

from fastapi.testclient import TestClient

from app.core.security import create_access_token, decode_access_token, hash_password, verify_password
from app.main import app


def test_password_hashing():
    hashed = hash_password("supersecret123")
    assert hashed != "supersecret123"
    assert verify_password("supersecret123", hashed)
    assert not verify_password("wrongpassword", hashed)
    print("test_password_hashing passed")


def test_jwt_round_trip():
    token = create_access_token({"sub": "someone@example.com"})
    payload = decode_access_token(token)
    assert payload["sub"] == "someone@example.com"
    assert "exp" in payload

    try:
        decode_access_token(token + "tampered")
        raise AssertionError("expected 401 for a tampered token")
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 401

    print("test_jwt_round_trip passed")


def test_register_and_login_flow():
    with TestClient(app) as client:
        r1 = client.post("/api/register", json={"email": "trader@example.com", "password": "hunter2pass"})
        assert r1.status_code == 200, r1.text
        assert r1.json()["token_type"] == "bearer"
        assert r1.json()["access_token"]

        r2 = client.post("/api/register", json={"email": "trader@example.com", "password": "hunter2pass"})
        assert r2.status_code == 400, "duplicate email should be rejected"

        r3 = client.post("/api/login", json={"email": "trader@example.com", "password": "hunter2pass"})
        assert r3.status_code == 200, r3.text
        token = r3.json()["access_token"]
        payload = decode_access_token(token)
        assert payload["sub"] == "trader@example.com"

        r4 = client.post("/api/login", json={"email": "trader@example.com", "password": "wrongpassword"})
        assert r4.status_code == 401

        r5 = client.post("/api/login", json={"email": "nosuchuser@example.com", "password": "whatever"})
        assert r5.status_code == 401

    print("test_register_and_login_flow passed")


if __name__ == "__main__":
    test_password_hashing()
    test_jwt_round_trip()
    test_register_and_login_flow()
