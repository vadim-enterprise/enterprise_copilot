import os
import sys
from pathlib import Path

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
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from fastapi.templating import Jinja2Templates
from .routers import websearch_router
from .routers.speech_router import router as speech_router
from .services.websearch_service import WebSearchService
import logging
from typing import Dict, Any
import json
import time
from openai import OpenAI
from .api import chat, files
from .settings import ALLOWED_ORIGINS, HOST, PORT

# Create a router for speech-related endpoints
from fastapi import APIRouter
rag_router = APIRouter()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

app = FastAPI()

# Initialize OpenAI client
openai_client = OpenAI()

# Include routers
app.include_router(websearch_router.router, prefix="/api/websearch", tags=["websearch"])
app.include_router(speech_router, prefix="/api/speech", tags=["speech"])
app.include_router(rag_router, prefix="/api/rag", tags=["rag"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(files.router, prefix="/api/files", tags=["files"])

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

@rag_router.options("/text_query")
async def text_query_options():
    """Handle OPTIONS request for CORS preflight"""
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "http://127.0.0.1:8000",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Credentials": "true"
        },
    )

@rag_router.post("/text_query")
async def text_query(request: Request):
    """Handle text mode queries"""
    try:
        data = await request.json()
        logger.info(f"Received text query: {data}")
        
        # Ensure query is a string
        if not isinstance(data.get('query'), str):
            raise HTTPException(status_code=400, detail="Query must be a string")
        
        # Use OpenAI directly
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": data['query']}],
            temperature=0.7,
            max_tokens=500
        )
        
        if not response or not response.choices:
            raise HTTPException(status_code=500, detail="No response from OpenAI")
        
        response_content = {
            "status": "success",
            "response": response.choices[0].message.content
        }

        return JSONResponse(
            content=response_content,
            headers={
                "Access-Control-Allow-Origin": request.headers.get("origin"),
                "Access-Control-Allow-Credentials": "true"
            }
        )
    except Exception as e:
        logger.error(f"Error in text_query: {str(e)}")
        logger.exception("Full traceback:")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "detail": str(e)
            },
            headers={
                "Access-Control-Allow-Origin": request.headers.get("origin"),
                "Access-Control-Allow-Credentials": "true"
            }
        )

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
    """Root endpoint for testing"""
    return {"message": "FastAPI server is running"}

@app.get("/api/health-check")
async def health_check():
    return {
        "status": "ok",
        "services": {
            "chat": "available",
            "speech": "available",
            "files": "available"
        }
    }

# User speaks → chatbot.js → speech_manager.js → 
# FastAPI main.py → speech_router.py → 
# Process → Response → 
# main.py → speech_manager.js → chatbot.js → User hears response

# graph TD
#     A[User Speaks] --> B[chatbot.js]
#     B --> C[speech_manager.js]
#     C -- "POST /api/speech/transcribe-speech/" --> D[speech_router.py]
#     D -- Whisper API --> E[OpenAI]
#     E -- Transcript --> D
#     D -- JSON Response --> C
#     C --> B[Display Text]

# Mount static files
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Templates
templates = Jinja2Templates(directory=os.path.join(static_dir, "html"))

@app.get("/")
async def root():
    return FileResponse(os.path.join(static_dir, "html", "index.html"))

@app.get("/api/health-check")
async def health_check():
    return {
        "status": "ok",
        "services": {
            "chat": "available",
            "speech": "available",
            "files": "available"
        }
    }

@app.on_event("startup")
async def startup_event():
    logger.info("Starting FastAPI server...")
    logger.info("Chat, Speech, RAG, and File upload endpoints are available")