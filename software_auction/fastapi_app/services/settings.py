# OpenAI Model Settings
GPT_MODEL_NAME = "gpt-4-turbo-preview"  # or "gpt-3.5-turbo" for a cheaper option
EMBEDDING_MODEL_NAME = "text-embedding-ada-002"
DEFAULT_TEMPERATURE = 0.7

# Search Settings
MAX_SEARCH_RESULTS = 10
SEARCH_CACHE_DURATION = 3600  # 1 hour in seconds
MIN_SIMILARITY_SCORE = 0.5

# API Keys and Endpoints
GOOGLE_API_KEY = "AIzaSyDctFXmLx_HK-EFl-oydmS7lbNy4LqLDTc"  # Replace with your actual API key
SEARCH_ENGINE_ID = "72d32c5973c70499e"  # Replace with your actual search engine ID

# Caching Settings
CACHE_ENABLED = True
CACHE_TYPE = "memory"  # Options: "memory", "redis", "file"
CACHE_EXPIRATION = 3600  # 1 hour in seconds

# Logging Settings
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s" 