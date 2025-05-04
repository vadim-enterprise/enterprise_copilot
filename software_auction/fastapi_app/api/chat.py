from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from ..services.chat_service import ChatService
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

router = APIRouter()

class ChatQuery(BaseModel):
    query: str

class ChatResponse(BaseModel):
    response: str

@router.post("/query", response_model=ChatResponse)
async def chat_query(request: Request, query: ChatQuery):
    try:
        logger.info(f"Received chat query: {query.query[:100]}...")
        
        # Initialize chat service
        chat_service = ChatService()
        
        # Get response (this will handle both chat and web search internally)
        response = await chat_service.get_response(query.query)
        logger.info(f"Got response: {response[:100]}...")
        
        return ChatResponse(response=response)
        
    except Exception as e:
        logger.error(f"Error processing chat query: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 