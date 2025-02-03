import os
import logging
from pathlib import Path
import tempfile
from openai import OpenAI
from fastapi import HTTPException, UploadFile, File
import aiofiles

logger = logging.getLogger(__name__)

class TranscriptionService:
    def __init__(self):
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            logger.error("OPENAI_API_KEY environment variable is not set!")
            raise RuntimeError("OpenAI API key is not configured")
            
        self.client = OpenAI(api_key=api_key)
        
    async def transcribe_audio(self, audio_file: UploadFile) -> dict:
        """Transcribe audio file using OpenAI Whisper"""
        if not audio_file:
            raise HTTPException(status_code=400, detail="No audio file provided")
            
        try:
            logger.info(f"Received audio file: {audio_file.filename}, size: {audio_file.size}, content_type: {audio_file.content_type}")
            
            # Read the audio content
            content = await audio_file.read()
            if len(content) < 1000:  # Less than 1KB
                raise HTTPException(
                    status_code=400, 
                    detail="Audio file too short. Please record a longer message."
                )
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.webm') as tmp_file:
                logger.info(f"Created temporary file: {tmp_file.name}")
                tmp_file.write(content)
                tmp_file_path = tmp_file.name

            try:
                # Transcribe the audio
                logger.info("Starting transcription...")
                with open(tmp_file_path, 'rb') as f:
                    transcript = self.client.audio.transcriptions.create(
                        model="whisper-1",
                        file=f,
                        response_format="text",
                        language="en",
                        temperature=0.3,
                        prompt="This is a conversation about software and technology."
                    )
                    
                logger.info(f"Transcription successful: {transcript[:100]}...")
                
                if not transcript or not transcript.strip():
                    raise HTTPException(
                        status_code=400,
                        detail="Could not transcribe audio. Please try again."
                    )
                    
                return {
                    'status': 'success',
                    'text': transcript
                }
                
            except Exception as e:
                logger.error(f"OpenAI transcription error: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Transcription failed: {str(e)}"
                )
            finally:
                # Clean up temporary file
                try:
                    os.unlink(tmp_file_path)
                    logger.info(f"Cleaned up temporary file: {tmp_file_path}")
                except Exception as e:
                    logger.error(f"Error cleaning up temporary file: {str(e)}")
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in transcribe_audio: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="An unexpected error occurred during transcription"
            )

    async def handle_transcription_request(self, audio: UploadFile = File(...)):
        """Handle transcription request and return transcribed text."""
        result = await self.transcribe_audio(audio)
        if result['status'] == 'error':
            raise HTTPException(status_code=500, detail=result['message'])
        return result 