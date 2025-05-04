from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
import logging
import os
from openai import OpenAI
from typing import Optional, List
import json
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

@router.get("/search")
async def web_search(
    query: str = Query(..., description="Search query"),
    max_results: int = Query(5, description="Maximum number of results to return")
) -> JSONResponse:
    """
    Perform a web search using the provided query.
    """
    try:
        logger.info(f"Performing web search for query: {query}")
        
        # Use OpenAI's search API
        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that performs web searches."},
                {"role": "user", "content": f"Search the web for: {query}"}
            ],
            max_tokens=1000
        )
        
        # Extract search results from the response
        search_results = response.choices[0].message.content
        
        # Format the response
        results = {
            "query": query,
            "results": search_results,
            "count": len(search_results.split("\n")),
            "status": "success"
        }
        
        return JSONResponse(content=results)
        
    except Exception as e:
        logger.error(f"Error performing web search: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error performing web search: {str(e)}"
        )

@router.get("/suggest")
async def suggest_queries(
    query: str = Query(..., description="Partial search query")
) -> JSONResponse:
    """
    Suggest search queries based on the partial input.
    """
    try:
        logger.info(f"Generating search suggestions for: {query}")
        
        # Use OpenAI to generate suggestions
        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that suggests search queries."},
                {"role": "user", "content": f"Suggest 5 search queries related to: {query}"}
            ],
            max_tokens=200
        )
        
        # Extract suggestions from the response
        suggestions = response.choices[0].message.content.split("\n")
        
        # Format the response
        results = {
            "query": query,
            "suggestions": suggestions,
            "count": len(suggestions),
            "status": "success"
        }
        
        return JSONResponse(content=results)
        
    except Exception as e:
        logger.error(f"Error generating suggestions: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating suggestions: {str(e)}"
        ) 