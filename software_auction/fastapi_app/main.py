from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from PyPDF2 import PdfReader
from .routers import websearch_router
from .services.websearch_service import WebSearchService
from .rag.hybrid_rag import HybridRAG
from .rag.rag_service import RAGService
import logging
import os
import aiohttp
from typing import Dict, Any
import json
import time

# Create a router for speech-related endpoints
from fastapi import APIRouter
speech_router = APIRouter()
rag_router = APIRouter()

# RAG endpoints
@rag_router.post("/enrich")
async def enrich_knowledge_base(request: Request):
    """Handle knowledge base enrichment request"""
    data = await request.json()
    result = RAGService.handle_enrich_knowledge_base(data)
    return result

@rag_router.post("/text_query")
async def text_query(request: Request):
    """Handle text mode queries"""
    data = await request.json()
    return RAGService.handle_text_query(data)

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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
hybrid_rag = HybridRAG()

# Ensure media directory exists
MEDIA_DIR = Path(__file__).resolve().parent.parent.parent / 'media'
MEDIA_DIR.mkdir(parents=True, exist_ok=True)
logger.info(f"Media directory: {MEDIA_DIR}")

# Mount static files
app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:8001",
        "http://127.0.0.1:8001"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=[
        "Content-Type",
        "Authorization",
        "Accept",
        "Origin",
        "X-Requested-With",
    ],
    allow_origin_regex=None,
    expose_headers=["*"],
    max_age=3600,
)

# Add CORS headers to all responses
@app.middleware("http")
async def add_cors_headers(request: Request, call_next):
    response = await call_next(request)
    origin = request.headers.get("origin")
    if origin in ["http://localhost:8000", "http://127.0.0.1:8000", "http://localhost:8001", "http://127.0.0.1:8001"]:
        response.headers["Access-Control-Allow-Origin"] = origin
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

@rag_router.post("/query")
async def query_rag(request: Request):
    """Query the RAG system"""
    try:
        data = await request.json()
        query = data.get("query")
        if not query:
            raise HTTPException(status_code=400, detail="Query is required")
            
        context = hybrid_rag.get_factual_context(query)
        response = hybrid_rag.generate_response(query, context=context)
        
        return {
            "status": "success",
            "response": response,
            "context_used": context,
            "sources": [s.get('source') for s in hybrid_rag.last_query_metadata.get('metadata', [])]
        }
    except Exception as e:
        logger.error(f"Error querying RAG: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@rag_router.post("/voice_query")
async def voice_query_rag(request: Request):
    """Enhanced RAG query for voice interactions"""
    try:
        data = await request.json()
        query = data.get("query")
        is_user_input = data.get("is_user_input", True)
        conversation_history = data.get("conversation_history", [])
        
        if not query:
            raise HTTPException(status_code=400, detail="Query is required")
        
        # Get context from knowledge base
        context = await hybrid_rag.get_context(query)
        
        # If this is user input, potentially add to knowledge base
        if is_user_input:
            # Extract potential new knowledge
            new_knowledge = await hybrid_rag.extract_knowledge(
                query, 
                conversation_history
            )
            
            if new_knowledge:
                # Add to knowledge base if it's new information
                await hybrid_rag.add_to_knowledge_base({
                    "content": new_knowledge,
                    "metadata": {
                        "source": "voice_interaction",
                        "timestamp": time.time(),
                        "type": "learned"
                    }
                })
        
        return {
            "status": "success",
            "context": context,
            "knowledge_added": bool(new_knowledge) if is_user_input else False
        }
        
    except Exception as e:
        logger.error(f"Error in voice RAG query: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event("startup")
async def startup_event():
    logger.info("FastAPI server starting up...")
    logger.info(f"Media directory: {MEDIA_DIR}")
    logger.info("Server configuration complete")

@app.get("/")
async def root():
    """Root endpoint for testing"""
    return {"message": "FastAPI server is running"}

@app.get("/api/health-check")
async def health_check():
    """Root endpoint for health checking"""
    return {
        "status": "ok",
        "message": "FastAPI server is running",
        "services": {
            "search": "available",
        }
    }

# Include routers - moved after endpoint definitions
app.include_router(websearch_router.router, prefix="/api/websearch", tags=["websearch"])
app.include_router(speech_router, prefix="/api/speech", tags=["speech"])
app.include_router(rag_router, prefix="/api/rag", tags=["rag"])