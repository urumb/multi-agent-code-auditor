# Author: urumb
"""Shared Ollama client factory tuned for fast local (often CPU-only) inference.

Why these settings matter on a CPU:
- ``num_predict`` caps generated tokens. Generation is the slowest part and
  runaway/rambling output is the most common cause of timeouts.
- ``format="json"`` constrains the model to emit valid JSON, which is both
  shorter and removes parse failures.
- ``num_ctx`` keeps the KV cache small (faster prompt processing, less RAM).
- ``keep_alive`` keeps the model resident so only the first audit pays the
  model-load cost.
"""
import os
import threading

import requests
from langchain_ollama import ChatOllama

from .config import Config

# Output cap for the reviewer (analysis agents size theirs from
# Config.MAX_FINDINGS_PER_CHUNK; see agents/base.py).
REVIEWER_MAX_TOKENS = 160
NUM_CTX = 4096
KEEP_ALIVE = "30m"


# Local inference (especially on CPU) is throughput-bound: running the three
# analysis agents' calls at the same time just makes each one ~3x slower
# (cores and memory bandwidth are shared), so total time is no better and
# every call risks the timeout. Calls therefore take turns by default. Raise
# LLM_CONCURRENCY only if you have a GPU / OLLAMA_NUM_PARALLEL > 1.
_LLM_SLOTS = threading.BoundedSemaphore(max(1, int(os.getenv("LLM_CONCURRENCY", "1"))))


# How often a call waiting for a slot re-checks whether its audit was cancelled.
_SLOT_POLL_SECONDS = 0.25


class AuditCancelled(Exception):
    """Raised instead of making an LLM call once the audit has been abandoned
    (e.g. its per-file timeout expired). Agents must re-raise it rather than
    record it as a per-snippet error, so the whole pipeline unwinds quickly."""


def invoke_llm(chain, inputs, cancel_event: threading.Event | None = None):
    """Run ``chain.invoke(inputs)`` while holding one of the LLM slots.

    If ``cancel_event`` is set — before the call starts or while it waits for
    a slot — raises AuditCancelled instead of calling the model. This stops a
    timed-out audit, whose thread can't be killed, from holding the slot for
    all its remaining calls and making the *next* file time out too. A call
    already running can't be interrupted, but it's bounded by ``num_predict``.
    """
    while not _LLM_SLOTS.acquire(timeout=_SLOT_POLL_SECONDS):
        if cancel_event is not None and cancel_event.is_set():
            raise AuditCancelled()
    try:
        if cancel_event is not None and cancel_event.is_set():
            raise AuditCancelled()
        return chain.invoke(inputs)
    finally:
        _LLM_SLOTS.release()


def make_llm(temperature: float, *, max_tokens: int, json_mode: bool = True) -> ChatOllama:
    """Build a ChatOllama client for the currently configured model."""
    return ChatOllama(
        base_url=Config.OLLAMA_BASE_URL,
        model=Config.MODEL_NAME,
        temperature=temperature,
        num_predict=max_tokens,
        num_ctx=NUM_CTX,
        keep_alive=KEEP_ALIVE,
        format="json" if json_mode else None,
    )


def installed_models() -> list[str]:
    """Names of models currently pulled into the local Ollama install."""
    response = requests.get(f"{Config.OLLAMA_BASE_URL}/api/tags", timeout=5)
    response.raise_for_status()
    return sorted(m["name"] for m in response.json().get("models", []))


def warm_up_model() -> None:
    """Load the configured model into memory in the background.

    Fire-and-forget: the first real audit then skips the cold-load delay
    (often 10-60s on CPU). Failures are ignored; Ollama may simply be down.
    """

    def _warm() -> None:
        try:
            requests.post(
                f"{Config.OLLAMA_BASE_URL}/api/generate",
                json={"model": Config.MODEL_NAME, "prompt": "", "keep_alive": KEEP_ALIVE},
                timeout=120,
            )
        except requests.RequestException:
            pass

    threading.Thread(target=_warm, daemon=True).start()
