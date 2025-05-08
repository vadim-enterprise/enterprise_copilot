from typing import Dict, List, Any
import time
import requests
from urllib.robotparser import RobotFileParser
from urllib.parse import urlparse
from openai import OpenAI
import os
import logging
from django.conf import settings
from .context_service import ContextService
import numpy as np
from dotenv import load_dotenv
from bs4 import BeautifulSoup

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class WebSearchService:
    def __init__(self):
        self.robot_parsers = {}
        self.search_results_cache = {}
        self.cache_expiry = settings.CACHE_EXPIRATION
        self.context_service = ContextService()
        self.knowledge_base_path = os.path.join(settings.BASE_DIR, 'software_auction/knowledge_base/data')
        self.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

    def get_context_embedding(self, text: str) -> Dict[str, Any]:
        """Get embedding for context text with context from knowledge base"""
        try:
            # Get context from text file
            text_file_path = os.path.join(self.knowledge_base_path, 'text.txt')
            with open(text_file_path, 'r') as f:
                context_docs = [f.read()]
                logger.info("context_docs: %s", context_docs)
            
            return self.context_service.get_context_embedding(text, context_docs)
        except Exception as e:
            logger.error(f"Error getting embedding: {str(e)}")
            return None

    def search_and_process(self, query: str, filter_context: bool = True, num_results: int = 10) -> List[Dict[str, Any]]:
        """
        Perform web search and process results
        filter_context: If True, filters results based on similarity during search
        """
        try:
            # Check if the query requires data analysis
            analysis_keywords = ['analyze', 'analysis', 'sql', 'python', 'data', 'database', 'query', 'table', 'column', 'select', 'from', 'where', 'join']
            requires_analysis = any(keyword in query.lower() for keyword in analysis_keywords)
            
            if requires_analysis:
                try:
                    # Try to get context embedding for data analysis
                    context_embedding = self.get_context_embedding(query)
                    if not context_embedding:
                        logger.info("No context embedding found, falling back to general search")
                        return self._perform_general_search(query, num_results)
                except Exception as e:
                    logger.info(f"Error in data analysis, falling back to general search: {str(e)}")
                    return self._perform_general_search(query, num_results)
            
            # Check cache first
            cache_key = f"{query}_{num_results}_{filter_context}"
            if cache_key in self.search_results_cache:
                cache_time, results = self.search_results_cache[cache_key]
                if time.time() - cache_time < self.cache_expiry:
                    logger.info("Returning cached results")
                    return results

            # Initialize RAG and get context if filtering is enabled
            enhanced_query = query
            context_embedding = None
            candidate_results = []
            
            if filter_context:
                try:
                    context_embedding = self.get_context_embedding(query)
                    
                    if not context_embedding:
                        logger.warning("No context embedding found, falling back to general search")
                        return self._perform_general_search(query, num_results)
                    
                    # Generate context embedding once
                    context_text = ' '.join(context_embedding['documents'][0][:10])  # Combine top 3 documents
                    
                    # Extract key concepts and terms from context
                    concept_prompt = f"""
                    Analyze this text and extract:
                    1. Main topics and concepts (3-4 key phrases)
                    2. Technical terms or jargon
                    3. Important names, organizations, or entities
                    4. Specific details that should be matched in search results

                    Text: {context_text}

                    Format the response as a list of search-optimized terms and phrases.
                    """
                    
                    concept_response = self.openai_client.chat.completions.create(
                        model=settings.GPT_MODEL_NAME,
                        messages=[{"role": "user", "content": concept_prompt}],
                        temperature=settings.DEFAULT_TEMPERATURE,
                        max_tokens=150
                    )
                    
                    search_terms = concept_response.choices[0].message.content
                    logger.info(f"Extracted search terms: {search_terms}")
                    
                    # Create a more focused search query
                    enhanced_query = f'"{query}" ({search_terms})'
                    logger.info(f"Enhanced search query: {enhanced_query}")
                except Exception as e:
                    logger.warning(f"Error in context processing, falling back to general search: {str(e)}")
                    return self._perform_general_search(query, num_results)
            
            # Perform the search
            results = self._perform_general_search(enhanced_query, num_results)
            
            # Cache the results
            self.search_results_cache[cache_key] = (time.time(), results)
            logger.info(f"Cached {len(results)} results")
            
            return results
                
        except Exception as e:
            logger.error(f"Search error: {str(e)}")
            return self._perform_general_search(query, num_results)

    def _perform_general_search(self, query: str, num_results: int = 10) -> List[Dict[str, Any]]:
        """Perform a general web search without data analysis"""
        try:
            # Use Google Custom Search API
            search_url = "https://www.googleapis.com/customsearch/v1"
            GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
            SEARCH_ENGINE_ID = os.getenv('SEARCH_ENGINE_ID')
            
            if not GOOGLE_API_KEY or not SEARCH_ENGINE_ID:
                logger.error("Google API credentials not configured")
                return []

            params = {
                'key': GOOGLE_API_KEY,
                'cx': SEARCH_ENGINE_ID,
                'q': query,
                'num': num_results,
                'fields': 'items(title,link,snippet)',
                'prettyPrint': False
            }
            
            response = requests.get(search_url, params=params, timeout=5)
            
            if not response.ok:
                logger.error(f"Search API error: {response.text}")
                return []

            results = response.json()
            items = results.get('items', [])
            
            formatted_results = []
            for item in items:
                if isinstance(item, dict):
                    result = {
                        'url': str(item.get('link', '')),
                        'title': str(item.get('title', '')),
                        'summary': str(item.get('snippet', '')),
                        'timestamp': time.strftime('%Y-%m-%d'),
                        'source': 'google_search'
                    }
                    if result['url'] and result['title'] and result['summary']:
                        formatted_results.append(result)
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error in general search: {str(e)}")
            return []

    def _check_robots_txt(self, url: str) -> bool:
        """Check if URL is allowed by robots.txt"""
        try:
            parsed_url = urlparse(url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            if base_url not in self.robot_parsers:
                rp = RobotFileParser()
                rp.set_url(f"{base_url}/robots.txt")
                try:
                    rp.read()
                except Exception as e:
                    print(f"Error reading robots.txt for {base_url}: {str(e)}")
                    return True
                self.robot_parsers[base_url] = rp
            
            return self.robot_parsers[base_url].can_fetch("*", url)
        except Exception as e:
            print(f"Error checking robots.txt: {str(e)}")
            return False

    def _calculate_cosine_similarity(self, embedding1, embedding2) -> float:
        """Calculate cosine similarity between two embeddings"""
        try:
            import numpy as np
            # Convert embeddings to numpy arrays if they aren't already
            if not isinstance(embedding1, np.ndarray):
                embedding1 = np.array(embedding1)
            if not isinstance(embedding2, np.ndarray):
                embedding2 = np.array(embedding2)
            
            # Ensure embeddings are 1D arrays
            embedding1 = embedding1.flatten()
            embedding2 = embedding2.flatten()
            
            # Check if embeddings are valid
            if embedding1.size == 0 or embedding2.size == 0:
                logger.error("Empty embedding detected")
                return 0.0
            
            if embedding1.size != embedding2.size:
                logger.error(f"Embedding dimensions don't match: {embedding1.size} vs {embedding2.size}")
                return 0.0

            # Calculate similarity
            similarity = np.dot(embedding1, embedding2) / (np.linalg.norm(embedding1) * np.linalg.norm(embedding2))
            return float(similarity)
        except Exception as e:
            logger.error(f"Error calculating similarity: {str(e)}")
            return 0.0

    async def search(self, query: str) -> List[Dict[str, str]]:
        try:
            logger.info(f"Performing web search for: {query}")
            # This is a placeholder implementation
            # In a real application, you would use a proper search API like Google Custom Search
            # or implement your own web scraping logic
            
            # For now, return some dummy results
            return [
                {
                    "title": "Example Result 1",
                    "snippet": "This is an example search result snippet.",
                    "link": "https://example.com/1"
                },
                {
                    "title": "Example Result 2",
                    "snippet": "Another example search result snippet.",
                    "link": "https://example.com/2"
                }
            ]
        except Exception as e:
            logger.error(f"Error performing web search: {str(e)}")
            raise Exception(f"Error performing web search: {str(e)}")
