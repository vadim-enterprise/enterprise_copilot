import json
from channels.generic.websocket import AsyncWebsocketConsumer
import speech_recognition as sr
import asyncio
import base64
import numpy as np
import wave
import io
import os
import logging
import tempfile
from pydub import AudioSegment

logger = logging.getLogger(__name__)

class Transcription(AsyncWebsocketConsumer):
    async def connect(self):
        logger.info("WebSocket connection attempt...")
        try:
            await self.accept()
            logger.info("WebSocket connection accepted!")
            await self.send(text_data=json.dumps({
                'status': 'connected',
                'message': 'WebSocket connection established'
            }))
        except Exception as e:
            logger.error(f"Connection error: {str(e)}")
            raise

    async def disconnect(self, close_code):
        logger.info(f"WebSocket disconnected with code: {close_code}")

    async def receive(self, text_data):
        try:
            text_data_json = json.loads(text_data)
            
            if 'audio_data' in text_data_json:
                audio_data = base64.b64decode(text_data_json['audio_data'])
                
                # Process smaller chunks of audio
                with io.BytesIO() as wav_io:
                    with wave.open(wav_io, 'wb') as wav_file:
                        wav_file.setnchannels(1)
                        wav_file.setsampwidth(2)
                        wav_file.setframerate(16000)
                        wav_file.writeframes(audio_data)
                    
                    wav_io.seek(0)
                    transcription = await self.transcribe_audio(wav_io)
                    
                    if transcription:
                        # Send transcription immediately
                        await self.send(text_data=json.dumps({
                            'status': 'transcription',
                            'text': transcription
                        }))
                        logger.info(f"Sent transcription: {transcription}")
                    else:
                        logger.debug("No speech detected in audio chunk")
                    
        except Exception as e:
            logger.error(f"Error in receive: {str(e)}")
            await self.send(text_data=json.dumps({
                'status': 'error',
                'error': str(e)
            }))

    async def transcribe_audio(self, audio_file):
        loop = asyncio.get_event_loop()
        recognizer = sr.Recognizer()

        def recognize():
            with sr.AudioFile(audio_file) as source:
                # Adjust recognition settings for real-time transcription
                recognizer.dynamic_energy_threshold = True
                recognizer.energy_threshold = 300
                recognizer.pause_threshold = 0.3  # Shorter pause threshold
                recognizer.phrase_threshold = 0.1  # More aggressive phrase detection
                recognizer.non_speaking_duration = 0.1  # Shorter non-speaking duration
                
                # Record with minimal noise adjustment
                recognizer.adjust_for_ambient_noise(source, duration=0.1)
                audio = recognizer.record(source)
                
                try:
                    # Use partial results for faster transcription
                    result = recognizer.recognize_google(
                        audio,
                        language='en-US',
                        show_all=False
                    )
                    return result if result else None
                except sr.UnknownValueError:
                    return None
                except sr.RequestError as e:
                    logger.error(f"Google Speech Recognition error: {str(e)}")
                    return None

        return await loop.run_in_executor(None, recognize)