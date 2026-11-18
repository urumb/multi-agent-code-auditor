# Author: urumb
"""Cache keys for "re-audit only changed files".

A file's previous report is reused only if *nothing* that affects the
result has changed: the file content and type, the scan depth, the model,
analysis settings, analyzer versions, and the auditor's own analysis code
(agents, prompts, merging rules, semgrep rules). Changing any of them gives
a new key, so stale results are never reused.
"""
import hashlib
import json
import os
import shutil
from functools import lru_cache
from importlib import metadata
from pathlib import Path

from src.config import Config

# Bump to invalidate every cached result (e.g. after a report-format change).
CACHE_SCHEMA = 1

_ROOT = Path(__file__).resolve().parents[3]
# Code whose changes can change a file's findings.
_FINGERPRINT_PATHS = (
    "src/agents",
    "src/findings.py",
    "src/static_analysis.py",
    "src/graph.py",
    "src/llm.py",
    "src/state.py",
    "rules/semgrep.yml",
    "backend/app/services/audit_runner.py",
)


def _version(package: str) -> str:
    try:
        return metadata.version(package)
    except metadata.PackageNotFoundError:
        return "absent"


@lru_cache(maxsize=1)
def _code_fingerprint() -> str:
    digest = hashlib.sha256()
    for rel in _FINGERPRINT_PATHS:
        path = _ROOT / rel
        files = sorted(path.rglob("*.py")) if path.is_dir() else [path]
        for f in files:
            if f.is_file():
                digest.update(str(f.relative_to(_ROOT)).encode())
                digest.update(f.read_bytes())
    for package in ("bandit", "ruff", "langchain-ollama", "langgraph"):
        digest.update(f"{package}={_version(package)}".encode())
    return digest.hexdigest()


def cache_key(content: str, file_path: str, depth: str) -> str:
    parts = [
        CACHE_SCHEMA,
        content,
        os.path.splitext(file_path)[1].lower(),
        depth,
        Config.MODEL_NAME,
        Config.AI_ENABLED,
        Config.MAX_FINDINGS_PER_CHUNK,
        Config.STATIC_ANALYSIS_ENABLED,
        Config.REVIEWER_USE_LLM,
        Config.MEMORY_ENABLED,
        os.getenv("SEMGREP_RULES", ""),
        shutil.which("semgrep") is not None,
        _code_fingerprint(),
    ]
    return hashlib.sha256(json.dumps(parts).encode("utf-8")).hexdigest()
