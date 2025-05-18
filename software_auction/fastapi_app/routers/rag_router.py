from fastapi import APIRouter, Request, HTTPException, Response
import logging
from pydantic import BaseModel
from typing import Optional, List
import re
from openai import OpenAI
import os

rag_router = APIRouter()
logger = logging.getLogger(__name__)

# Initialize OpenAI client
openai_client = OpenAI()

class QueryRequest(BaseModel):
    query: str

class ChartResponse(BaseModel):
    code: str
    status: str = "success"

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
            # Use OpenAI directly for text queries
            response = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": data['query']}],
                temperature=0.7,
                max_tokens=500
            )
            
            if not response or not response.choices:
                raise ValueError("Empty response from OpenAI")
            
            return {
                "status": "success",
                "response": response.choices[0].message.content
            }
        except Exception as e:
            logger.error(f"OpenAI service error: {str(e)}")
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
        
        # Just log the data for now since we removed the knowledge base
        logger.info(f"Would have added to knowledge base: {data}")
        
        return {
            "status": "success",
            "message": "Successfully logged content (knowledge base functionality removed)"
        }
    except Exception as e:
        logger.error(f"Error adding to knowledge base: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }

@rag_router.post("/generate-chart", response_model=ChartResponse)
async def generate_chart(request: QueryRequest):
    """Extract Chart.js code from the transcribed text"""
    try:
        query = request.query.lower()
        
        # Look for code block in the transcribed text
        code_match = re.search(r'```javascript\n([\s\S]*?)\n```', query)
        if not code_match:
            return ChartResponse(
                status="error",
                code=""
            )
        
        # Extract and return the actual code
        extracted_code = code_match.group(1).strip()
        return ChartResponse(
            status="success",
            code=extracted_code
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
