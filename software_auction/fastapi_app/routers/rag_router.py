from fastapi import APIRouter, Request, HTTPException
from ..rag.rag_service import RAGService
import logging

rag_router = APIRouter()
logger = logging.getLogger(__name__)

@rag_router.post("/text_query")
async def text_query(request: Request):
    """Handle text mode queries"""
    try:
        data = await request.json()
        if not data.get('query'):
            return {
                "status": "error",
                "message": "No query provided"
            }

        try:
            response = RAGService.handle_text_query(data['query'])
            if not response:
                raise ValueError("Empty response from RAG service")
            
            return {
                "status": "success",
                "response": response
            }
        except Exception as e:
            logger.error(f"RAG service error: {str(e)}")
            return {
                "status": "error",
                "message": f"Error processing query: {str(e)}"
            }
    except Exception as e:
        logger.error(f"Error in text_query: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }

@rag_router.post("/add-to-kb")
async def add_to_kb(request: Request):
    """Add content to knowledge base"""
    try:
        data = await request.json()
        
        # Validate required fields
        if not all(key in data for key in ['title', 'content', 'url']):
            return {
                "status": "error",
                "message": "Missing required fields"
            }
        
        # Add to knowledge base using RAG service
        RAGService.add_to_knowledge_base(data)
        
        return {
            "status": "success",
            "message": "Successfully added to knowledge base"
        }
    except Exception as e:
        logger.error(f"Error adding to knowledge base: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }
