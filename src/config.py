# Author: urumb
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

    # Model to use explicitly. Mutable at runtime via POST /settings; agents
    # read this attribute on every run rather than capturing it once.
    MODEL_NAME = os.getenv("MODEL_NAME", "llama3.2")

    @staticmethod
    def validate():
        if not os.path.exists(Config.OLLAMA_MODELS_DIR):
             # Just a warning, as Ollama might manage it differently or it might be absolute
             print(f"Warning: OLLAMA_MODELS path '{Config.OLLAMA_MODELS_DIR}' does not exist locally yet.")
