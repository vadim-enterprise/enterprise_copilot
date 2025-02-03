from typing import Dict, Any
from openai import OpenAI
import os
import logging

logger = logging.getLogger(__name__)

def get_context_embedding(client: OpenAI, text: str) -> Dict[str, Any]:
    """Get embedding for context text"""
    try:
        embedding = client.embeddings.create(
            input=text,
            model="text-embedding-ada-002"
        ).data[0].embedding
        return embedding
    except Exception as e:
        logger.error(f"Error getting embedding: {str(e)}")
        return None 