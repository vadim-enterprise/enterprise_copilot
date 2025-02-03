# Model Settings
GPT_MODEL_NAME = "gpt-4-turbo-preview"
EMBEDDING_MODEL_NAME = "text-embedding-ada-002"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 500

# AI Model Config
AI_MODEL_CONFIG = {
    'USE_LLAMA': False,
    'OPENAI_MODEL': 'gpt-4',
    'TEMPERATURE': 0.7
}

# Path Settings
import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) 