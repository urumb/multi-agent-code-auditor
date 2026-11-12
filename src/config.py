# Author: urumb
import logging
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

class Config:
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODELS_DIR = os.getenv("OLLAMA_MODELS", "./local_models")
    CHROMA_PERSIST_DIRECTORY = os.getenv("CHROMA_PERSIST_DIRECTORY", "./chroma_db")
    AUDIT_DB_PATH = os.getenv("AUDIT_DB_PATH", "./audit_history.db")

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

    # Run bandit / ruff (and semgrep, if installed) before the LLM agents.
    STATIC_ANALYSIS_ENABLED = os.getenv("STATIC_ANALYSIS_ENABLED", "true").lower() == "true"

    # Most findings each analysis agent may report per code chunk. Each extra
    # finding costs ~130 output tokens, i.e. noticeably slower on a CPU.
    MAX_FINDINGS_PER_CHUNK = max(1, int(os.getenv("MAX_FINDINGS_PER_CHUNK", "2")))

    # ChromaDB "memory" of past audits. Off by default: it only feeds the
    # optional LLM reviewer summary, yet costs an embedding-model download
    # plus a vector lookup and write on every audit.
    MEMORY_ENABLED = os.getenv("MEMORY_ENABLED", "false").lower() == "true"

    _validated = False

    @staticmethod
    def validate():
        # Runs before every file's audit; only warn once per process.
        if Config._validated:
            return
        Config._validated = True
        if not os.path.exists(Config.OLLAMA_MODELS_DIR):
            # Just a warning, as Ollama might manage it differently or it might be absolute
            logging.getLogger(__name__).warning(
                "OLLAMA_MODELS path '%s' does not exist locally yet.", Config.OLLAMA_MODELS_DIR
            )
