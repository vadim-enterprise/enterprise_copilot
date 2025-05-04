# Model Settings
GPT_MODEL_NAME = "gpt-4o"
EMBEDDING_MODEL_NAME = "text-embedding-ada-002"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 500

# AI Model Config
AI_MODEL_CONFIG = {
    'USE_LLAMA': False,
    'OPENAI_MODEL': 'gpt-4o',
    'TEMPERATURE': 0.7
}

# Path Settings
import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Server Settings
HOST = "127.0.0.1"
PORT = 8001

# CORS Settings
ALLOWED_ORIGINS = [
    "http://127.0.0.1:8000",  # Django server
    "http://localhost:8000",   # Django server alternative
    "http://127.0.0.1:8001",  # FastAPI server
    "http://localhost:8001",   # FastAPI server alternative
] 