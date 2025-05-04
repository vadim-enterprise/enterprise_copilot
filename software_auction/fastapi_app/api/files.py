from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from typing import List, Optional
import pandas as pd
import logging
import os
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
from openai import OpenAI
import json
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

router = APIRouter()

# Database connection
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://glinskiyvadim@localhost:5540/pred_genai')
engine = create_engine(DATABASE_URL)

@router.post("/upload-csv")
async def upload_csv(file: UploadFile = File(...)):
    try:
        logger.info(f"Received file upload: {file.filename}")
        
        # Read the CSV file
        content = await file.read()
        logger.info(f"File content size: {len(content)} bytes")
        
        # Reset file pointer
        file.file.seek(0)
        df = pd.read_csv(file.file)
        logger.info(f"Successfully read CSV with {len(df)} rows and columns: {df.columns.tolist()}")
        
        # Generate a unique table name based on the file name and timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        table_name = f"csv_data_{os.path.splitext(file.filename)[0]}_{timestamp}"
        table_name = table_name.lower().replace('-', '_').replace(' ', '_')
        logger.info(f"Generated table name: {table_name}")
        
        # Store the data in PostgreSQL
        try:
            df.to_sql(table_name, engine, if_exists='replace', index=False)
            logger.info(f"Successfully created table {table_name} in PostgreSQL")
        except Exception as e:
            logger.error(f"Error creating table in PostgreSQL: {str(e)}")
            raise
        
        # Create a metadata entry for the uploaded file
        try:
            with engine.connect() as conn:
                # Check if csv_metadata table exists
                result = conn.execute(text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'csv_metadata'
                    );
                """))
                if not result.scalar():
                    logger.info("Creating csv_metadata table")
                    conn.execute(text("""
                        CREATE TABLE csv_metadata (
                            id SERIAL PRIMARY KEY,
                            table_name VARCHAR(255) NOT NULL,
                            original_filename VARCHAR(255) NOT NULL,
                            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            column_names TEXT[] NOT NULL,
                            row_count INTEGER NOT NULL
                        )
                    """))
                
                conn.execute(text("""
                    INSERT INTO csv_metadata (table_name, original_filename, column_names, row_count)
                    VALUES (:table_name, :filename, :columns, :row_count)
                """), {
                    'table_name': table_name,
                    'filename': file.filename,
                    'columns': df.columns.tolist(),
                    'row_count': len(df)
                })
                conn.commit()
                logger.info("Successfully inserted metadata")
        except Exception as e:
            logger.error(f"Error handling metadata: {str(e)}")
            raise
        
        return JSONResponse(
            status_code=200,
            content={
                "message": "File uploaded successfully",
                "table_name": table_name,
                "row_count": len(df),
                "columns": df.columns.tolist()
            }
        )
        
    except Exception as e:
        logger.error(f"Error processing CSV file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/list-csv-files")
async def list_csv_files():
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT id, table_name, original_filename, upload_date, column_names, row_count
                FROM csv_metadata
                ORDER BY upload_date DESC
            """))
            files = [dict(row) for row in result]
            return {"files": files}
    except Exception as e:
        logger.error(f"Error listing CSV files: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/get-csv-data/{table_name}")
async def get_csv_data(table_name: str, limit: int = 100):
    try:
        with engine.connect() as conn:
            # Verify the table exists in metadata
            result = conn.execute(text("""
                SELECT 1 FROM csv_metadata WHERE table_name = :table_name
            """), {'table_name': table_name})
            if not result.fetchone():
                raise HTTPException(status_code=404, detail="Table not found")
            
            # Get the data
            result = conn.execute(text(f"""
                SELECT * FROM {table_name} LIMIT {limit}
            """))
            data = [dict(row) for row in result]
            return {"data": data}
    except Exception as e:
        logger.error(f"Error retrieving CSV data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/query-dataset")
