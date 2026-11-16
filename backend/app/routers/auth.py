# Author: urumb
"""Login / logout and request guards (login check, rate limits)."""
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from backend.app.security import (
    SESSION_COOKIE,
    RateLimiter,
    make_session,
    read_session,
    verify_password,
)
from backend.app.services import job_store
from src.config import Config

router = APIRouter(tags=["auth"])

login_limiter = RateLimiter(Config.LOGIN_ATTEMPTS_PER_MINUTE)
audit_limiter = RateLimiter(Config.AUDITS_PER_MINUTE)

# Reachable without a session: health checks and the login flow itself.
PUBLIC_PATHS = {"/health", "/auth/login", "/auth/logout", "/auth/me"}


class LoginRequest(BaseModel):
    username: str
    password: str


def client_key(request: Request) -> str:
    # Behind the production proxy, uvicorn runs with --proxy-headers so this
    # is the real client address, not the proxy's.
    return request.client.host if request.client else "unknown"


def current_user(request: Request) -> str | None:
    return read_session(request.cookies.get(SESSION_COOKIE), Config.SESSION_SECRET)


async def require_login(request: Request, call_next):
    """Middleware: when AUTH_ENABLED, every route except PUBLIC_PATHS needs
    a valid session. CORS preflights pass through."""
    if (
        Config.AUTH_ENABLED
        and request.method != "OPTIONS"
        and request.url.path not in PUBLIC_PATHS
        and current_user(request) is None
    ):
        return JSONResponse({"detail": "Not authenticated"}, status_code=401)
    return await call_next(request)


def enforce_audit_limits(request: Request) -> None:
    """Dependency for routes that start audits: per-client rate limit and a
    cap on audits running at once, so no one can flood the server."""
    if not audit_limiter.allow(client_key(request)):
        raise HTTPException(status_code=429, detail="Too many audits started; wait a minute and try again.")
    running = sum(1 for job in list(job_store.jobs.values()) if job["status"] in ("pending", "running"))
    if running >= Config.MAX_CONCURRENT_AUDITS:
        raise HTTPException(
            status_code=429,
            detail=f"{running} audit(s) already running; wait for one to finish or cancel it.",
        )


@router.post("/auth/login")
def login(body: LoginRequest, request: Request, response: Response) -> dict:
    if not Config.AUTH_ENABLED:
        return {"authenticated": True, "auth_enabled": False}
    if not login_limiter.allow(client_key(request)):
        raise HTTPException(status_code=429, detail="Too many login attempts; wait a minute and try again.")
    # Always verify the hash (even for a wrong username) so response timing
    # doesn't reveal whether the username exists.
    password_ok = verify_password(body.password, Config.AUTH_PASSWORD_HASH)
    if not (password_ok and body.username == Config.AUTH_USERNAME):
        raise HTTPException(status_code=401, detail="Wrong username or password")
    ttl = int(Config.SESSION_TTL_HOURS * 3600)
    response.set_cookie(
        SESSION_COOKIE,
        # The configured username (equal to body.username at this point),
        # so nothing from the request is written into the cookie.
        make_session(Config.AUTH_USERNAME, Config.SESSION_SECRET, ttl),
        max_age=ttl,
        httponly=True,
        secure=Config.COOKIE_SECURE,
        samesite="strict",
        path="/",
    )
    return {"authenticated": True, "auth_enabled": True, "username": Config.AUTH_USERNAME}


@router.post("/auth/logout")
def logout(response: Response) -> dict:
    response.delete_cookie(SESSION_COOKIE, path="/", secure=Config.COOKIE_SECURE, httponly=True, samesite="strict")
    return {"authenticated": False}


@router.get("/auth/me")
def me(request: Request) -> dict:
    if not Config.AUTH_ENABLED:
        return {"auth_enabled": False, "authenticated": True, "username": None}
    user = current_user(request)
    return {"auth_enabled": True, "authenticated": user is not None, "username": user}
