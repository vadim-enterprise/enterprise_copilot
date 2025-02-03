from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request
from ..services.speech_service import SpeechService
from ..services.transcription_service import TranscriptionService
from ..services.tts_service import TTSService
from ..services.insights_service import InsightsService
from ..services.knowledge_service import KnowledgeService
import logging

router = APIRouter()

# Initialize services
speech_service = SpeechService()  # This now handles both TTS and realtime speech
transcription_service = TranscriptionService()
tts_service = TTSService()
insights_service = InsightsService()
knowledge_service = KnowledgeService()

logger = logging.getLogger(__name__)

@router.post("/generate-speech/")
async def generate_speech(text: str, voice: str = "alloy"):
    """Endpoint to generate speech from text."""
    result = tts_service.generate_speech(text, voice)
    if result['status'] == 'error':
        raise HTTPException(status_code=500, detail=result['message'])
    return result

@router.post("/transcribe-speech/")
async def transcribe_speech(audio: UploadFile = File(...)):
    """Transcribe speech to text"""
    return await transcription_service.transcribe_audio(audio)

@router.get("/health-check")
async def health_check():
    """Check if the speech service is available"""
    return {"status": "ok"}

@router.post("/generate-insights/")
async def generate_insights(data: dict):
    """Endpoint to generate insights."""
    result = insights_service.generate_insights(data)
    if result['status'] == 'error':
        raise HTTPException(status_code=500, detail=result['message'])
    return result

@router.post("/update-knowledge/")
async def update_knowledge(data: dict):
    """Endpoint to update the knowledge base."""
    result = knowledge_service.update_knowledge_base(data)
    if result['status'] == 'error':
        raise HTTPException(status_code=500, detail=result['message'])
    return result

@router.post("/session")
async def create_session():
    """Create a new realtime session"""
    try:
        result = await speech_service.create_session()
        if result['status'] == 'error':
            raise HTTPException(status_code=500, detail=result['message'])
        return result
    except Exception as e:
        logger.error(f"Session creation error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sdp")
async def handle_sdp(request: Request):
    """Handle SDP offer and return answer"""
    try:
        sdp = await request.body()
        return await speech_service.handle_sdp_offer(sdp.decode())
    except Exception as e:
        logger.error(f"SDP handling error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 