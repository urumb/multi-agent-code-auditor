# Author: urumb
"""Model selection and Ollama connectivity."""
import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src import llm
from src.config import Config

router = APIRouter(tags=["settings"])


class SettingsUpdate(BaseModel):
    model: str


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
    return {"models": models, "current": Config.MODEL_NAME}


@router.post("/settings")
def update_settings(settings: SettingsUpdate) -> dict:
    """Switch the active model. Rejects models that aren't installed, so a
    typo or un-pulled model fails here instead of failing every audit."""
    try:
        installed = llm.installed_models()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Ollama is not reachable: {e}")
    if not _model_installed(settings.model, installed):
        raise HTTPException(
            status_code=400,
            detail=f"Model '{settings.model}' is not installed. Run: ollama pull {settings.model}",
        )
    if Config.MODEL_NAME != settings.model:
        Config.MODEL_NAME = settings.model
        llm.warm_up_model()
    return {"status": "ok", "model": Config.MODEL_NAME}


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
