# Author: urumb
"""Model selection and Ollama connectivity."""
import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app.services import model_pull
from src import llm
from src.config import Config

router = APIRouter(tags=["settings"])


class SettingsUpdate(BaseModel):
    model: str | None = None
    ai_enabled: bool | None = None


def _model_installed(requested: str, installed: list[str]) -> bool:
    # Ollama lists "llama3.2:latest" for a model pulled as "llama3.2".
    return requested in installed or f"{requested}:latest" in installed


@router.get("/settings/models")
def list_models() -> dict:
    """Models actually installed in the local Ollama, plus the active one."""
    try:
        models = llm.installed_models()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Could not list Ollama models: {e}")
    return {"models": models, "current": Config.MODEL_NAME, "ai_enabled": Config.AI_ENABLED}


class PullRequest(BaseModel):
    model: str


@router.get("/settings/status")
def ai_status() -> dict:
    """Everything the setup card needs in one call: is AI on, is Ollama
    reachable, and is the chosen model installed."""
    try:
        models = llm.installed_models()
        reachable = True
    except Exception:
        models, reachable = [], False
    return {
        "ai_enabled": Config.AI_ENABLED,
        "ollama_reachable": reachable,
        "model": Config.MODEL_NAME,
        "model_installed": reachable and _model_installed(Config.MODEL_NAME, models),
        "models": models,
        "pull": model_pull.status(),
    }


@router.post("/settings/models/pull")
def pull_model(body: PullRequest) -> dict:
    """Download a model into Ollama in the background (poll /settings/status)."""
    try:
        return model_pull.start(body.model)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.get("/settings")
def get_settings() -> dict:
    """Current settings; works even when Ollama isn't running."""
    return {"model": Config.MODEL_NAME, "ai_enabled": Config.AI_ENABLED}


@router.post("/settings")
def update_settings(settings: SettingsUpdate) -> dict:
    """Switch AI on/off and/or the active model. A model change is rejected
    if the model isn't installed, so a typo or un-pulled model fails here
    instead of failing every audit. Turning AI off needs no Ollama."""
    if settings.model is not None and settings.model != Config.MODEL_NAME:
        try:
            installed = llm.installed_models()
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"Ollama is not reachable: {e}")
        if not _model_installed(settings.model, installed):
            raise HTTPException(
                status_code=400,
                detail=f"Model '{settings.model}' is not installed. Run: ollama pull {settings.model}",
            )
        Config.MODEL_NAME = settings.model
    if settings.ai_enabled is not None:
        Config.AI_ENABLED = settings.ai_enabled
    llm.warm_up_model()  # no-op when AI is off
    return {"status": "ok", "model": Config.MODEL_NAME, "ai_enabled": Config.AI_ENABLED}


@router.get("/settings/ollama")
def check_ollama() -> dict:
    """Whether Ollama is reachable."""
    try:
        response = requests.get(Config.OLLAMA_BASE_URL, timeout=5)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Ollama connection failed: {e}")
    if response.status_code != 200:
        raise HTTPException(status_code=503, detail="Ollama returned non-200 status")
    return {"status": "ok"}
