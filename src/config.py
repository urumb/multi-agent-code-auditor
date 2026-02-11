# Author: urumb
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

class Config:
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODELS_DIR = os.getenv("OLLAMA_MODELS", "./local_models")
    CHROMA_PERSIST_DIRECTORY = os.getenv("CHROMA_PERSIST_DIRECTORY", "./chroma_db")
    
    # Model to use explicitly
    MODEL_NAME = "llama3.2" # Default, can be changed or made environmental

    @staticmethod
    def validate():
        if not os.path.exists(Config.OLLAMA_MODELS_DIR):
             # Just a warning, as Ollama might manage it differently or it might be absolute
             print(f"Warning: OLLAMA_MODELS path '{Config.OLLAMA_MODELS_DIR}' does not exist locally yet.")
