from typing import List, Dict, Any
import logging
import os
import requests
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

    async def _generate_analysis_response(self, query: str, analytics_result: dict) -> str:
        """
        Generate a response based on the analytics result.
        """
        try:
            analysis_type = analytics_result.get('type', 'basic')
            
            if analysis_type == "regression":
                features = analytics_result['features']
                target = analytics_result['target']
                metrics = analytics_result['metrics']
                
                # Format regression results with code
                response = f"""
## Regression Analysis Results

**Target Variable:** {target}
**Features:** {', '.join(features)}

**Metrics:**
```
R² Score: {metrics['r2_score']:.3f}
RMSE: {metrics['rmse']:.3f}
MAE: {metrics['mae']:.3f}
```

**Top Feature Importance:**
```
{chr(10).join(f'- {feature}: {importance:.3f}' for feature, importance in analytics_result['feature_importance'][:5])}
```

**Python Code to Reproduce:**
```python
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, mean_absolute_error
from sklearn.preprocessing import StandardScaler

# Prepare your data
features = {features}
target = '{target}'
X = df[features]
y = df[target]

# Scale features
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# Train the model
model = LinearRegression()
model.fit(X_scaled, y)

# Make predictions
y_pred = model.predict(X_scaled)

# Evaluate the model
r2_score = model.score(X_scaled, y)
rmse = np.sqrt(mean_squared_error(y, y_pred))
mae = mean_absolute_error(y, y_pred)

# Print results
print(f'R² Score: {r2_score:.3f}')
print(f'RMSE: {rmse:.3f}')
print(f'MAE: {mae:.3f}')

# Feature importance
coeffs = pd.DataFrame({'Feature': features, 'Coefficient': model.coef_})
coeffs['Abs_Coefficient'] = abs(coeffs['Coefficient'])
coeffs = coeffs.sort_values('Abs_Coefficient', ascending=False)
print("Feature Importance:")
print(coeffs)
```

**Sample Predictions (Actual vs Predicted):**
```
{chr(10).join(f'- Actual: {actual:.2f}, Predicted: {pred:.2f}' for actual, pred in zip(analytics_result['actual_values'][:5], analytics_result['predictions'][:5]))}
```
"""
                return response
                
            elif analysis_type == "correlation":
                correlations = analytics_result['strong_correlations']
                
                # Format correlation results with code
                response = f"""
## Correlation Analysis Results

**Strong Correlations Found:**
```
{chr(10).join(f'- {corr["variable1"]} and {corr["variable2"]}: {corr["correlation"]:.3f}' for corr in correlations)}
```

**Python Code to Reproduce:**
```python
import pandas as pd
import numpy as np
import seaborn as sns

# Calculate correlation matrix
corr_matrix = df.corr()

# Find strong correlations
strong_corrs = []
for i in range(len(corr_matrix.columns)):
    for j in range(i):
        if abs(corr_matrix.iloc[i, j]) > 0.7:  # Threshold for strong correlation
            strong_corrs.append({
                'variable1': corr_matrix.columns[i],
                'variable2': corr_matrix.columns[j],
                'correlation': corr_matrix.iloc[i, j]
            })

# Sort by absolute correlation
strong_corrs = sorted(strong_corrs, key=lambda x: abs(x['correlation']), reverse=True)

# Print strong correlations
for corr in strong_corrs:
    print(f"{corr['variable1']} and {corr['variable2']}: {corr['correlation']:.3f}")
```
"""
                return response
                
            elif analysis_type == "time_series":
                time_column = analytics_result['time_column']
                metrics = analytics_result['metrics']
                
                # Format time series results with code
                response = f"""
## Time Series Analysis Results

**Time Column:** {time_column}

**Metrics by Variable:**
```
{chr(10).join(f'- {var}:' + chr(10) + chr(10).join(f'  * {metric}: {value:.3f}' for metric, value in var_metrics.items()) for var, var_metrics in metrics.items())}
```

**Python Code to Reproduce:**
```python
import pandas as pd
import numpy as np
from statsmodels.tsa.seasonal import seasonal_decompose

# Identify time column
time_col = '{time_column}'

# Ensure time column is in datetime format
df[time_col] = pd.to_datetime(df[time_col])
df = df.sort_values(time_col)

# Set the time column as index
df_ts = df.set_index(time_col)

# Select numeric columns
numeric_cols = df_ts.select_dtypes(include=[np.number]).columns

# Calculate statistics for each numeric column
for col in numeric_cols[:3]:  # Analyze first 3 numeric columns
    print(f"\\nAnalyzing {col}:")
    ts = df_ts[col]
    print(f"Mean: {ts.mean():.3f}")
    print(f"Std: {ts.std():.3f}")
    print(f"Min: {ts.min():.3f}")
    print(f"Max: {ts.max():.3f}")
    
    # Calculate trend
    if len(ts) >= 10:
        # Calculate percent change between first and last value
        pct_change = (ts.iloc[-1] - ts.iloc[0]) / ts.iloc[0] * 100
        print(f"Overall change: {pct_change:.2f}%")
        
        # Try to decompose the time series
        try:
            decomposition = seasonal_decompose(ts, model='additive', period=min(len(ts)//2, 12))
            trend = decomposition.trend.dropna()
            seasonal = decomposition.seasonal.dropna()
            residual = decomposition.resid.dropna()
            
            print(f"Trend component variance: {trend.var():.3f}")
            print(f"Seasonal component variance: {seasonal.var():.3f}")
            print(f"Residual component variance: {residual.var():.3f}")
        except Exception as e:
            print(f"Could not decompose time series: {e}")
```
"""
                return response
                
            else:  # basic analysis
                numeric_analysis = analytics_result['numeric_analysis']
                categorical_analysis = analytics_result['categorical_analysis']
                
                # Format basic analysis results with code
                response = f"""
## Basic Statistical Analysis

**Numeric Variables:**
```
{chr(10).join(f'- {var}:' + chr(10) + chr(10).join(f'  * {metric}: {value:.3f}' for metric, value in metrics.items()) for var, metrics in numeric_analysis.items())}
```

**Categorical Variables:**
```
{chr(10).join(f'- {var}:' + chr(10) + chr(10).join(f'  * {metric}: {value}' for metric, value in metrics.items()) for var, metrics in categorical_analysis.items())}
```

**Python Code to Reproduce:**
```python
import pandas as pd
import numpy as np

# Basic statistics for numeric columns
numeric_cols = df.select_dtypes(include=[np.number]).columns
numeric_stats = df[numeric_cols].describe().T
numeric_stats['skew'] = df[numeric_cols].skew()
numeric_stats['kurtosis'] = df[numeric_cols].kurtosis()

print(numeric_stats)

# Statistics for categorical columns
categorical_cols = df.select_dtypes(include=['object']).columns
for col in categorical_cols:
    print(f"\\n{col}:\\n")
    value_counts = df[col].value_counts()
    print(value_counts)
    print(f"Unique values: {df[col].nunique()}")
```
"""
                return response
                
        except Exception as e:
            self.logger.error(f"Error generating analysis response: {str(e)}")
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
            context = ""  # Define context variable to avoid UnboundLocalError
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
                            
                            # Generate detailed response with actual analysis results and code
                            response = await self._generate_analysis_response(query, analytics_result)
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
                    
                    # Generate response from SQL results with SQL code included
                    return await self._generate_sql_response(query, sql_results, sql_query)
                    
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

    async def _generate_sql_response(self, query: str, sql_results: List[Dict[str, Any]], sql_query: str) -> str:
        """Generate response with actual SQL results including the query used"""
        try:
            if not sql_results:
                return f"""
## SQL Query Result
No data was returned for your query.

**SQL Query Used:**
```sql
{sql_query}
```

You can modify this query to get different results.
"""
            
            # Format the first 10 results as a markdown table
            columns = list(sql_results[0].keys())
            result_table = "| " + " | ".join(columns) + " |\n"
            result_table += "| " + " | ".join(["---"] * len(columns)) + " |\n"
            
            # Add up to 10 rows
            for row in sql_results[:10]:
                result_table += "| " + " | ".join([str(row[col]) for col in columns]) + " |\n"
                
            # Create the response
            response = f"""
## SQL Query Results
**Found {len(sql_results)} records. Showing first {min(10, len(sql_results))}:**

{result_table}

**SQL Query Used:**
```sql
{sql_query}
```

**Python Code to Reproduce:**
```python
import pandas as pd
import psycopg2
from sqlalchemy import create_engine

# Connect to the database
conn_str = "postgresql://glinskiyvadim@localhost:5540/pred_genai"
engine = create_engine(conn_str)

# Execute the query
query = '''
{sql_query}
'''
df = pd.read_sql(query, engine)

# Display the results
print(f"Found {len(df)} records")
display(df.head(10))

# Generate summary statistics
if len(df) > 0:
    print("\\nSummary statistics:")
    numeric_cols = df.select_dtypes(include=['number']).columns
    if len(numeric_cols) > 0:
        print(df[numeric_cols].describe())
```
"""
            return response
                
        except Exception as e:
            self.logger.error(f"Error generating SQL response: {str(e)}")
            raise 