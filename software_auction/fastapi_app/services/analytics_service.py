import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from sqlalchemy import create_engine, text
import os
from typing import Dict, List, Union, Tuple
import logging

logger = logging.getLogger(__name__)

class AnalyticsService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.engine = create_engine(
            f"postgresql://{os.getenv('DB_USER')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
        )

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
            # First get table information
            with self.engine.connect() as conn:
                tables_query = text("""
                    SELECT table_name, column_names 
                    FROM csv_metadata 
                    ORDER BY upload_date DESC
                """)
                result = conn.execute(tables_query)
                tables = []
                for row in result:
                    # Convert row to dictionary properly
                    table_info = {
                        'table_name': row[0],
                        'column_names': row[1]
                    }
                    tables.append(table_info)

            if not tables:
                raise ValueError("No tables found in the database")

            # Get the most recent table
            latest_table = tables[0]
            table_name = latest_table['table_name']
            
            # Fetch all data from the table
            with self.engine.connect() as conn:
                # Convert column_names from string to list if it's stored as a string
                if isinstance(latest_table['column_names'], str):
                    column_names = latest_table['column_names'].strip('{}').split(',')
                else:
                    column_names = latest_table['column_names']
                
                # Create a proper SQL query with explicit column names
                columns_str = ', '.join(f'"{col}"' for col in column_names)
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

    def _perform_regression(self, df: pd.DataFrame, query: str) -> Dict:
        """
        Perform regression analysis.
        """
        try:
            # Get numeric columns
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            
            if len(numeric_cols) < 2:
                raise ValueError("Not enough numeric columns for regression analysis")

            # Determine target and feature columns based on query
            query_lower = query.lower()
            
            # Try to identify target variable from query
            target_col = None
            for col in numeric_cols:
                if col.lower() in query_lower:
                    target_col = col
                    break
            
            # If no target found in query, use the last numeric column
            if not target_col:
                target_col = numeric_cols[-1]
            
            # Use remaining numeric columns as features
            feature_cols = [col for col in numeric_cols if col != target_col]
            
            if not feature_cols:
                raise ValueError("No feature columns available for regression")

            # Prepare data
            X = df[feature_cols]
            y = df[target_col]

            # Handle missing values
            X = X.fillna(X.mean())
            y = y.fillna(y.mean())

            # Scale features
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)

            # Fit regression model
            model = LinearRegression()
            model.fit(X_scaled, y)

            # Calculate predictions
            y_pred = model.predict(X_scaled)

            # Calculate metrics
            r2_score = model.score(X_scaled, y)
            
            # Create coefficients dictionary properly
            coefficients = {}
            for feature, coef in zip(feature_cols, model.coef_):
                coefficients[feature] = float(coef)

            # Calculate additional metrics
            mse = np.mean((y - y_pred) ** 2)
            rmse = np.sqrt(mse)
            mae = np.mean(np.abs(y - y_pred))

            # Calculate feature importance
            feature_importance = {}
            for feature, coef in zip(feature_cols, np.abs(model.coef_)):
                feature_importance[feature] = float(coef)
            
            # Sort feature importance
            sorted_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)
            feature_importance = dict(sorted_features)

            return {
                "type": "regression",
                "target": target_col,
                "features": feature_cols,
                "r2_score": float(r2_score),
                "coefficients": coefficients,
                "predictions": y_pred.tolist(),
                "metrics": {
                    "mse": float(mse),
                    "rmse": float(rmse),
                    "mae": float(mae)
                },
                "feature_importance": feature_importance,
                "actual_values": y.tolist(),
                "residuals": (y - y_pred).tolist()
            }
        except Exception as e:
            self.logger.error(f"Error in regression analysis: {str(e)}")
            raise

    def _perform_correlation_analysis(self, df: pd.DataFrame, query: str) -> Dict:
        """
        Perform correlation analysis between variables.
        """
        # Get numeric columns
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        
        # Calculate correlation matrix
        corr_matrix = df[numeric_cols].corr()
        
        # Find strong correlations
        strong_correlations = []
        for i in range(len(numeric_cols)):
            for j in range(i+1, len(numeric_cols)):
                corr = corr_matrix.iloc[i, j]
                if abs(corr) > 0.5:  # Threshold for strong correlation
                    strong_correlations.append({
                        "variable1": numeric_cols[i],
                        "variable2": numeric_cols[j],
                        "correlation": corr
                    })

        return {
            "type": "correlation",
            "correlation_matrix": corr_matrix.to_dict(),
            "strong_correlations": strong_correlations
        }

    def _perform_time_series_analysis(self, df: pd.DataFrame, query: str) -> Dict:
        """
        Perform time series analysis.
        """
        # Identify time column
        time_col = self._identify_time_column(df)
        if not time_col:
            raise ValueError("No time column found for time series analysis")

        # Convert to datetime if needed
        df[time_col] = pd.to_datetime(df[time_col])

        # Sort by time
        df = df.sort_values(time_col)

        # Calculate basic time series metrics
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        time_series_metrics = {}

        for col in numeric_cols:
            time_series_metrics[col] = {
                "mean": df[col].mean(),
                "std": df[col].std(),
                "trend": self._calculate_trend(df[col]),
                "seasonality": self._detect_seasonality(df[col])
            }

        return {
            "type": "time_series",
            "time_column": time_col,
            "metrics": time_series_metrics
        }

    def _perform_basic_analysis(self, df: pd.DataFrame, query: str) -> Dict:
        """
        Perform basic statistical analysis.
        """
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        categorical_cols = df.select_dtypes(include=['object']).columns

        analysis = {
            "type": "basic",
            "numeric_analysis": {},
            "categorical_analysis": {}
        }

        # Analyze numeric columns
        for col in numeric_cols:
            analysis["numeric_analysis"][col] = {
                "mean": df[col].mean(),
                "median": df[col].median(),
                "std": df[col].std(),
                "min": df[col].min(),
                "max": df[col].max()
            }

        # Analyze categorical columns
        for col in categorical_cols:
            analysis["categorical_analysis"][col] = {
                "unique_values": df[col].nunique(),
                "most_common": df[col].value_counts().head().to_dict()
            }

        return analysis

    def _determine_regression_columns(self, df: pd.DataFrame, query: str) -> Tuple[str, List[str]]:
        """
        Determine target and feature columns for regression analysis.
        """
        # This is a simplified version - in practice, you'd want to use NLP
        # to better understand which columns to use
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        
        if len(numeric_cols) < 2:
            raise ValueError("Not enough numeric columns for regression")

        # Use the last column as target, others as features
        return numeric_cols[-1], numeric_cols[:-1]

    def _identify_time_column(self, df: pd.DataFrame) -> str:
        """
        Identify the time column in the dataframe.
        """
        time_related_keywords = ['date', 'time', 'timestamp', 'year', 'month', 'day']
        
        for col in df.columns:
            if any(keyword in col.lower() for keyword in time_related_keywords):
                return col
        
        return None

    def _calculate_trend(self, series: pd.Series) -> float:
        """
        Calculate the trend of a time series.
        """
        x = np.arange(len(series))
        slope, _ = np.polyfit(x, series, 1)
        return slope

    def _detect_seasonality(self, series: pd.Series) -> bool:
        """
        Detect if a time series has seasonality.
        """
        # Simple seasonality detection using autocorrelation
        autocorr = pd.Series(series).autocorr()
        return abs(autocorr) > 0.5

    def _determine_relevant_tables(self, query: str, tables: List[Dict]) -> List[Dict]:
        """
        Determine which tables are relevant for the analysis.
        """
        # This is a simplified version - in practice, you'd want to use NLP
        # to better understand which tables to use
        return tables[:1]  # For now, just use the most recent table 