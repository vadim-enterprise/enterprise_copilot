import os
import logging
import openai
from typing import List
from .settings import GPT_MODEL_NAME, DEFAULT_TEMPERATURE

logger = logging.getLogger(__name__)

class PromptManager:
    def __init__(self):
        self.prompts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'prompts')
        if not os.path.exists(self.prompts_dir):
            os.makedirs(self.prompts_dir)

    def load_prompt(self, filename: str) -> str:
        """Load a prompt file from the prompts directory."""
        try:
            file_path = os.path.join(self.prompts_dir, filename)
            logger.info(f"Attempting to load prompt file: {file_path}")
            
            if not os.path.exists(file_path):
                logger.error(f"Prompt file not found: {file_path}")
                raise FileNotFoundError(f"Prompt file not found: {file_path}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                logger.info(f"Successfully loaded prompt file: {filename}")
                return content
                
        except Exception as e:
            logger.error(f"Error loading prompt file {filename}: {str(e)}")
            raise 

    def ask_chatgpt(client, prompt):
        logger.info(f"Sending request to ChatGPT with prompt: {prompt[:50]}...")  # Log first 50 chars of prompt
        try:
            response = client.chat.completions.create(
                model=GPT_MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=DEFAULT_TEMPERATURE,
                max_tokens=1000
            )
            logger.info("Received response from ChatGPT")
            return response.choices[0].message.content
        except openai.APIError as e:
            logger.error(f"OpenAI API Error: {str(e)}")
            return f"OpenAI API Error: {str(e)}"
        except openai.APIConnectionError as e:
            logger.error(f"Failed to connect to OpenAI API: {str(e)}")
            return "Failed to connect to OpenAI API. Please check your internet connection."
        except openai.RateLimitError as e:
            logger.error(f"OpenAI API request exceeded rate limit: {str(e)}")
            return "OpenAI API request exceeded rate limit. Please try again later."
        except openai.AuthenticationError as e:
            logger.error(f"OpenAI API authentication error: {str(e)}")
            return "Authentication with OpenAI failed. Please check your API key."
        except openai.InvalidRequestError as e:
            logger.error(f"Invalid request to OpenAI API: {str(e)}")
            return f"Invalid request to OpenAI API: {str(e)}"
        except Exception as e:
            logger.exception(f"Unexpected error in ChatGPT API call: {str(e)}")



def truncate_at_sentence(self, text: str, max_words: int = 150) -> str:
    """Helper function to truncate text at sentence boundary"""
    # Split into words and count
    words = text.split()
    if len(words) <= max_words:
        return text
    
    # Get the first max_words words
    truncated = ' '.join(words[:max_words])
    
    # Find the last complete sentence
    sentences = truncated.split('.')
    if len(sentences) > 1:
        # Remove incomplete sentence and rejoin
        complete_sentences = sentences[:-1]
        return '. '.join(complete_sentences) + '.'
    else:
        # If no sentence boundary found, try other punctuation
        for punct in ['!', '?', ';']:
            sentences = truncated.split(punct)
            if len(sentences) > 1:
                complete_sentences = sentences[:-1]
                return punct.join(complete_sentences) + punct
    
    # If no sentence boundary found, return at word boundary
    return truncated + '...'

def _chunk_text(self, text: str, chunk_size: int = 500) -> List[str]:
    """Split text into chunks with overlap"""
    chunks = []
    overlap = 50  # Number of words to overlap
    words = text.split()
    
    for i in range(0, len(words), chunk_size - overlap):
        chunk = ' '.join(words[i:i + chunk_size])
        chunks.append(chunk)
        
    return chunks
