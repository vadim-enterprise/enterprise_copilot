from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request
from ..services.transcription_service import TranscriptionService
from ..services.tts_service import TTSService
import logging
import os
from openai import OpenAI

router = APIRouter()

# Initialize services
transcription_service = TranscriptionService()
tts_service = TTSService()

logger = logging.getLogger(__name__)

# Initialize OpenAI client
openai_client = OpenAI()

@router.post("/transcribe-speech/")
async def transcribe_speech(audio: UploadFile = File(...)):
    """Transcribe speech using Whisper API"""
    try:
        # Read the audio file
        audio_content = await audio.read()
        
        # Create a temporary file
        temp_path = f"temp_{audio.filename}"
        try:
            # Save audio to temporary file
            with open(temp_path, "wb") as temp_file:
                temp_file.write(audio_content)
            
            # Transcribe using Whisper
            with open(temp_path, "rb") as audio_file:
                transcript = openai_client.audio.transcriptions.create(
                    file=audio_file,
                    model="whisper-1",
                    response_format="text"
                )
            
            return {
                "status": "success",
                "text": transcript
            }
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
    except Exception as e:
        logger.error(f"Error transcribing speech: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health-check")
async def health_check():
    """Check if the speech service is available"""
    return {"status": "ok"}

@router.post("/generate-insights/")
async def generate_insights(data: dict):
    """Endpoint to generate insights."""
    try:
        # Use OpenAI directly for insights generation
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": f"Analyze and provide insights for: {data}"}],
            temperature=0.7,
            max_tokens=500
        )
        
        insights = response.choices[0].message.content
        
        return {
            "status": "success",
            "insights": insights
        }
    except Exception as e:
        logger.error(f"Error generating insights: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/update-knowledge/")
async def update_knowledge(data: dict):
    """Endpoint to update the knowledge base."""
    try:
        # Use OpenAI directly for knowledge base updates
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": f"Update knowledge base with: {data}"}],
            temperature=0.7,
            max_tokens=500
        )
        
        return {
            "status": "success",
            "message": "Knowledge base updated successfully"
        }
    except Exception as e:
        logger.error(f"Error updating knowledge base: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/session")
async def create_session():
    """Create a new realtime session"""
    try:
        # Return a simple session ID for now
        return {
            "status": "success",
            "session_id": "default_session"
        }
    except Exception as e:
        logger.error(f"Session creation error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sdp")
async def handle_sdp(request: Request):
    """Handle SDP offer and return answer"""
    try:
        # Return a simple SDP answer for now
        return {
            "status": "success",
            "sdp": "v=0\no=- 0 0 IN IP4 127.0.0.1\ns=-\nt=0 0\na=group:BUNDLE audio\nm=audio 9 UDP/TLS/RTP/SAVPF 111 103 104 9 0 8 106 105 13 110 112 113 126\nc=IN IP4 0.0.0.0\na=rtcp:9 IN IP4 0.0.0.0\na=ice-ufrag:default\na=ice-pwd:default\n"
        }
    except Exception as e:
        logger.error(f"SDP handling error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 