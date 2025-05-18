import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
import os
from typing import Dict, Union, Any, List, Optional
import logging
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.ensemble import IsolationForest
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
import re
from software_auction.fastapi_app.rag.hybrid_rag import HybridRAG
import json
from pathlib import Path
from datetime import datetime

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

logger = logging.getLogger(__name__)

class AnalyticsService:
    def __init__(self):
        self.rag = HybridRAG()        
        self.logger = logging.getLogger(__name__)
        self.engine = create_engine(
            f"postgresql://{os.getenv('DB_USER')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
        )
        # Use the same engine for tile_analytics since it's now in the main database
        self.tile_analytics_engine = self.engine
        
        # Load company info from JSON file
        self.company_info = self._load_company_info()

    def _load_company_info(self) -> Dict[str, str]:
        """Load company information from JSON file"""
        try:
            json_path = Path(__file__).parent.parent / 'data' / 'company_info.json'
            with open(json_path, 'r') as f:
                data = json.load(f)
                # Convert list to dictionary for easier lookup
                return {company['name']: company['company_description'] 
                       for company in data['companies']}
        except Exception as e:
            self.logger.error(f"Error loading company info from JSON: {str(e)}")
            return {}

    def analyze_data(self, query: str) -> Dict:
        """
        Main method to analyze data using either SQL or Python-based analytics
        based on the complexity of the query.
        """
        try:
            # First get the data
            df = self._get_relevant_data(query)
            if df.empty:
                raise ValueError("No data available for analysis")

            # Determine analysis type
            analysis_type = self._determine_analysis_type(query)
            self.logger.info(f"Performing {analysis_type} analysis")

            # Perform the appropriate analysis
            if analysis_type == "regression":
                result = self._perform_regression(df, query)
                self.logger.info(f"Regression analysis completed with R² score: {result['r2_score']:.3f}")
                return result
            elif analysis_type == "correlation":
                result = self._perform_correlation_analysis(df, query)
                self.logger.info("Correlation analysis completed")
                return result
            elif analysis_type == "time_series":
                result = self._perform_time_series_analysis(df, query)
                self.logger.info("Time series analysis completed")
                return result
            else:
                result = self._perform_basic_analysis(df, query)
                self.logger.info("Basic analysis completed")
                return result

        except Exception as e:
            self.logger.error(f"Error in analyze_data: {str(e)}")
            raise

    def _get_relevant_data(self, query: str) -> pd.DataFrame:
        """
        Extract relevant data from the database based on the query.
        """
        try:
            # Get the most recent CSV data table
            with self.engine.connect() as conn:
                # Find the most recent CSV data table
                result = conn.execute(text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_name LIKE 'csv_data_%'
                    ORDER BY table_name DESC
                    LIMIT 1
                """))
                table_info = result.fetchone()
                
                if not table_info:
                    raise ValueError("No CSV data tables found in the database")
                
                table_name = table_info[0]
                
                # Get column information
                result = conn.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = :table_name
                """), {'table_name': table_name})
                
                columns = [row[0] for row in result]
                
                if not columns:
                    raise ValueError(f"No columns found in table {table_name}")
                
                # Create a proper SQL query with explicit column names
                columns_str = ', '.join(f'"{col}"' for col in columns)
                query = f'SELECT {columns_str} FROM "{table_name}"'
                
                # Execute query and convert to DataFrame
                df = pd.read_sql(query, conn)
                
            if df.empty:
                raise ValueError(f"No data found in table {table_name}")
                
            # Convert numeric columns to appropriate types
            for col in df.columns:
                try:
                    df[col] = pd.to_numeric(df[col], errors='ignore')
                except:
                    continue
                
            self.logger.info(f"Retrieved {len(df)} rows from {table_name}")
            return df

        except Exception as e:
            self.logger.error(f"Error getting relevant data: {str(e)}")
            raise

    def _determine_analysis_type(self, query: str) -> str:
        """
        Determine the type of analysis needed based on the query.
        """
        query = query.lower()
        
        # Check for regression-related keywords
        regression_keywords = ["regression", "predict", "forecast", "model", "relationship"]
        if any(keyword in query for keyword in regression_keywords):
            return "regression"
            
        # Check for correlation-related keywords
        correlation_keywords = ["correlation", "related", "relationship", "association"]
        if any(keyword in query for keyword in correlation_keywords):
            return "correlation"
            
        # Check for time series-related keywords
        time_series_keywords = ["time", "trend", "forecast", "seasonal", "temporal"]
        if any(keyword in query for keyword in time_series_keywords):
            return "time_series"
            
        return "basic"

    def _try_sql_analysis(self, query: str) -> Union[Dict, None]:
        """
        Attempt to analyze data using SQL queries.
        Returns None if the query requires Python-based analysis.
        """
        try:
            # Convert natural language to SQL
            sql_query = self._convert_to_sql(query)
            if not sql_query:
                return None

            # Execute SQL query
            with self.engine.connect() as conn:
                result = conn.execute(text(sql_query))
                data = [dict(row) for row in result]

            return {
                "type": "sql",
                "query": sql_query,
                "results": data
            }
        except Exception as e:
            logger.warning(f"SQL analysis failed, falling back to Python: {str(e)}")
            return None

    def _python_analysis(self, query: str) -> Dict:
        """
        Perform Python-based data analysis using pandas and scikit-learn.
        """
        try:
            # Extract relevant data from database
            df = self._get_relevant_data(query)
            
            # Determine analysis type and perform it
            analysis_type = self._determine_analysis_type(query)
            
            if analysis_type == "regression":
                return self._perform_regression(df, query)
            elif analysis_type == "correlation":
                return self._perform_correlation_analysis(df, query)
            elif analysis_type == "time_series":
                return self._perform_time_series_analysis(df, query)
            else:
                return self._perform_basic_analysis(df, query)
        except Exception as e:
            logger.error(f"Error in Python analysis: {str(e)}")
            raise

    def _populate_company_info(self, data: pd.DataFrame) -> bool:
        """
        Update company information in the JSON file based on the dataset
        
        Args:
            data: DataFrame containing company data
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.logger.info(f"Starting to update company info with {len(data)} records")
            
            # Check for required name column
            if 'name' not in data.columns:
                self.logger.error("Missing required column: name")
                return False
            
            # Prepare company descriptions
            companies = []
            for _, row in data.iterrows():
                try:
                    name = row['name']
                    description_parts = [f"{name}"]
                    
                    # Add industry if available
                    if 'industry' in row and pd.notna(row['industry']):
                        description_parts.append(f"is a {row['industry']} company")
                    
                    # Add employee count if available
                    if 'employee_count' in row and pd.notna(row['employee_count']):
                        description_parts.append(f"with {row['employee_count']} employees")
                    
                    # Add location if available
                    if 'location' in row and pd.notna(row['location']):
                        description_parts.append(f"located in {row['location']}")
                    
                    # Add churn rate if available
                    if 'churn_rate' in row and pd.notna(row['churn_rate']):
                        description_parts.append(f"has a churn rate of {row['churn_rate']*100:.1f}%")
                    
                    # Add revenue information
                    revenue_info = []
                    if 'revenue_millions' in row and pd.notna(row['revenue_millions']):
                        revenue_info.append(f"${row['revenue_millions']:.1f}M in revenue")
                    if 'arr' in row and pd.notna(row['arr']):
                        revenue_info.append(f"${row['arr']:,.0f} in ARR")
                    if revenue_info:
                        description_parts.append(f"generates {' and '.join(revenue_info)}")
                    
                    # Add contract value if available
                    if 'avg_contract_value' in row and pd.notna(row['avg_contract_value']):
                        description_parts.append(f"with an average contract value of ${row['avg_contract_value']:,.0f}")
                    
                    # Add additional metrics if available
                    additional_metrics = []
                    if 'customer_satisfaction' in row and pd.notna(row['customer_satisfaction']):
                        additional_metrics.append(f"{row['customer_satisfaction']}% customer satisfaction")
                    if 'growth_rate' in row and pd.notna(row['growth_rate']):
                        additional_metrics.append(f"{row['growth_rate']*100:.1f}% growth rate")
                    if additional_metrics:
                        description_parts.append(f"with {', '.join(additional_metrics)}")
                    
                    # Combine all parts into a description
                    description = ' '.join(description_parts) + '.'
                    
                    companies.append({
                        'name': name,
                        'company_description': description,
                        'metrics': {
                            'industry': row.get('industry'),
                            'employee_count': row.get('employee_count'),
                            'location': row.get('location'),
                            'churn_rate': float(row['churn_rate']) if 'churn_rate' in row and pd.notna(row['churn_rate']) else None,
                            'revenue_millions': float(row['revenue_millions']) if 'revenue_millions' in row and pd.notna(row['revenue_millions']) else None,
                            'arr': float(row['arr']) if 'arr' in row and pd.notna(row['arr']) else None,
                            'avg_contract_value': float(row['avg_contract_value']) if 'avg_contract_value' in row and pd.notna(row['avg_contract_value']) else None,
                            'customer_satisfaction': float(row['customer_satisfaction']) if 'customer_satisfaction' in row and pd.notna(row['customer_satisfaction']) else None,
                            'growth_rate': float(row['growth_rate']) if 'growth_rate' in row and pd.notna(row['growth_rate']) else None
                        }
                    })
                    self.logger.info(f"Prepared data for company: {name}")
                except Exception as row_error:
                    self.logger.error(f"Error processing row for company {row.get('name', 'unknown')}: {str(row_error)}")
                    continue
            
            # Create data directory if it doesn't exist
            json_path = Path(__file__).parent.parent / 'data'
            json_path.mkdir(parents=True, exist_ok=True)
            
            # Write to JSON file
            json_file = json_path / 'company_info.json'
            with open(json_file, 'w') as f:
                json.dump({'companies': companies}, f, indent=4, cls=DateTimeEncoder)
            
            # Update in-memory company info
            self.company_info = {company['name']: company['company_description'] 
                               for company in companies}
            
            self.logger.info(f"Successfully updated company info with {len(companies)} records")
            return True
                
        except Exception as e:
            self.logger.error(f"Error updating company info: {str(e)}")
            return False

    def handle_csv_upload(self, file_path: str) -> Dict[str, Any]:
        """Process a newly uploaded CSV file with analytics
        
        Args:
            file_path: Path to the uploaded CSV file
            
        Returns:
            Dictionary with processing results
        """
        try:
            # Read the CSV file
            df = pd.read_csv(file_path)
            
            if df.empty:
                return {
                    "success": False,
                    "message": "CSV file is empty"
                }
            
            self.logger.info("Found company data, updating company_info.json")
            success = self._populate_company_info(df)
            if not success:
                self.logger.error("Failed to update company_info.json")
                return {
                    "success": False,
                    "message": "Failed to update company information"
                }
            
            # Create tiles based on company metrics
            try:
                # Get company info from JSON
                json_path = Path(__file__).parent.parent / 'data' / 'company_info.json'
                with open(json_path, 'r') as f:
                    company_data = json.load(f)
                
                # Create tiles for each company
                for company in company_data['companies']:
                    metrics = company['metrics']
                    
                    # Create red tile for high churn risk
                    churn_rate = metrics.get('churn_rate')
                    if churn_rate is not None and churn_rate > 0.1:  # 10% churn rate
                        self.write_to_tile_analytics({
                            'name': company['name'],
                            'category': 'churn_risk',
                            'color': 'red',
                            'title': 'High Churn Risk',
                            'description': f'Churn rate is {churn_rate:.1%}. Immediate attention required.',
                            'metrics': {
                                'churn_rate': churn_rate,
                                'customer_satisfaction': metrics.get('customer_satisfaction'),
                                'revenue': metrics.get('revenue_millions')
                            }
                        }, 'churn_risk')
                    
                    # Create green tile for growth opportunity
                    growth_rate = metrics.get('growth_rate')
                    if growth_rate is not None and growth_rate > 0.2:  # 20% growth
                        self.write_to_tile_analytics({
                            'name': company['name'],
                            'category': 'growth_opportunity',
                            'color': 'green',
                            'title': 'Strong Growth',
                            'description': f'Growth rate is {growth_rate:.1%}. Excellent performance.',
                            'metrics': {
                                'growth_rate': growth_rate,
                                'revenue': metrics.get('revenue_millions'),
                                'customer_satisfaction': metrics.get('customer_satisfaction')
                            }
                        }, 'growth_opportunity')
                    
                    # Create yellow tile for low engagement
                    customer_satisfaction = metrics.get('customer_satisfaction')
                    if customer_satisfaction is not None and customer_satisfaction < 50:  # 50% satisfaction
                        self.write_to_tile_analytics({
                            'name': company['name'],
                            'category': 'engagement_risk',
                            'color': 'yellow',
                            'title': 'Low Customer Satisfaction',
                            'description': f'Customer satisfaction is {customer_satisfaction}%. Needs improvement.',
                            'metrics': {
                                'customer_satisfaction': customer_satisfaction,
                                'churn_rate': metrics.get('churn_rate'),
                                'revenue': metrics.get('revenue_millions')
                            }
                        }, 'engagement_risk')
                
                self.logger.info("Successfully created tiles in tile_analytics table")
                
            except Exception as tile_error:
                self.logger.error(f"Error creating tiles: {str(tile_error)}")
                return {
                    "success": False,
                    "message": f"Error creating tiles: {str(tile_error)}"
                }
            
            # Run comprehensive analysis
            results = self.analyze_data("Analyze the uploaded dataset")

            return {
                "success": "error" not in results,
                "message": results.get("error", "Analysis completed successfully"),
                "results": results
            }
            
        except Exception as e:
            logger.error(f"Error processing CSV file: {str(e)}")
            return {
                "success": False,
                "message": f"Error processing CSV file: {str(e)}"
            }

    def _print_tile_analytics_table(self, conn) -> None:
        """Print the current contents of the tile_analytics table in tabular format"""
        try:
            # Query the table and convert to DataFrame
            df = pd.read_sql("""
                SELECT 
                    name,
                    category,
                    color,
                    title,
                    description,
                    metrics,
                    created_at,
                    updated_at
                FROM tile_analytics 
                ORDER BY created_at DESC
            """, conn)
            
            if df.empty:
                self.logger.info("tile_analytics table is empty")
                return
            
            # Format the DataFrame for display
            pd.set_option('display.max_columns', None)
            pd.set_option('display.width', None)
            pd.set_option('display.max_colwidth', 30)
            
            # Convert metrics to string representation
            df['metrics'] = df['metrics'].apply(lambda x: json.dumps(x, cls=DateTimeEncoder) if x else '{}')
            
            # Format timestamps
            df['created_at'] = pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d %H:%M:%S')
            df['updated_at'] = pd.to_datetime(df['updated_at']).dt.strftime('%Y-%m-%d %H:%M:%S')
            
            # Print the table
            self.logger.info("\nCurrent tile_analytics table contents:")
            self.logger.info(df.head(n = 100))
            
        except Exception as e:
            self.logger.error(f"Error printing tile_analytics table: {str(e)}")

    def write_to_tile_analytics(self, analysis_results: Dict[str, Any], analysis_type: str) -> bool:
        """
        Write analytics results to tile_analytics table based on company characteristics
        
        Args:
            analysis_results: Dictionary containing the analysis results for a single company
            analysis_type: Type of analysis performed
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.logger.info("Starting write_to_tile_analytics")
            self.logger.info(f"Input analysis_results: {json.dumps(analysis_results, indent=2, cls=DateTimeEncoder)}")
            self.logger.info(f"Input analysis_type: {analysis_type}")
            
            name = analysis_results.get('name')
            if not name:
                self.logger.error("No company name provided in analysis_results")
                return False
            
            # Insert into tile_analytics
            try:
                with self.engine.connect() as conn:
                    # First check if table exists
                    result = conn.execute(text("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_name = 'tile_analytics'
                        );
                    """))
                    table_exists = result.scalar()
                    
                    if not table_exists:
                        self.logger.info("Creating tile_analytics table")
                        conn.execute(text("""
                            CREATE TABLE tile_analytics (
                                id SERIAL PRIMARY KEY,
                                name VARCHAR(255) NOT NULL,
                                category VARCHAR(50) NOT NULL,
                                color VARCHAR(20) NOT NULL,
                                title VARCHAR(255) NOT NULL,
                                description TEXT,
                                metrics JSONB,
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                            );
                        """))
                        conn.commit()
                        self.logger.info("Successfully created tile_analytics table")
                    
                    # Insert the tile data
                    self.logger.info("Inserting tile data with parameters:")
                    insert_params = {
                        'name': name,
                        'category': analysis_results['category'],
                        'color': analysis_results['color'],
                        'title': analysis_results['title'],
                        'description': analysis_results['description'],
                        'metrics': json.dumps(analysis_results['metrics'], cls=DateTimeEncoder)
                    }
                    self.logger.info(f"Insert parameters: {json.dumps(insert_params, indent=2, cls=DateTimeEncoder)}")
                    
                    conn.execute(text("""
                        INSERT INTO tile_analytics 
                        (name, category, color, title, description, metrics)
                        VALUES (:name, :category, :color, :title, :description, :metrics)
                    """), insert_params)
                    
                    # Verify the insertion
                    result = conn.execute(text("""
                        SELECT * FROM tile_analytics 
                        WHERE name = :name 
                        ORDER BY created_at DESC 
                        LIMIT 1
                    """), {'name': name})
                    
                    inserted_row = result.fetchone()
                    if inserted_row:
                        self.logger.info(f"Successfully inserted tile for {name}")
                        # Convert row to dict properly and handle datetime serialization
                        row_dict = {key: value for key, value in inserted_row._mapping.items()}
                        self.logger.info(f"Inserted row: {json.dumps(row_dict, indent=2, cls=DateTimeEncoder)}")
                        
                        # Print current table contents after insertion
                        self.logger.info("Printing the current table contents after insertion")
                        self._print_tile_analytics_table(conn)
                    else:
                        self.logger.error(f"Failed to verify insertion for {name}")
                    
                    conn.commit()
                    return True
                    
            except Exception as insert_error:
                self.logger.error(f"Error inserting tile for {name}: {str(insert_error)}")
                self.logger.exception("Full traceback:")
                return False
            
        except Exception as e:
            self.logger.error(f"Error in write_to_tile_analytics: {str(e)}")
            self.logger.exception("Full traceback:")
            return False

    def _determine_tile_characteristics(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Determine the most significant characteristic for a company's tile
        """
        try:
            # Convert metrics to float values
            churn_rate = self._convert_to_float(metrics.get('churn_rate'))
            customer_satisfaction = self._convert_to_float(metrics.get('customer_satisfaction'))
            
            # Define thresholds
            HIGH_CHURN_THRESHOLD = 0.1  # 10% churn rate
            LOW_SATISFACTION_THRESHOLD = 0.05  # 5% satisfaction
            
            # Determine the most significant characteristic
            if churn_rate and churn_rate > HIGH_CHURN_THRESHOLD:
                return {
                    'category': 'churn_risk',
                    'color': 'red',
                    'title': 'High Churn Risk',
                    'description': f'Churn rate is {churn_rate:.1%}. Immediate attention required.',
                    'metrics': {
                        'churn_rate': churn_rate,
                        'customer_satisfaction': customer_satisfaction,
                        'revenue': metrics.get('revenue_millions')
                    }
                }
            elif customer_satisfaction and customer_satisfaction < LOW_SATISFACTION_THRESHOLD:
                return {
                            'category': 'satisfaction_risk',
                            'color': 'orange',
                            'title': 'Low Customer Satisfaction',
                            'description': f'Customer satisfaction is {customer_satisfaction:.1%}. Needs improvement.',
                            'metrics': {
                                'customer_satisfaction': customer_satisfaction,
                                'churn_rate': churn_rate,
                                'revenue': metrics.get('revenue_millions')
                            }
                        }
            return None
        except Exception as e:
            self.logger.error(f"Error determining tile characteristics: {str(e)}")
            return None

    def _convert_to_float(self, value: Any) -> Optional[float]:
        """Convert a value to float, handling various formats"""
        if value is None:
            return None
            
        try:
            if isinstance(value, str):
                if '%' in value:
                    return float(value.strip('%')) / 100
                return float(value)
            return float(value)
        except (ValueError, TypeError):
            return None

    def _perform_basic_analysis(self, df: pd.DataFrame, query: str) -> Dict:
        """
        Perform basic statistical analysis on the dataset.
        
        Args:
            df: DataFrame containing the data
            query: The original query string
            
        Returns:
            Dictionary containing basic analysis results
        """
        try:
            results = {
                "summary_statistics": {},
                "column_info": {},
                "data_quality": {}
            }
            
            # Basic summary statistics for numeric columns
            numeric_cols = df.select_dtypes(include=['number']).columns
            if not numeric_cols.empty:
                # Convert numpy/pandas types to Python native types
                stats = df[numeric_cols].describe()
                results["summary_statistics"] = {
                    col: {
                        stat: float(val) if isinstance(val, (np.number, pd.Series)) else val
                        for stat, val in stats[col].items()
                    }
                    for col in numeric_cols
                }
            
            # Column information
            for col in df.columns:
                col_info = {
                    "dtype": str(df[col].dtype),
                    "unique_values": int(df[col].nunique()),
                    "missing_values": int(df[col].isnull().sum())
                }
                
                # Add value counts for categorical columns
                if df[col].dtype == 'object' or df[col].dtype.name == 'category':
                    value_counts = df[col].value_counts().head(5)
                    col_info["value_counts"] = {
                        str(k): int(v) if isinstance(v, (np.number, pd.Series)) else v
                        for k, v in value_counts.items()
                    }
                
                results["column_info"][col] = col_info
            
            # Data quality metrics
            results["data_quality"] = {
                "total_rows": int(len(df)),
                "total_columns": int(len(df.columns)),
                "missing_values_percentage": float((df.isnull().sum().sum() / (len(df) * len(df.columns))) * 100),
                "duplicate_rows": int(df.duplicated().sum())
            }
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error in basic analysis: {str(e)}")
            raise

    def store_analytics_results(self, results: List[Dict[str, Any]]) -> bool:
        """
        Store analytics results in the tile_analytics table in PostgreSQL
        """
        try:
            with self.engine.connect() as conn:
                for result in results:
                    # Insert into tile_analytics table
                    conn.execute(text("""
                        INSERT INTO tile_analytics (
                            name,
                            title,
                            description,
                            color,
                            created_at,
                            updated_at
                        ) VALUES (:name, :title, :description, :color, NOW(), NOW())
                    """), {
                        'name': result['name'],
                        'title': result['title'],
                        'description': result['description'],
                        'color': result['color']
                    })
                conn.commit()
            
            self.logger.info(f"Successfully stored {len(results)} analytics results in tile_analytics table")
            return True
            
        except Exception as e:
            self.logger.error(f"Error storing analytics results: {str(e)}")
            return False 