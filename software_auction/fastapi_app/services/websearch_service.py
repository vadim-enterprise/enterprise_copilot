from typing import Dict, List, Any
import time
import requests
from urllib.robotparser import RobotFileParser
from urllib.parse import urlparse
from openai import OpenAI
import os
import logging
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
from django.conf import settings
from ..models.search_types import ModelChoice
from .context_service import ContextService
import numpy as np

logger = logging.getLogger(__name__)

class WebSearchService:
    def __init__(self, model_choice: ModelChoice = ModelChoice.OPENAI):
        self.robot_parsers = {}
        self.search_results_cache = {}
        self.cache_expiry = settings.CACHE_EXPIRATION
        self.model_choice = model_choice
        self.context_service = ContextService()
        self.knowledge_base_path = os.path.join(settings.BASE_DIR, 'software_auction/knowledge_base/data')
        
        if model_choice == ModelChoice.OPENAI:
            self.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        else:
            self.openai_client = None
            model_name = "meta-llama/Llama-2-7b-chat-hf"
            self.llama_tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.llama_model = AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype=torch.float16,
                device_map="auto"
            )

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
            candidate_results = []  # Store all potentially good results
            
            if filter_context:
                context_embedding = self.get_context_embedding(query)
                
                if not context_embedding:
                    logger.warning("No context embedding found")
                    return []
                
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
                
            page = 1
            max_attempts = 10  # Maximum number of search pages to try
            consecutive_empty_pages = 0  # Track pages without valid results

            # Use Google Custom Search API with enhanced query and pagination
            search_url = "https://www.googleapis.com/customsearch/v1"
            GOOGLE_API_KEY = "AIzaSyDctFXmLx_HK-EFl-oydmS7lbNy4LqLDTc"
            SEARCH_ENGINE_ID = "72d32c5973c70499e"            

            while page <= max_attempts and consecutive_empty_pages < 3:  # Google only allows up to 100 results (10 pages)
                logger.info(f"Searching page {page}")
                
                params = {
                    'key': GOOGLE_API_KEY,
                    'cx': SEARCH_ENGINE_ID,
                    'q': enhanced_query,
                    'num': 10,
                    'start': ((page - 1) * 10) + 1,
                    'fields': 'items(title,link,snippet)',
                    'prettyPrint': False,
                    'exactTerms': query,
                }
                
                response = requests.get(search_url, params=params, timeout=5)
                logger.info(f"Search API response status: {response.status_code} for page {page}")
                
                if not response.ok:
                    logger.error(f"Search API error: {response.text}")
                    page += 1
                    consecutive_empty_pages += 1
                    continue

                results = response.json()
                
                if not isinstance(results, dict):
                    logger.error(f"Results is not a dictionary: {type(results)}")
                    continue
                
                if 'items' not in results:
                    logger.info(f"No items in search results for page {page}")
                    page += 1
                    consecutive_empty_pages += 1
                    continue

                items = results.get('items', [])
                if not isinstance(items, list):
                    logger.error(f"Items is not a list: {type(items)}")
                    continue

                found_valid_result = False
                
                # Process results one at a time
                for item in items:
                    try:
                        # Ensure we have valid item data
                        if not isinstance(item, dict):
                            logger.warning(f"Invalid item format: {item}")
                            continue

                        result = {
                            'url': str(item.get('link', '')),
                            'title': str(item.get('title', '')),
                            'summary': str(item.get('snippet', '')),
                            'timestamp': time.strftime('%Y-%m-%d'),
                            'source': 'google_search'
                        }
                        
                        if not (result['url'] and result['title'] and result['summary']):
                            logger.warning("Missing required fields in search result")
                            continue

                        # Calculate similarity if context is available
                        if filter_context and context_embedding:
                            result_text = f"{result['title']}\n{result['summary']}"
                            try:
                                # Get embedding for result text
                                response = self.openai_client.embeddings.create(
                                    input=result_text,
                                    model=settings.EMBEDDING_MODEL_NAME
                                )
                                
                                # Access the embedding from the response
                                if not response or not response.data or not response.data[0]:
                                    logger.warning(f"No valid embedding response for result: {result['title']}")
                                    continue
                                
                                result_embedding = response.data[0].embedding
                            except Exception as embed_error:
                                logger.error(f"Error getting embedding for result: {str(embed_error)}")
                                continue
                            
                            if not result_embedding:
                                logger.warning(f"No embedding generated for result: {result['title']}")
                                continue
                            
                            context_embedding_vector = context_embedding['embedding']
                            if not context_embedding_vector:
                                logger.warning("No embedding vector in context")
                                continue
                            
                            if not isinstance(result_embedding, (list, np.ndarray)):
                                logger.warning(f"Invalid result embedding type: {type(result_embedding)}")
                                continue
                            
                            similarity = self._calculate_cosine_similarity(context_embedding_vector, result_embedding)
                            logger.info(f"Similarity score for {result['title']}: {similarity}")
                            
                            if similarity <= settings.MIN_SIMILARITY_SCORE:
                                logger.info(f"Skipping result due to low similarity: {result['title']}")
                                continue
                            
                            result['similarity_score'] = similarity
                            found_valid_result = True
                            candidate_results.append(result)
                            logger.info(f"Added candidate result: {result['title']} with score {similarity}")
                        else:
                            candidate_results.append(result)
                            found_valid_result = True
                            
                    except Exception as e:
                        logger.error(f"Error processing search result: {str(e)}")
                        continue
                
                logger.info(f"Processed page {page}, found {len(candidate_results)} total candidates so far")
                
                if found_valid_result:
                    consecutive_empty_pages = 0
                else:
                    consecutive_empty_pages += 1
                    
                page += 1

            # Sort all candidates by similarity score
            if filter_context:
                candidate_results.sort(key=lambda x: x.get('similarity_score', 0), reverse=True)
                logger.info("Sorted candidates by similarity score")
                
                # Log top scores for debugging
                for i, result in enumerate(candidate_results[:num_results]):
                    logger.info(f"Top {i+1} result: {result['title']} - Score: {result.get('similarity_score', 0)}")

            # Select top results
            final_results = candidate_results[:num_results]
            
            # Cache the results
            self.search_results_cache[cache_key] = (time.time(), final_results)
            logger.info(f"Cached {len(final_results)} results from {len(candidate_results)} candidates")
            
            return final_results
                
        except Exception as e:
            logger.error(f"Search error: {str(e)}")
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
