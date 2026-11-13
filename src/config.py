# Author: urumb
import logging
import os
import shutil

from dotenv import load_dotenv

# Load .env file
load_dotenv()

class Config:
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    # Everything the app writes (audit history, optional ChromaDB memory)
    # lives under one folder, so it's easy to back up, wipe, or mount as a
    # Docker volume. Individual paths can still be overridden.
    DATA_DIR = os.getenv("DATA_DIR", "./data")
    CHROMA_PERSIST_DIRECTORY = os.getenv("CHROMA_PERSIST_DIRECTORY", os.path.join(DATA_DIR, "chroma_db"))
    AUDIT_DB_PATH = os.getenv("AUDIT_DB_PATH", os.path.join(DATA_DIR, "audit_history.db"))

    # Origins allowed to call the backend via CORS. Defaults to the Next.js
    # dev server only — deliberately NOT a wildcard, since this server has
    # no authentication: an unrestricted CORS policy would let any website
    # the user happens to have open silently trigger audits (or read past
    # results) against their local backend. Override via env for other
    # deployments (e.g. a different frontend port).
    FRONTEND_ORIGINS = [
        origin.strip()
        for origin in os.getenv(
            "FRONTEND_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
        ).split(",")
        if origin.strip()
    ]

    # The Reviewer's executive summary is built from the findings directly
    # (instant). Set REVIEWER_USE_LLM=true to have the LLM write it instead -
    # costs one extra model call per file (slow on CPU-only machines).
    REVIEWER_USE_LLM = os.getenv("REVIEWER_USE_LLM", "false").lower() == "true"

    # Model to use explicitly. Mutable at runtime via POST /settings; agents
    # read this attribute on every run rather than capturing it once.
    MODEL_NAME = os.getenv("MODEL_NAME", "llama3.2")

    # Hard timeout for auditing one file: every agent LLM call for that
    # file's chunks, serialized through one local Ollama. 240s gives CPU-only
    # machines realistic room while keeping the wait bounded.
    PER_FILE_TIMEOUT_SECONDS = float(os.getenv("PER_FILE_TIMEOUT_SECONDS", "240"))

    # Most files audited per run. Each costs roughly a minute on a CPU-only
    # machine; the smallest files are kept. Raise it if you have a GPU.
    MAX_FILES_PER_AUDIT = int(os.getenv("MAX_FILES_PER_AUDIT", "25"))

    # Run bandit / ruff (and semgrep, if installed) before the LLM agents.
    STATIC_ANALYSIS_ENABLED = os.getenv("STATIC_ANALYSIS_ENABLED", "true").lower() == "true"

    # Most findings each analysis agent may report per code chunk. Each extra
    # finding costs ~130 output tokens, i.e. noticeably slower on a CPU.
    MAX_FINDINGS_PER_CHUNK = max(1, int(os.getenv("MAX_FINDINGS_PER_CHUNK", "2")))

    # ChromaDB "memory" of past audits. Off by default: it only feeds the
    # optional LLM reviewer summary, yet costs an embedding-model download
    # plus a vector lookup and write on every audit.
    MEMORY_ENABLED = os.getenv("MEMORY_ENABLED", "false").lower() == "true"

    @staticmethod
    def migrate_legacy_data(root: str = ".") -> list[str]:
        """Move data from the old locations (project root) into DATA_DIR.

        Earlier versions wrote ./audit_history.db and ./chroma_db/. Each item
        is moved only if its path wasn't customized via env, it exists at the
        old location, and nothing exists at the new one — so this never
        overwrites anything and is a no-op after the first run.
        """
        log = logging.getLogger(__name__)
        moved = []
        targets = []
        if "AUDIT_DB_PATH" not in os.environ:
            for suffix in ("", "-wal", "-shm", "-journal"):
                targets.append(("audit_history.db" + suffix, Config.AUDIT_DB_PATH + suffix))
        if "CHROMA_PERSIST_DIRECTORY" not in os.environ:
            targets.append(("chroma_db", Config.CHROMA_PERSIST_DIRECTORY))
        for old_name, new_path in targets:
            old_path = os.path.join(root, old_name)
            if not os.path.exists(old_path) or os.path.exists(new_path):
                continue
            if os.path.abspath(old_path) == os.path.abspath(new_path):
                continue
            os.makedirs(os.path.dirname(os.path.abspath(new_path)), exist_ok=True)
            shutil.move(old_path, new_path)
            log.info("Moved %s -> %s", old_path, new_path)
            moved.append(new_path)
        return moved
