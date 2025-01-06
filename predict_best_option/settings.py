import certifi

POSTHOG_CONFIG = {
    'api_key': 'your-api-key',
    'host': 'https://us.i.posthog.com',
    'verify_ssl': certifi.where()
}

POSTHOG_DISABLED = True 

# OpenAI Model Settings
GPT_MODEL_NAME = "gpt-4o"
EMBEDDING_MODEL_NAME = "text-embedding-ada-002"

# Model Parameters
DEFAULT_TEMPERATURE = 0.3
DEFAULT_MAX_TOKENS = 500 