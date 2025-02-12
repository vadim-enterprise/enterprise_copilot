from fastapi import APIRouter, HTTPException, Request
from ..services.websearch_service import WebSearchService, ModelChoice
from ..services import settings
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/health")
async def health_check():
    """Health check endpoint for websearch service"""
    try:
        return {
            "status": "ok",
            "service": "websearch",
            "message": "WebSearch service is running"
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail="Service unavailable")

# Initialize service with settings
websearch_service = WebSearchService()

@router.post("/search")
async def web_search(request: Request):
    """Handle web search requests"""
    try:
        logger.info("Received web search request")
        data = await request.json()
        logger.info(f"Search query: {data.get('query')}")

        if not data.get('query'):
            logger.error("No query provided")
            return {
                "status": "error",
                "message": "No search query provided"
            }

        logger.info("Performing web search...")
        results = websearch_service.search_and_process(
            data['query'],
            filter_context=True,
            num_results=settings.MAX_SEARCH_RESULTS
        )
        logger.info(f"Search results: {results}")

        formatted_results = [{
            "title": r["title"],
            "link": r["url"],
            "snippet": r["summary"]
        } for r in results]

        logger.info(f"Formatted results: {formatted_results}")
        return {
            "status": "success",
            "results": formatted_results
        }
    except Exception as e:
        logger.error(f"Error in web search: {str(e)}")
        logger.exception("Full traceback:")
        raise HTTPException(status_code=500, detail=str(e)) 