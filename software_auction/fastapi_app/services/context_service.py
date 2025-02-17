from typing import List, Dict, Any
import logging
from openai import OpenAI
import os

logger = logging.getLogger(__name__)

class ContextService:
    def __init__(self):
        self.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

    def get_context_embedding(self, text: str, context_docs: List[str]) -> Dict[str, Any]:
        """Get embedding for context text"""
        try:
            if not context_docs:
                logger.warning("No context documents provided")
                return None
            
            # Combine context documents
            combined_context = " ".join(context_docs)
            
            # Get embedding for the context
            response = self.openai_client.embeddings.create(
                input=combined_context,
                model="text-embedding-ada-002"
            )
            
            if not response or not response.data or not response.data[0]:
                logger.warning("No valid embedding response")
                return None
            
            # Ensure we return a dictionary with the embedding
            return {
                'embedding': response.data[0].embedding,
                'documents': context_docs
            }
        except Exception as e:
            logger.error(f"Error getting embedding: {str(e)}")
            return None 