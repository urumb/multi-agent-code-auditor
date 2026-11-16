# Author: urumb
"""FastAPI application: lifespan, CORS and router wiring.

Routes live in backend/app/routers/, audit execution in
backend/app/services/audit_jobs.py.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.routers import audit, auth, history, settings
from backend.app.services import db
from src import llm
from src.config import Config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Config.check_security()  # fail closed: never run with half-configured login
    Config.migrate_legacy_data()
    db.init_db()
    # Pre-load the model so the first audit doesn't pay the cold-start cost.
    llm.warm_up_model()
    yield


app = FastAPI(
    lifespan=lifespan,
    title="Multi-Agent Code Auditor",
    description="Local multi-agent code auditing with static analysis and Ollama.",
    version="0.6.0",
)

# Login check (a no-op unless AUTH_ENABLED=true). Registered before CORS so
# CORS wraps it: Starlette runs the last-added middleware first, and 401s
# must still carry CORS headers for the browser to read them.
app.middleware("http")(auth.require_login)

app.add_middleware(
    CORSMiddleware,
    # Explicit allowlist, not a wildcard: with login off (local use), an
    # unrestricted CORS policy would let any website the user has open
    # silently trigger audits or read past results via fetch().
    allow_origins=Config.FRONTEND_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(audit.router)
app.include_router(history.router)
app.include_router(settings.router)


@app.get("/health")
def health_check() -> dict:
    """Basic health check endpoint."""
    return {"status": "ok"}
