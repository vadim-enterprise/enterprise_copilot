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
from dotenv import load_dotenv
import psycopg2
import pandas as pd
import json
import re

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
        # Database connections
        self.pred_genai_conn = None
        self.tile_analytics_conn = None
        
    def _get_pred_genai_db_conn(self):
        """Get a connection to the pred_genai database on port 5540"""
        if not self.pred_genai_conn or self.pred_genai_conn.closed:
            self.pred_genai_conn = psycopg2.connect(
                host="localhost",
                port=5540,
                database="pred_genai",
                user="glinskiyvadim"
            )
        return self.pred_genai_conn
        
    def _get_tile_analytics_db_conn(self):
        """Get a connection to the tile_analytics database"""
        if not self.tile_analytics_conn or self.tile_analytics_conn.closed:
            self.tile_analytics_conn = psycopg2.connect(
                host=os.getenv('DB_HOST', 'localhost'),
                port=os.getenv('DB_PORT'),
                database=os.getenv('DB_NAME'),
                user=os.getenv('DB_USER')
            )
        return self.tile_analytics_conn

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

    def get_latest_postgres_dataset(self) -> List[Dict]:
        """Get information about the latest dataset in PostgreSQL on port 5540"""
        try:
            # Connect to the PostgreSQL database
            conn = self._get_pred_genai_db_conn()
            
            # Create a cursor
            cursor = conn.cursor()
            
            # Get list of all tables
            cursor.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_type = 'BASE TABLE'
                ORDER BY table_name;
            """)
            tables = cursor.fetchall()
            
            # Get details about each table
            dataset_info = []
            for table in tables:
                table_name = table[0]
                
                # Get column information
                cursor.execute(f"""
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_name = '{table_name}'
                    ORDER BY ordinal_position;
                """)
                columns = cursor.fetchall()
                
                # Get row count
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                row_count = cursor.fetchone()[0]
                
                # Get a sample of data (first 5 rows)
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 5")
                sample_data = cursor.fetchall()
                
                # Get column names for the sample data
                column_names = [col[0] for col in columns]
                
                # Format sample data as list of dictionaries
                formatted_sample = []
                for row in sample_data:
                    row_dict = {}
                    for i, value in enumerate(row):
                        row_dict[column_names[i]] = str(value)
                    formatted_sample.append(row_dict)
                
                dataset_info.append({
                    "table_name": table_name,
                    "columns": [{"name": col[0], "type": col[1]} for col in columns],
                    "row_count": row_count,
                    "sample_data": formatted_sample
                })
            
            # Don't close the connection, as it's reused
            cursor.close()
            
            return dataset_info
            
        except Exception as e:
            logger.error(f"Error getting PostgreSQL dataset info: {str(e)}")
            return []

    def store_to_tile_data(self, data_dict: Dict[str, str]) -> bool:
        """
        Store data from websearch to the tile_data table in PostgreSQL
        Preserves the schema of the tile_data table
        
        Args:
            data_dict: Dictionary containing data for the tile_data table
                Required key: tile_name
                Optional keys: notification_type, motion, customer, issue
                
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Validate required fields
            if 'tile_name' not in data_dict:
                logger.error("Error: tile_name is required")
                return False
                
            # Ensure only valid fields are included
            valid_fields = {'tile_name', 'notification_type', 'motion', 'customer', 'issue'}
            data_to_insert = {k: v for k, v in data_dict.items() if k in valid_fields}
            
            # Create a connection to the database
            conn = self._get_tile_analytics_db_conn()
            cursor = conn.cursor()
            
            # Check if the tile_name already exists
            cursor.execute("SELECT 1 FROM tile_data WHERE tile_name = %s", (data_dict['tile_name'],))
            already_exists = cursor.fetchone() is not None
            
            if already_exists:
                # Update existing record
                set_clause = ", ".join([f"{field} = %s" for field in data_to_insert.keys() if field != 'tile_name'])
                set_clause += ", updated_at = CURRENT_TIMESTAMP"
                
                query = f"UPDATE tile_data SET {set_clause} WHERE tile_name = %s"
                params = [data_to_insert[field] for field in data_to_insert.keys() if field != 'tile_name']
                params.append(data_dict['tile_name'])
                
                cursor.execute(query, params)
                logger.info(f"Updated existing tile: {data_dict['tile_name']}")
            else:
                # Insert new record
                fields = list(data_to_insert.keys())
                placeholders = ['%s'] * len(fields)
                
                query = f"INSERT INTO tile_data ({', '.join(fields)}) VALUES ({', '.join(placeholders)})"
                params = [data_to_insert[field] for field in fields]
                
                cursor.execute(query, params)
                logger.info(f"Inserted new tile: {data_dict['tile_name']}")
            
            # Commit changes
            conn.commit()
            cursor.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Error storing data to tile_data table: {str(e)}")
            if 'conn' in locals() and conn:
                conn.rollback()
            return False

    def process_csv_for_tiles(self, csv_file_path: str) -> bool:
        """
        Process a CSV file and insert/update records in the tile_data table
        
        Args:
            csv_file_path: Path to the CSV file
                
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Check if file exists
            if not os.path.exists(csv_file_path):
                logger.error(f"Error: File {csv_file_path} does not exist")
                return False
                
            # Read the CSV file
            df = pd.read_csv(csv_file_path)
            logger.info(f"Successfully read CSV with {len(df)} rows")
            
            # Validate required columns
            if 'tile_name' not in df.columns:
                logger.error("Error: CSV must contain 'tile_name' column")
                return False
                
            # Filter to include only valid columns
            valid_columns = {'tile_name', 'notification_type', 'motion', 'customer', 'issue'}
            df_filtered = df[[col for col in df.columns if col in valid_columns]]
            
            # Process each row
            success_count = 0
            for _, row in df_filtered.iterrows():
                # Convert row to dictionary, removing NaN values
                row_dict = {k: v for k, v in row.to_dict().items() if pd.notna(v)}
                
                # Store to tile_data table
                if self.store_to_tile_data(row_dict):
                    success_count += 1
            
            logger.info(f"Successfully processed {success_count} of {len(df)} rows")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Error processing CSV for tiles: {str(e)}")
            return False

    def search_and_process(self, query: str, filter_context: bool = True, num_results: int = 10) -> List[Dict[str, Any]]:
        """
        Perform web search and process results
        filter_context: If True, filters results based on similarity during search
        """
        try:
            # Check if this is a request to store data to tile_data
            tile_data_keywords = ['tile data', 'save tile', 'update tile', 'store tile', 'create tile']
            if any(keyword in query.lower() for keyword in tile_data_keywords):
                try:
                    # Try to extract tile data from the query using AI
                    tile_data = self._extract_tile_data_from_query(query)
                    
                    if tile_data and 'tile_name' in tile_data:
                        # Store the data
                        success = self.store_to_tile_data(tile_data)
                        
                        if success:
                            return [{
                                'url': "postgresql://localhost:5540/tile_analytics/table/tile_data",
                                'title': "Tile Data Updated Successfully",
                                'summary': f"Successfully stored tile: {tile_data['tile_name']}",
                                'timestamp': time.strftime('%Y-%m-%d'),
                                'source': 'tile_data_update'
                            }]
                        else:
                            return [{
                                'url': "postgresql://localhost:5540/tile_analytics/table/tile_data",
                                'title': "Tile Data Update Failed",
                                'summary': f"Failed to store tile data. Please check the format and try again.",
                                'timestamp': time.strftime('%Y-%m-%d'),
                                'source': 'tile_data_update_error'
                            }]
                except Exception as e:
                    logger.error(f"Error processing tile data request: {str(e)}")
                    # Continue with normal search processing
                    pass
            
            # Check if the query requires data analysis
            analysis_keywords = ['analyze', 'analysis', 'sql', 'python', 'data', 'database', 'query', 'table', 'column', 'select', 'from', 'where', 'join']
            requires_analysis = any(keyword in query.lower() for keyword in analysis_keywords)
            
            if requires_analysis:
                try:
                    # Get information about latest dataset in PostgreSQL
                    latest_dataset = self.get_latest_postgres_dataset()
                    if latest_dataset:
                        logger.info(f"Using latest dataset from PostgreSQL for query: {query}")
                        
                        # Format dataset information for inclusion in search results
                        results = []
                        
                        # Create a response with dataset information
                        for table_info in latest_dataset:
                            # Format column information
                            columns_text = ", ".join([f"{col['name']} ({col['type']})" for col in table_info["columns"]])
                            
                            # Format sample data
                            sample_rows = []
                            for row in table_info["sample_data"][:3]:  # Limit to 3 rows for display
                                sample_rows.append(", ".join([f"{k}: {v}" for k, v in row.items()]))
                            
                            sample_data_text = "\n".join(sample_rows)
                            
                            result = {
                                'url': f"postgresql://localhost:5540/pred_genai/table/{table_info['table_name']}",
                                'title': f"Database Table: {table_info['table_name']}",
                                'summary': f"Table with {table_info['row_count']} rows and columns: {columns_text}. Sample data: {sample_data_text}",
                                'timestamp': time.strftime('%Y-%m-%d'),
                                'source': 'postgresql_database'
                            }
                            results.append(result)
                        
                        # Add usage examples
                        usage_example = {
                            'url': "postgresql://localhost:5540/pred_genai",
                            'title': "SQL/Python Query Example",
                            'summary': f"You can use this data for your analysis. SQL example: SELECT * FROM {latest_dataset[0]['table_name']} LIMIT 10; Python example: import pandas as pd; df = pd.read_sql_query('SELECT * FROM {latest_dataset[0]['table_name']}', 'postgresql://glinskiyvadim@localhost:5540/pred_genai')",
                            'timestamp': time.strftime('%Y-%m-%d'),
                            'source': 'suggestion'
                        }
                        results.append(usage_example)
                        
                        return results
                    else:
                        # Try to get context embedding for data analysis as fallback
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

    def _extract_tile_data_from_query(self, query: str) -> Dict[str, str]:
        """
        Extract tile data from a natural language query using AI
        
        Args:
            query: Natural language query asking to save tile data
                
        Returns:
            dict: Dictionary with tile data fields
        """
        try:
            # Create a prompt for the AI
            prompt = f"""
            Extract structured tile data from the following query. 
            The tile data should include at least the 'tile_name' field, which is required.
            Other optional fields are 'notification_type', 'motion', 'customer', and 'issue'.
            
            Format your response as a valid JSON object containing only the extracted fields.
            Include only the fields that are explicitly mentioned in the query.
            
            Query: {query}
            """
            
            # Get the AI response
            response = self.openai_client.chat.completions.create(
                model=settings.GPT_MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=250
            )
            
            # Parse the response
            content = response.choices[0].message.content
            
            # Extract JSON from response
            try:
                # Try to extract JSON from the response if it's not already in JSON format
                json_match = re.search(r'({.*})', content, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    json_str = content
                    
                tile_data = json.loads(json_str)
                logger.info(f"Extracted tile data: {tile_data}")
                return tile_data
            except json.JSONDecodeError:
                logger.error(f"Failed to parse JSON from response: {content}")
                return None
            
        except Exception as e:
            logger.error(f"Error extracting tile data from query: {str(e)}")
            return None

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

    def process_query(self, query: str) -> Dict[str, Any]:
        """
        Process a natural language query and return relevant information
        """
        try:
            # Check if this is a request to store data to tile_analytics
            tile_analytics_keywords = ['tile analytics', 'save analytics', 'update analytics', 'store analytics', 'create analytics']
            if any(keyword in query.lower() for keyword in tile_analytics_keywords):
                logger.info("Detected tile analytics storage request")
                tile_analytics = self._extract_tile_analytics_from_query(query)
                
                if tile_analytics and 'name' in tile_analytics:
                    success = self.store_to_tile_analytics(tile_analytics)
                    return {
                        'success': success,
                        'url': "postgresql://localhost:5540/tile_analytics/table/tile_analytics",
                        'summary': f"Successfully stored analytics for: {tile_analytics['name']}",
                        'source': 'tile_analytics_update'
                    } if success else {
                        'success': False,
                        'url': "postgresql://localhost:5540/tile_analytics/table/tile_analytics",
                        'summary': f"Failed to store analytics for: {tile_analytics['name']}",
                        'source': 'tile_analytics_update_error'
                    }
            
            # Process CSV file if present
            if hasattr(self, 'csv_file') and self.csv_file:
                return self.process_csv_file()
            
            # Default web search behavior
            return self._perform_web_search(query)
            
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            return {
                'success': False,
                'summary': f"Error processing query: {str(e)}",
                'source': 'error'
            }

    def _extract_tile_analytics_from_query(self, query: str) -> Dict[str, str]:
        """
        Extract tile analytics data from a natural language query
        """
        try:
            # Look for JSON-like structure in the query
            json_str = query[query.find('{'):query.rfind('}')+1]
            if not json_str:
                return None
            
            tile_analytics = json.loads(json_str)
            logger.info(f"Extracted tile analytics: {tile_analytics}")
            return tile_analytics
        except Exception as e:
            logger.error(f"Error extracting tile analytics from query: {str(e)}")
            return None
