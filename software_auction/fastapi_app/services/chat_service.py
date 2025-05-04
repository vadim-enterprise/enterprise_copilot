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

    async def get_response(self, query: str) -> str:
        try:
            self.logger.info(f"Processing query: {query}")
            
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
            
            # Convert question to SQL
            sql_query = await self._convert_to_sql(query, tables_info)
            self.logger.info(f"Generated SQL query: {sql_query}")
            
            # Execute SQL query
            sql_results = await self._execute_sql(sql_query)
            self.logger.info(f"SQL query returned {len(sql_results)} results")
            
            # Generate natural language response
            response = await self._generate_response(query, sql_results, sql_query)
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error processing query: {str(e)}")
            return f"Error processing your query: {str(e)}"

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
                    2. Use proper SQL syntax
                    3. Include necessary JOINs if querying multiple tables
                    4. Use appropriate aggregation functions when needed
                    5. Return ONLY the SQL query, no markdown formatting, no explanations, no backticks"""},
                    {"role": "system", "content": f"Available tables and columns:\n{tables_context}"},
                    {"role": "user", "content": f"Convert this question to SQL: {query}"}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            if not response.choices or not response.choices[0].message:
                raise ValueError("Invalid response format from OpenAI")
            
            # Clean up the SQL query - remove any markdown formatting
            sql_query = response.choices[0].message.content.strip()
            sql_query = sql_query.replace('```sql', '').replace('```', '').strip()
            
            return sql_query
            
        except Exception as e:
            self.logger.error(f"Error converting to SQL: {str(e)}")
            raise

    async def _execute_sql(self, sql_query: str) -> List[Dict[str, Any]]:
        """Execute SQL query and return results"""
        try:
            with self.db_conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql_query)
                return cur.fetchall()
                
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