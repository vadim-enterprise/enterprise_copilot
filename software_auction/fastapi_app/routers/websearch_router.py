from fastapi import APIRouter, HTTPException
from ..services.websearch_service import WebSearchService, ModelChoice
from ..services import settings
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# Initialize service with settings
websearch_service = WebSearchService(
    model_choice=ModelChoice.OPENAI
)

@router.post("/search")
async def web_search(query: dict):
    """Endpoint to perform web search"""
    try:
        results = websearch_service.search_and_process(
            query.get('query', ''),
            filter_context=True,
            num_results=settings.MAX_SEARCH_RESULTS
        )
        
        if not results:
            return {
                "status": "success",
                "results": []
            }
            
        formatted_results = [{
            "title": result["title"],
            "description": result["summary"],
            "url": result["url"]
        } for result in results]
        
        return {
            "status": "success",
            "results": formatted_results
        }
    except Exception as e:
        logger.error(f"Web search error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 