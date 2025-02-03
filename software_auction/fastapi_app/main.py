from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from .routers import websearch_router
import logging
import os
import aiohttp
from typing import Dict, Any
import json

# Create a router for speech-related endpoints
from fastapi import APIRouter
speech_router = APIRouter()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Ensure media directory exists
MEDIA_DIR = Path(__file__).resolve().parent.parent.parent / 'media'
MEDIA_DIR.mkdir(parents=True, exist_ok=True)
logger.info(f"Media directory: {MEDIA_DIR}")

# Mount static files
app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=[
        "Content-Type",
        "Authorization",
        "Accept",
        "Origin",
        "X-Requested-With",
    ],
    expose_headers=["*"],
    max_age=3600,
)

# Add CORS headers to all responses
@app.middleware("http")
async def add_cors_headers(request: Request, call_next):
    response = await call_next(request)
    origin = request.headers.get("origin")
    if origin in ["http://localhost:8000", "http://127.0.0.1:8000"]:
        response.headers["Access-Control-Allow-Origin"] = origin
    return response

# Include routers
app.include_router(websearch_router.router, prefix="/api/websearch")

@speech_router.get("/session")
async def create_session(config: str = None):
    """Create a session with OpenAI's realtime API"""
    try:
        logger.info("Creating realtime session with OpenAI")
        headers = {
            "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
            "Content-Type": "application/json"
        }
        
        # Parse the config if provided
        session_config = json.loads(config) if config else {}
        
        # Log the API key (first few characters)
        api_key = os.getenv('OPENAI_API_KEY')
        logger.info(f"Using API key: {api_key[:8]}...")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.openai.com/v1/realtime/sessions",
                headers=headers,
                json={
                    "model": "gpt-4o-realtime-preview-2024-12-17",
                    "voice": "verse",
                    **session_config  # Merge the provided config
                }
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

# Include the speech router
app.include_router(speech_router, prefix="/api")

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