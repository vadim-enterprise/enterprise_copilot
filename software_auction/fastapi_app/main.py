import os
import sys
from pathlib import Path
import logging

# Load environment variables
from software_auction.fastapi_app.utils.env_loader import load_env_variables
load_env_variables()

# Setup Django environment
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')

import django
django.setup()

# Now import FastAPI and other dependencies
from fastapi import FastAPI, HTTPException, Request, Response, Form, File, UploadFile, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from fastapi.templating import Jinja2Templates
from .routers import websearch_router
from .routers.speech_router import router as speech_router
from .routers.tile_router import router as tile_router
from .services.websearch_service import WebSearchService
from .services.analytics_service import AnalyticsService
import logging
from typing import Dict, Any, List, Optional
import json
import time
from openai import OpenAI
from .settings import ALLOWED_ORIGINS
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
import tempfile
import shutil
from datetime import datetime
from sqlalchemy import create_engine, text
from django.conf import settings

# Create a router for speech-related endpoints
from fastapi import APIRouter
from .routers.rag_router import rag_router
from .rag.rag_service import RAGService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Analytics FastAPI Application")

# Add CORS middleware with more permissive settings for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8000", "http://localhost:8000"],  # Add your frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Initialize services
rag_service = RAGService()
analytics_service = AnalyticsService()
websearch_service = WebSearchService()

# Initialize OpenAI client
openai_client = OpenAI()

# Get model settings from Django settings
GPT_MODEL = settings.GPT_MODEL_NAME

# Database connection
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://glinskiyvadim@localhost:5540/pred_genai')
engine = create_engine(DATABASE_URL)

# Include routers
app.include_router(websearch_router.router, prefix="/api/websearch", tags=["websearch"])
app.include_router(speech_router, prefix="/api/speech", tags=["speech"])
app.include_router(tile_router, prefix="/api", tags=["tiles"])
app.include_router(rag_router, prefix="/api/rag", tags=["rag"])

# File handling endpoints
def get_db_connection():
    """Get a database connection with proper error handling"""
    try:
        conn = psycopg2.connect(
            host="localhost",
            port=5540,
            database="pred_genai",
            user="glinskiyvadim"
        )
        logger.info("Successfully connected to database")
        return conn
    except Exception as e:
        logger.error(f"Error connecting to database: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database connection error: {str(e)}")

@app.post("/api/files/upload-csv")
async def upload_csv(file: UploadFile = File(...)):
    """
    Upload a CSV file, store it in PostgreSQL, and process it with analytics
    """
    temp_file_path = None
    try:
        logger.info(f"Received file upload: {file.filename}")
        
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as temp_file:
            shutil.copyfileobj(file.file, temp_file)
            temp_file_path = temp_file.name
        
        # Read and process the CSV file
        df = pd.read_csv(temp_file_path)
        logger.info(f"Successfully read CSV with {len(df)} rows and columns: {df.columns.tolist()}")
        
        # Generate table name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        table_name = f"csv_data_{os.path.splitext(file.filename)[0]}_{timestamp}".lower().replace('-', '_').replace(' ', '_')
        logger.info(f"Generated table name: {table_name}")
        
        # Store in PostgreSQL and process with analytics
        df.to_sql(table_name, engine, if_exists='replace', index=False)
        logger.info(f"Successfully created table {table_name} in PostgreSQL")
        
        result = analytics_service.handle_csv_upload(temp_file_path)
        logger.info(f"Analytics processing complete: {result.get('success', False)}")
        
        return JSONResponse(
            status_code=200,
            content={
                "message": "File uploaded and processed successfully",
                "table_name": table_name,
                "row_count": len(df),
                "columns": df.columns.tolist(),
                "analytics_result": result,
                "should_refresh": True
            }
        )
        
    except Exception as e:
        logger.error(f"Error processing CSV file: {str(e)}")
        logger.exception("Full traceback:")
        raise HTTPException(status_code=500, detail=str(e))
        
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            logger.info(f"Removed temporary file: {temp_file_path}")

