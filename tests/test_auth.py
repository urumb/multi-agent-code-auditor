import json
import os
import tempfile

import pytest
from fastapi.testclient import TestClient

from backend.app.routers import auth as auth_router
from backend.app.security import (
    SESSION_COOKIE,
    RateLimiter,
    hash_password,
    make_session,
    read_session,
    verify_password,
)
from backend.app.services import audit_runner, db, job_store
from src.config import Config

SECRET = "s" * 48
PASSWORD = "correct horse battery staple"


# --- primitives ------------------------------------------------------------------

def test_password_hash_roundtrip_and_salting():
    first, second = hash_password(PASSWORD), hash_password(PASSWORD)
    assert first.startswith("scrypt:") and first != second  # random salt
    assert PASSWORD not in first
    assert verify_password(PASSWORD, first)
    assert not verify_password("wrong", first)
    assert not verify_password(PASSWORD, "garbage")


def test_session_tokens_are_signed_and_expire():
    token = make_session("admin", SECRET, ttl_seconds=60, now=1000)
    assert read_session(token, SECRET, now=1030) == "admin"
    assert read_session(token, SECRET, now=1061) is None  # expired
    assert read_session(token, "x" * 48, now=1030) is None  # wrong secret
    user, exp, nonce, sig = token.split(".")
    forged = f"{user}.{int(exp) + 9999}.{nonce}.{sig}"
    assert read_session(forged, SECRET, now=1030) is None  # tampered
    assert read_session(None, SECRET) is None


def test_rate_limiter_window():
    limiter = RateLimiter(limit=2, window=60)
    assert limiter.allow("ip", now=0) and limiter.allow("ip", now=1)
    assert not limiter.allow("ip", now=2)
    assert limiter.allow("other", now=2)
    assert limiter.allow("ip", now=62)


def test_startup_refuses_half_configured_login(monkeypatch):
    monkeypatch.setattr(Config, "AUTH_ENABLED", True)
    monkeypatch.setattr(Config, "AUTH_USERNAME", "admin")
    monkeypatch.setattr(Config, "AUTH_PASSWORD_HASH", "")
    monkeypatch.setattr(Config, "SESSION_SECRET", "short")
    with pytest.raises(RuntimeError, match="AUTH_PASSWORD_HASH.*SESSION_SECRET"):
        Config.check_security()
    monkeypatch.setattr(Config, "AUTH_ENABLED", False)
    Config.check_security()  # off: nothing required


# --- the API with login on -------------------------------------------------------

class FakeGraph:
    def invoke(self, state):
        return {**state, "final_report": json.dumps({"findings": [], "risk_score": 0, "max_severity": "Low"}),
                "execution_plan": {"agents": ["security"]}}


@pytest.fixture
def secured(monkeypatch):
    tmp = tempfile.mkdtemp(prefix="auditor_auth_")
    monkeypatch.setattr(Config, "AUDIT_DB_PATH", os.path.join(tmp, "audit.db"))
    monkeypatch.setattr(Config, "AUTH_ENABLED", True)
    monkeypatch.setattr(Config, "AUTH_USERNAME", "admin")
    monkeypatch.setattr(Config, "AUTH_PASSWORD_HASH", hash_password(PASSWORD))
    monkeypatch.setattr(Config, "SESSION_SECRET", SECRET)
    monkeypatch.setattr(Config, "COOKIE_SECURE", False)  # TestClient talks plain http
    monkeypatch.setattr(audit_runner, "graph", FakeGraph())
    monkeypatch.setattr("src.llm.warm_up_model", lambda: None)
    db._initialized = False
    job_store.jobs.clear()
    auth_router.login_limiter.reset()
    auth_router.audit_limiter.reset()
    from backend.app.main import app

    with TestClient(app) as client:
        yield client
    db._initialized = False
    job_store.jobs.clear()


def test_everything_but_health_and_login_needs_a_session(secured):
    assert secured.get("/health").status_code == 200
    assert secured.get("/auth/me").json() == {"auth_enabled": True, "authenticated": False, "username": None}
    for method, path in [("get", "/audit/history"), ("get", "/metrics"), ("get", "/settings/models"),
                         ("post", "/audit/stream"), ("get", "/docs"), ("get", "/openapi.json")]:
        assert getattr(secured, method)(path).status_code == 401, path


def test_login_sets_secure_cookie_and_unlocks_api(secured):
    assert secured.post("/auth/login", json={"username": "admin", "password": "nope"}).status_code == 401
    assert secured.post("/auth/login", json={"username": "root", "password": PASSWORD}).status_code == 401

    resp = secured.post("/auth/login", json={"username": "admin", "password": PASSWORD})
    assert resp.status_code == 200
    cookie = resp.headers["set-cookie"].lower()
    assert SESSION_COOKIE in cookie and "httponly" in cookie and "samesite=strict" in cookie

    assert secured.get("/auth/me").json()["authenticated"] is True
    assert secured.get("/audit/history").status_code == 200
    job = secured.post("/audit/stream", json={"input_type": "paste", "code": "a = 1\n" * 30})
    assert job.status_code == 200

    secured.post("/auth/logout")
    secured.cookies.clear()
    assert secured.get("/audit/history").status_code == 401


def test_login_attempts_are_rate_limited(secured):
    codes = [secured.post("/auth/login", json={"username": "admin", "password": "bad"}).status_code
             for _ in range(Config.LOGIN_ATTEMPTS_PER_MINUTE + 1)]
    assert codes[-1] == 429 and set(codes[:-1]) == {401}


def test_audit_starts_are_rate_limited(secured, monkeypatch):
    secured.post("/auth/login", json={"username": "admin", "password": PASSWORD})
    monkeypatch.setattr(auth_router.audit_limiter, "limit", 2)
    body = {"input_type": "paste", "code": "b = 1\n" * 30}
    codes = [secured.post("/audit/stream", json=body).status_code for _ in range(3)]
    assert codes == [200, 200, 429]


def test_concurrent_audit_cap(secured, monkeypatch):
    secured.post("/auth/login", json={"username": "admin", "password": PASSWORD})
    monkeypatch.setattr(Config, "MAX_CONCURRENT_AUDITS", 1)
    job_id = job_store.create_job("busy", "paste")
    job_store.jobs[job_id]["status"] = "running"
    resp = secured.post("/audit/stream", json={"input_type": "paste", "code": "c = 1\n" * 30})
    assert resp.status_code == 429 and "already running" in resp.json()["detail"]
