from typing import Optional, List, Dict, Any
import logging
import os
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from openai import OpenAI
from ..settings import AI_MODEL_CONFIG
import psycopg2
from psycopg2.extras import RealDictCursor
from .analytics_service import AnalyticsService

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class ChatService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            self.logger.error("OPENAI_API_KEY not found in environment variables")
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        self.client = OpenAI(api_key=self.api_key)
        self.model = AI_MODEL_CONFIG['OPENAI_MODEL']
        self.temperature = AI_MODEL_CONFIG['TEMPERATURE']
        self.logger.info(f"ChatService initialized successfully with model: {self.model}")
        
        # Database connection
        self.db_conn = psycopg2.connect(
            dbname='pred_genai',
            user='glinskiyvadim',
            host='localhost',
            port='5540'
        )

        self.analytics_service = AnalyticsService()

    def _get_relevant_csv_data(self, query: str) -> str:
        """
        Get relevant CSV data from the database based on the query.
        Returns a string containing the data in a format suitable for the AI.
        """
        try:
            # First, ensure the csv_metadata table exists
            with self.db_conn.cursor() as cur:
                # Create csv_metadata table if it doesn't exist
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS csv_metadata (
                        table_name VARCHAR(255) PRIMARY KEY,
                        column_names TEXT[],
                        upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                self.db_conn.commit()

            # Get information about available tables
            with self.db_conn.cursor(cursor_factory=RealDictCursor) as cur:
                # First check if we have any tables in csv_metadata
                cur.execute("""
                    SELECT COUNT(*) as count
                    FROM csv_metadata
                """)
                count_result = cur.fetchone()
                
                if count_result['count'] == 0:
                    # If no tables in csv_metadata, check for any tables in the database
                    cur.execute("""
                        SELECT table_name 
                        FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_type = 'BASE TABLE'
                        AND table_name != 'csv_metadata'
                    """)
                    tables = cur.fetchall()
                    
                    if not tables:
                        return "No datasets are available for analysis."
                    
                    # For each table found, get its columns and add to csv_metadata
                    for table in tables:
                        table_name = table['table_name']
                        cur.execute(f"""
                            SELECT column_name 
                            FROM information_schema.columns 
                            WHERE table_name = %s
                            ORDER BY ordinal_position
                        """, (table_name,))
                        columns = [row['column_name'] for row in cur.fetchall()]
                        
                        # Insert into csv_metadata
                        cur.execute("""
                            INSERT INTO csv_metadata (table_name, column_names)
                            VALUES (%s, %s)
                            ON CONFLICT (table_name) DO UPDATE 
                            SET column_names = EXCLUDED.column_names,
                                upload_date = CURRENT_TIMESTAMP
                        """, (table_name, columns))
                    
                    self.db_conn.commit()
                
                # Now get the most recent table's information
                cur.execute("""
                    SELECT table_name, column_names
                    FROM csv_metadata
                    ORDER BY upload_date DESC
                    LIMIT 1
                """)
                table_info = cur.fetchone()

            if not table_info:
                return "No datasets are available for analysis."

            # Get a sample of the data (first 10 rows)
            with self.db_conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(f"SELECT * FROM {table_info['table_name']} LIMIT 10")
                sample_data = [dict(row) for row in cur.fetchall()]

            # Format the data for context
            context = f"Available data from {table_info['table_name']}:\n"
            context += f"Columns: {', '.join(table_info['column_names'])}\n\n"
            context += "Sample data (first 10 rows):\n"
            
            for i, row in enumerate(sample_data, 1):
                context += f"Row {i}:\n"
                for key, value in row.items():
                    if value is None:
                        value = "NULL"
                    context += f"  {key}: {value}\n"
                context += "\n"

            return context

        except Exception as e:
            self.logger.error(f"Error getting CSV data: {str(e)}")
            # Reset any failed transaction
            self.db_conn.rollback()
            return "Error retrieving data from the database."

    def _format_analytics_results(self, analytics_result: dict) -> str:
        """
        Format analytics results in a way that's easy for the AI to understand and use.
        """
        if analytics_result["type"] == "regression":
            return f"""
Regression Analysis Results:
- Target Variable: {analytics_result['target']}
- Features: {', '.join(analytics_result['features'])}
- Model Performance:
  * R² Score: {analytics_result['r2_score']:.3f}
  * RMSE: {analytics_result['metrics']['rmse']:.3f}
  * MAE: {analytics_result['metrics']['mae']:.3f}
- Feature Coefficients:
{chr(10).join(f'  {feature}: {coef:.3f}' for feature, coef in analytics_result['coefficients'].items())}
- Feature Importance (sorted by impact):
{chr(10).join(f'  {feature}: {importance:.3f}' for feature, importance in analytics_result['feature_importance'].items())}
- Sample Predictions (first 5):
{chr(10).join(f'  Actual: {actual:.2f}, Predicted: {pred:.2f}' for actual, pred in zip(analytics_result['actual_values'][:5], analytics_result['predictions'][:5]))}
"""
        elif analytics_result["type"] == "correlation":
            return f"""
Correlation Analysis Results:
- Strong Correlations Found:
{chr(10).join(f'  {corr["variable1"]} and {corr["variable2"]}: {corr["correlation"]:.3f}' for corr in analytics_result['strong_correlations'])}
"""
        elif analytics_result["type"] == "time_series":
            return f"""
Time Series Analysis Results:
- Time Column: {analytics_result['time_column']}
- Metrics by Variable:
{chr(10).join(f'  {var}:' + chr(10) + chr(10).join(f'    {metric}: {value:.3f}' for metric, value in metrics.items()) for var, metrics in analytics_result['metrics'].items())}
"""
        else:  # basic analysis
            return f"""
Basic Statistical Analysis:
- Numeric Variables:
{chr(10).join(f'  {var}:' + chr(10) + chr(10).join(f'    {metric}: {value:.3f}' for metric, value in metrics.items()) for var, metrics in analytics_result['numeric_analysis'].items())}
- Categorical Variables:
{chr(10).join(f'  {var}:' + chr(10) + chr(10).join(f'    {metric}: {value}' for metric, value in metrics.items()) for var, metrics in analytics_result['categorical_analysis'].items())}
"""

    async def _get_chat_response(self, query: str, context: str) -> str:
        """
        Generate a chat response using the OpenAI API based on the query and context.
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": """You are a helpful data analyst assistant. 
                    Your role is to:
                    1. Analyze data and provide clear insights
                    2. Explain complex patterns in simple terms
                    3. Highlight important trends and relationships
                    4. Provide actionable recommendations when appropriate
                    5. Be precise and data-driven in your responses"""},
                    {"role": "system", "content": f"Context information:\n{context}"},
                    {"role": "user", "content": query}
                ],
                temperature=self.temperature,
                max_tokens=1000
            )
            
            if not response.choices or not response.choices[0].message:
                raise ValueError("Invalid response format from OpenAI")
            
            return response.choices[0].message.content
            
        except Exception as e:
            self.logger.error(f"Error generating chat response: {str(e)}")
            raise

    def _determine_web_search_needed(self, query: str, response: str) -> bool:
        """
        Determine if web search is needed based on the query and initial response.
        """
        # Keywords that might indicate need for external information
        search_keywords = [
            "latest", "recent", "current", "trend", "news", "update",
            "compare", "versus", "vs", "difference", "similar"
        ]
        
        # Check if query contains search keywords
        query_lower = query.lower()
        if any(keyword in query_lower for keyword in search_keywords):
            return True
            
        # Check if response indicates uncertainty
        uncertainty_phrases = [
            "I don't know", "I'm not sure", "I can't find",
            "no information", "unable to determine"
        ]
        
        response_lower = response.lower()
        if any(phrase in response_lower for phrase in uncertainty_phrases):
            return True
            
        return False

    async def _perform_web_search(self, query: str) -> str:
        """
        Perform a web search to gather additional information.
        """
        try:
            # Use Google Custom Search API
            api_key = os.getenv('GOOGLE_API_KEY')
            search_engine_id = os.getenv('SEARCH_ENGINE_ID')
            
            if not api_key or not search_engine_id:
                return "Web search is not configured."
                
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                'key': api_key,
                'cx': search_engine_id,
                'q': query
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            search_results = response.json()
            
            # Format search results
            formatted_results = "Web search results:\n\n"
            for item in search_results.get('items', [])[:3]:  # Get top 3 results
                formatted_results += f"Title: {item.get('title', 'N/A')}\n"
                formatted_results += f"Link: {item.get('link', 'N/A')}\n"
                formatted_results += f"Snippet: {item.get('snippet', 'N/A')}\n\n"
                
            return formatted_results
            
        except Exception as e:
            self.logger.error(f"Error performing web search: {str(e)}")
            return "Error performing web search."

    def _combine_responses(self, query: str, initial_response: str, web_results: str, context: str) -> str:
        """
        Combine the initial response with web search results.
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": """You are a helpful data analyst assistant.
                    Your task is to combine the initial analysis with web search results to provide
                    a comprehensive response. Make sure to:
                    1. Maintain consistency between different sources
                    2. Highlight any contradictions or additional insights
                    3. Provide a well-structured, coherent response
                    4. Cite sources when appropriate"""},
                    {"role": "system", "content": f"Context information:\n{context}"},
                    {"role": "system", "content": f"Initial analysis:\n{initial_response}"},
                    {"role": "system", "content": f"Web search results:\n{web_results}"},
                    {"role": "user", "content": query}
                ],
                temperature=self.temperature,
                max_tokens=1500
            )
            
            if not response.choices or not response.choices[0].message:
                raise ValueError("Invalid response format from OpenAI")
            
            return response.choices[0].message.content
            
        except Exception as e:
            self.logger.error(f"Error combining responses: {str(e)}")
            return initial_response  # Fallback to initial response if combination fails

    async def get_response(self, query: str) -> str:
        """
        Get a response for the user's query, handling both chat and data analysis.
        """
        try:
            # Check if the query is data-related
            data_keywords = [
                "data", "analysis", "statistics", "table", "database", "query",
                "sql", "regression", "correlation", "trend", "predict", "forecast",
                "relationship", "analyze", "metrics", "values", "columns", "rows"
            ]
            
            is_data_query = any(keyword in query.lower() for keyword in data_keywords)
            
            if not is_data_query:
                # For non-data queries, use OpenAI directly without any data context
                try:
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": "You are a helpful AI assistant. Provide clear, concise, and accurate responses to user questions."},
                            {"role": "user", "content": query}
                        ],
                        temperature=self.temperature,
                        max_tokens=1000
                    )
                    return response.choices[0].message.content
                except Exception as e:
                    self.logger.error(f"Error in direct chat response: {str(e)}")
                    return f"I apologize, but I encountered an error while processing your query. Please try again."
            
            # For data queries, proceed with data analysis
            try:
                # First try Python-based analytics for complex analysis
                should_use_python = any(keyword in query.lower() for keyword in [
                    "regression", "correlation", "trend", "predict", "forecast",
                    "relationship", "analyze", "analysis", "statistics", "statistical"
                ])
                
                if should_use_python:
                    try:
                        # Perform Python-based analytics
                        self.logger.info("Starting Python-based analytics")
                        analytics_result = self.analytics_service.analyze_data(query)
                        
                        if analytics_result:
                            self.logger.info(f"Analytics completed successfully: {analytics_result['type']}")
                            # Format analytics results for the AI
                            analytics_context = self._format_analytics_results(analytics_result)
                            
                            # Generate response based on analytics results
                            response = await self._get_chat_response(
                                query,
                                f"Based on the following analysis results, provide a detailed explanation:\n{analytics_context}"
                            )
                            return response
                        else:
                            self.logger.warning("Analytics returned no results")
                    except Exception as e:
                        self.logger.error(f"Python analytics failed: {str(e)}")
                        # Fall back to SQL if Python analytics fails
                        pass
                
                # If Python analytics failed or wasn't appropriate, try SQL-based analysis
                try:
                    # Reset any failed transaction
                    self.db_conn.rollback()
                    
                    # Get context from database
                    context = self._get_relevant_csv_data(query)
                    
                    # Get information about available tables
                    with self.db_conn.cursor(cursor_factory=RealDictCursor) as cur:
                        cur.execute("""
                            SELECT table_name, column_names
                            FROM csv_metadata
                            ORDER BY upload_date DESC
                        """)
                        tables_info = [dict(row) for row in cur.fetchall()]
                    
                    if not tables_info:
                        return "No datasets are available for analysis."
                    
                    # Convert query to SQL
                    sql_query = await self._convert_to_sql(query, tables_info)
                    
                    # Execute SQL query
                    sql_results = await self._execute_sql(sql_query)
                    
                    # Generate response from SQL results
                    return await self._generate_response(query, sql_results, sql_query)
                    
                except Exception as sql_error:
                    self.logger.error(f"Error in SQL analysis: {str(sql_error)}")
                    # Reset any failed transaction
                    self.db_conn.rollback()
                    
                    # If both Python and SQL analysis fail, try a basic chat response with context
                    try:
                        response = await self._get_chat_response(query, context)
                        return response
                    except Exception as chat_error:
                        self.logger.error(f"Error in fallback chat response: {str(chat_error)}")
                        return f"I apologize, but I encountered an error while analyzing the data. Please try rephrasing your question."
                    
            except Exception as e:
                self.logger.error(f"Error in data analysis: {str(e)}")
                # Reset any failed transaction
                self.db_conn.rollback()
                return f"I apologize, but I encountered an error while processing your query. Please try again."
                
        except Exception as e:
            self.logger.error(f"Error in get_response: {str(e)}")
            # Reset any failed transaction
            self.db_conn.rollback()
            return f"I apologize, but I encountered an error while processing your query. Please try again."

    async def _convert_to_sql(self, query: str, tables_info: List[Dict[str, Any]]) -> str:
        """Convert natural language query to SQL"""
        try:
            # Create context about available tables
            tables_context = "\n".join([
                f"Table: {table['table_name']}\nColumns: {', '.join(table['column_names'])}"
                for table in tables_info
            ])
            
            # Ask AI to convert to SQL
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": """You are a SQL expert. Convert the user's question into a SQL query.
                    Use the following guidelines:
                    1. Only use tables and columns that are available
                    2. Use proper PostgreSQL syntax
                    3. For regression analysis, use REGR_SLOPE and REGR_INTERCEPT functions
                    4. Use WITH clauses for complex queries
                    5. Return ONLY the SQL query, no markdown formatting, no explanations, no backticks
                    6. Do not include any text that is not SQL
                    7. Do not include any comments or explanations
                    8. Do not include any variable declarations or SET statements"""},
                    {"role": "system", "content": f"Available tables and columns:\n{tables_context}"},
                    {"role": "user", "content": f"Convert this question to SQL: {query}"}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            if not response.choices or not response.choices[0].message:
                raise ValueError("Invalid response format from OpenAI")
            
            # Clean up the SQL query - remove any markdown formatting and non-SQL text
            sql_query = response.choices[0].message.content.strip()
            sql_query = sql_query.replace('```sql', '').replace('```', '').strip()
            
            # Remove any non-SQL text (like explanations or comments)
            if ';' in sql_query:
                sql_query = sql_query.split(';')[0] + ';'
            
            # Validate that the query only contains SQL
            if not all(c.isalnum() or c in ' .,;()[]{}_+-*/=<>!@#$%^&|\\\'\"' for c in sql_query):
                raise ValueError("Invalid SQL query generated")
            
            return sql_query
            
        except Exception as e:
            self.logger.error(f"Error converting to SQL: {str(e)}")
            raise

    async def _execute_sql(self, sql_query: str) -> List[Dict[str, Any]]:
        """Execute SQL query and return results"""
        try:
            with self.db_conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql_query)
                results = [dict(row) for row in cur.fetchall()]
                return results
                
        except Exception as e:
            self.logger.error(f"Error executing SQL: {str(e)}")
            self.logger.error(f"SQL Query: {sql_query}")
            raise

    async def _generate_response(self, query: str, sql_results: List[Dict[str, Any]], sql_query: str) -> str:
        """Generate natural language response from SQL results"""
        try:
            if not sql_results:
                return "No results found for your query."
                
            # Format results for context
            results_context = []
            for i, row in enumerate(sql_results, 1):
                row_str = f"Row {i}:"
                for key, value in row.items():
                    if value is None:
                        value = "NULL"
                    row_str += f"\n  {key}: {value}"
                results_context.append(row_str)
            
            results_text = "\n\n".join(results_context)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": """You are a data analyst. Generate a clear, natural language response based on the SQL query results.
                    Guidelines:
                    1. Use specific numbers and values from the results
                    2. Explain the findings in simple terms
                    3. Highlight key insights
                    4. If no results were found, explain why
                    5. Be precise and data-driven"""},
                    {"role": "system", "content": f"Original question: {query}\nSQL query used: {sql_query}\nQuery results:\n{results_text}"},
                    {"role": "user", "content": "Please provide a clear answer to the original question based on these results."}
                ],
                temperature=self.temperature,
                max_tokens=1000
            )
            
            if not response.choices or not response.choices[0].message:
                raise ValueError("Invalid response format from OpenAI")
            
            return response.choices[0].message.content
            
        except Exception as e:
            self.logger.error(f"Error generating response: {str(e)}")
            raise 