async def query_dataset(
    table_name: str,
    question: str,
    model: str = Query(default="gpt-4", description="The OpenAI model to use for answering questions")
):
    try:
        # Get the data from the specified table
        with engine.connect() as conn:
            # First verify the table exists in metadata
            result = conn.execute(text("""
                SELECT column_names FROM csv_metadata WHERE table_name = :table_name
            """), {'table_name': table_name})
            metadata = result.fetchone()
            if not metadata:
                raise HTTPException(status_code=404, detail="Table not found")
            
            # Get a sample of the data
            result = conn.execute(text(f"""
                SELECT * FROM {table_name} LIMIT 100
            """))
            data = [dict(row) for row in result]
            
            # Get column descriptions
            columns = metadata[0]
            
            # Prepare the context for the AI
            context = {
                "columns": columns,
                "sample_data": data[:5],  # Send first 5 rows as sample
                "total_rows": len(data)
            }
            
            # Initialize OpenAI client
            client = OpenAI()
            
            # Create a prompt for the AI
            prompt = f"""
            You are a data analyst assistant. You have access to a dataset with the following columns: {', '.join(columns)}.
            
            Here is a sample of the data:
            {json.dumps(context['sample_data'], indent=2)}
            
            The dataset contains {context['total_rows']} rows.
            
            Please answer the following question about the dataset:
            {question}
            
            If the question requires specific data analysis, please provide:
            1. The analysis methodology
            2. The results
            3. Any relevant insights or patterns you notice
            
            If the question cannot be answered with the available data, please explain why.
            """
            
            # Get the AI response
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a helpful data analyst assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            
            return {
                "answer": response.choices[0].message.content,
                "context": {
                    "table_name": table_name,
                    "columns": columns,
                    "sample_size": len(data)
                }
            }
            
    except Exception as e:
        logger.error(f"Error querying dataset: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/search")
async def search(request: Request):
    try:
        data = await request.json()
        query = data.get('query', '')
        
        if not query:
            raise HTTPException(status_code=400, detail="No search query provided")
        
        # Get all available datasets
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name, column_names, row_count 
                FROM csv_metadata 
                ORDER BY upload_date DESC
            """))
            datasets = [dict(row) for row in result]
            
            # Prepare full dataset access
            all_data = []
            for dataset in datasets:
                # Get the entire dataset
                result = conn.execute(text(f"""
                    SELECT * FROM {dataset['table_name']}
                """))
                full_data = [dict(row) for row in result]
                
                all_data.append({
                    "table_name": dataset['table_name'],
                    "columns": dataset['column_names'],
                    "data": full_data,
                    "total_rows": dataset['row_count']
                })
        
        # Initialize OpenAI client
        client = OpenAI()
        
        # Create a flexible prompt that gives the AI freedom to analyze
        prompt = f"""
        You have direct access to the following datasets:
        {json.dumps(all_data, indent=2)}
        
        User query: {query}
        
        You have complete freedom to:
        1. Analyze any aspect of the data
        2. Perform any calculations or comparisons
        3. Identify patterns, trends, or correlations
        4. Draw conclusions and insights
        5. Combine information from multiple datasets
        6. Use web search results to supplement your analysis
        
        Please provide a comprehensive answer that:
        - Directly addresses the user's query
        - Uses the available data to support your analysis
        - Includes specific examples and numbers from the datasets
        - Explains your reasoning and methodology
        - Highlights any interesting findings
        """
        
        # Get the AI response
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an advanced data analyst with full access to multiple datasets. You can freely analyze and interpret the data to answer questions."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        
        # Perform web search in parallel
        searcher = WebSearchService()
        web_results = searcher.search_and_process(query)
        
        return {
            "type": "combined",
            "answer": response.choices[0].message.content,
            "web_results": web_results,
            "context": {
                "datasets_used": [d["table_name"] for d in all_data],
                "total_datasets": len(all_data)
            }
        }
            
    except Exception as e:
        logger.error(f"Error in search: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 