@app.get("/api/files/list-csv-files")
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

@app.get("/api/files/get-csv-data/{table_name}")
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

@app.post("/api/files/query-dataset")
async def query_dataset(
    table_name: str,
    question: str,
    model: str = Query(default=GPT_MODEL, description="The OpenAI model to use for answering questions")
):
    try:
        # First verify the table exists in metadata
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT column_names FROM csv_metadata WHERE table_name = :table_name
            """), {'table_name': table_name})
            metadata = result.fetchone()
            if not metadata:
                raise HTTPException(status_code=404, detail="Table not found")
            
            # Get the data
            result = conn.execute(text(f"""
                SELECT * FROM {table_name} LIMIT 1000
            """))
            data = [dict(row) for row in result]
            
            # Convert to DataFrame for analysis
            df = pd.DataFrame(data)
            
            # Use the analytics service to analyze the data
            # First try SQL analysis
            sql_result = analytics_service._try_sql_analysis(question)
            if sql_result:
                return JSONResponse(
                    status_code=200,
                    content={
                        "message": "Analysis completed successfully",
                        "results": sql_result
                    }
                )
            
            # If SQL analysis fails, use Python analysis
            python_result = analytics_service._python_analysis(question)
            return JSONResponse(
                status_code=200,
                content={
                    "message": "Analysis completed successfully",
                    "results": python_result
                }
            )
            
    except Exception as e:
        logger.error(f"Error querying dataset: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# RAG endpoints
@rag_router.post("/enrich")
async def enrich_knowledge_base(request: Request):
    """Handle knowledge base enrichment request"""
    try:
        data = await request.json()
        logger.info(f"Would have enriched knowledge base with: {data}")
        return {
            "status": "success",
            "message": "Knowledge base enrichment functionality removed"
        }
    except Exception as e:
        logger.error(f"Error in enrich_knowledge_base: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }

@rag_router.get("/text_instructions")
async def get_text_instructions():
    """Get instructions from text.txt"""
    try:
        text_path = Path(__file__).resolve().parent.parent / 'knowledge_base' / 'data' / 'text.txt'
        logger.info(f"Looking for text.txt at: {text_path}")
        
        if text_path.exists():
            logger.info("text.txt file found, attempting to read...")
            with open(text_path, 'r', encoding='utf-8') as f:
                instructions = f.read().strip()
            
            logger.info(f"Extracted text length: {len(instructions)}")
            
            if not instructions:
                logger.error("text.txt file is empty")
                raise HTTPException(status_code=500, detail="text.txt file is empty")

            logger.info("Successfully loaded text.txt instructions")
            return {
                "status": "success",
                "instructions": instructions
            }
        logger.error(f"text.txt file not found at {text_path}")
        return {
            "status": "error",
            "message": "text.txt not found"
        }
    except Exception as e:
        logger.error(f"Error loading text.txt: {str(e)}")
        logger.exception("Full traceback:")
        raise HTTPException(status_code=500, detail=str(e))

# Mount static files
media_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "media")
os.makedirs(media_dir, exist_ok=True)
logger.info(f"Media directory: {media_dir}")

app.mount("/media", StaticFiles(directory=media_dir), name="media")

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"]
)

@app.options("/{full_path:path}")
async def preflight_handler(request: Request, full_path: str):
    """Handle CORS preflight requests for all routes"""
    requested_headers = request.headers.get("access-control-request-headers", "")
    origin = request.headers.get("origin")
    
    if origin in ALLOWED_ORIGINS:
        return Response(
            status_code=200,
            headers={
                "Access-Control-Allow-Origin": origin,
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": requested_headers or "*",
                "Access-Control-Allow-Credentials": "true",
                "Access-Control-Max-Age": "3600"
            }
        )
    return Response(status_code=400)

# Custom middleware to handle CORS
@app.middleware("http")
async def cors_middleware(request: Request, call_next):
    try:
        response = await call_next(request)
        
        # Get origin from request headers
        origin = request.headers.get("origin")
        
        # If origin is in allowed list, add CORS headers
        if origin in ALLOWED_ORIGINS:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            # Get requested headers from preflight request
            requested_headers = request.headers.get("access-control-request-headers", "*")
            response.headers["Access-Control-Allow-Headers"] = requested_headers
        
        return response
    except Exception as e:
        # Create a new response for errors
        response = JSONResponse(
            status_code=500,
            content={"detail": str(e)}
        )
        
        # Add CORS headers to error response
        if origin in ALLOWED_ORIGINS:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "*"
        
        return response

@speech_router.get("/session")
async def create_session(config: str = None):
    """Create a session with OpenAI's realtime API"""
    try:
        logger.info("Creating realtime session with OpenAI")
        logger.info(f"Received config: {config}")
        
        headers = {
            "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
            "Content-Type": "application/json"
        }
        
        # Parse the config if provided
        try:
            session_config = json.loads(config) if config else {}
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse config JSON: {e}")
            session_config = {}
        
        # Log the API key (first few characters)
        api_key = os.getenv('OPENAI_API_KEY')
        logger.info(f"Using API key: {api_key[:8]}...")
        
        # Prepare request payload
        request_payload = {
            "model": "gpt-4o-realtime-preview-2024-12-17",
            "voice": "verse",
        }
        
        # Only merge config if it's a valid dictionary
        if isinstance(session_config, dict):
            request_payload.update(session_config)
        
        logger.info(f"Sending request payload: {request_payload}")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.openai.com/v1/realtime/sessions",
                headers=headers,
                json=request_payload
            ) as response:
                logger.info(f"OpenAI response status: {response.status}")
                response_text = await response.text()
                logger.info(f"OpenAI raw response: {response_text}")

                try:
                    data = json.loads(response_text)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON response: {e}")
                    raise HTTPException(status_code=500, detail="Invalid response from OpenAI")

                logger.info(f"OpenAI response data: {data}")
                
                if response.status != 200:
                    raise HTTPException(
                        status_code=response.status,
                        detail=f"OpenAI API error: {data.get('error', {}).get('message', 'Unknown error')}"
                    )
                
                # Extract token and expiry from response
                token = data.get("token") or data.get("client_secret", {}).get("value")
                expires_at = data.get("expires_at") or data.get("client_secret", {}).get("expires_at")

                if not token:
                    logger.error("No token found in response")
                    raise HTTPException(status_code=500, detail="No token in OpenAI response")

                return {
                    "status": "success",
                    "client_secret": {
                        "value": token,
                        "expires_at": expires_at
                    }
                }
    except Exception as e:
        logger.error(f"Error creating session: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event("startup")
async def startup_event():
    logger.info("Starting FastAPI server...")
    logger.info("Chat, Speech, RAG, and File upload endpoints are available")

@app.get("/")
async def root():
    return FileResponse(os.path.join(static_dir, "html", "index.html"))

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "services": {
            "chat": "available",
            "speech": "available",
            "files": "available"
        }
    }

@app.post("/api/rag/audio_query")
async def audio_query(request: Request):
    """Handle audio mode queries"""
    try:
        form = await request.form()
        audio_file = form.get('audio')
        
        if not audio_file:
            raise HTTPException(status_code=400, detail="No audio file provided")
        
        # Process audio file here
        # For now, return a placeholder response
        return {
            "status": "success",
            "response": "Audio processing not yet implemented"
        }
    except Exception as e:
        logger.error(f"Error in audio_query: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "detail": str(e)
            }
        )

@app.get("/api/tiles")
async def get_tiles():
    """Fetch tiles from tile_analytics table"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get the data from tile_analytics table
        cur.execute("""
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
        """)
        tiles = cur.fetchall()
        
        cur.close()
        conn.close()
        
        logger.info(f"Successfully fetched {len(tiles)} tiles from tile_analytics table")
        return {"tiles": [dict(tile) for tile in tiles]}
    except Exception as e:
        logger.error(f"Error fetching tiles: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))