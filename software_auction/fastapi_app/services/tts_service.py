import os
import logging
from openai import OpenAI
from pathlib import Path
import uuid
from fastapi import HTTPException, Form

logger = logging.getLogger(__name__)

class TTSService:
    def __init__(self):
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            logger.error("OPENAI_API_KEY environment variable is not set!")
            raise RuntimeError("OpenAI API key is not configured")
        
        self.client = OpenAI(api_key=api_key)
        # Get the media directory path from the FastAPI app
        self.media_dir = Path(__file__).resolve().parent.parent.parent.parent / 'media' / 'tts_audio'
        self.media_dir.mkdir(parents=True, exist_ok=True)

    def generate_speech(self, text: str, voice: str = "alloy") -> dict:
        """Generate speech from text using OpenAI's TTS."""
        try:
            if not text:
                return {
                    'status': 'error',
                    'message': 'Text is required'
                }

            response = self.client.audio.speech.create(
                model="tts-1",
                voice=voice,
                input=text
            )
            
            # Generate a unique filename
            filename = f"speech_{uuid.uuid4()}.mp3"
            file_path = self.media_dir / filename
            
            # Save the audio content
            with open(file_path, 'wb') as f:
                f.write(response.content)
            
            # Return the URL path to the audio file
            return {
                'status': 'success',
                'audio_url': f'/media/tts_audio/{filename}',
                'content_type': 'audio/mpeg'
            }
        except Exception as e:
            logger.error(f"Error generating speech: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }

    async def handle_tts_request(self, text: str = Form(...), voice: str = Form("alloy")):
        """Handle TTS request and generate speech."""
        if not text:
            raise HTTPException(status_code=422, detail="Text is required")
            
        result = self.generate_speech(text, voice)
        if result['status'] == 'error':
            raise HTTPException(status_code=500, detail=result['message'])
        return result 