# Author: urumb
"""Download an Ollama model in the background, with progress.

Used by the setup card ("Download qwen2.5-coder:3b") so desktop users don't
need a terminal. One download at a time; progress is polled by the UI.
"""
import json
import logging
import re
import threading
from typing import Any, Dict

import requests

from src.config import Config

logger = logging.getLogger(__name__)

# Ollama model names: "name", "name:tag", "namespace/name:tag".
MODEL_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*(/[a-z0-9][a-z0-9._-]*)?(:[a-z0-9][a-z0-9._-]*)?$")

_lock = threading.Lock()
_state: Dict[str, Any] = {"model": None, "status": "idle", "completed": 0, "total": 0, "error": None}


def status() -> Dict[str, Any]:
    with _lock:
        return dict(_state)


def _set(**changes: Any) -> None:
    with _lock:
        _state.update(changes)


def _pull(model: str) -> None:
    try:
        with requests.post(
            f"{Config.OLLAMA_BASE_URL}/api/pull",
            json={"model": model, "stream": True},
            stream=True,
            timeout=(10, 600),  # connect, then up to 10 min between progress lines
        ) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if not line:
                    continue
                event = json.loads(line)
                if event.get("error"):
                    raise RuntimeError(event["error"])
                if event.get("total"):
                    _set(completed=int(event.get("completed") or 0), total=int(event["total"]))
                if event.get("status") == "success":
                    _set(status="done", completed=_state["total"])
                    logger.info("Model downloaded: %s", model)
                    return
        raise RuntimeError("Download ended without success")
    except requests.ConnectionError:
        logger.warning("Model download failed (%s): Ollama not reachable", model)
        _set(status="error", error="Can't reach Ollama. Is it running?")
    except Exception as exc:  # report any failure to the UI
        logger.warning("Model download failed (%s): %s", model, exc)
        _set(status="error", error=str(exc)[:300])


def start(model: str) -> Dict[str, Any]:
    """Start downloading ``model``. Raises ValueError for a bad name and
    RuntimeError if another download is already running."""
    if not MODEL_NAME_RE.match(model or ""):
        raise ValueError(f"Not a valid model name: {model!r}")
    with _lock:
        if _state["status"] == "pulling":
            raise RuntimeError(f"Already downloading {_state['model']}")
        _state.update(model=model, status="pulling", completed=0, total=0, error=None)
        started = dict(_state)  # snapshot before the thread can change it
    threading.Thread(target=_pull, args=(model,), name="model-pull", daemon=True).start()
    return started
