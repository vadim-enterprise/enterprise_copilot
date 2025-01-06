import json
from channels.generic.websocket import AsyncWebsocketConsumer
import speech_recognition as sr
import asyncio
import logging
from .hybrid_rag import HybridRAG

logger = logging.getLogger(__name__)

class Transcription(AsyncWebsocketConsumer):
    async def connect(self):
        self.hybrid_rag = HybridRAG()  # Initialize HybridRAG
        self.conversation_history = []
        await self.accept()
        print("WebSocket connected with HybridRAG support")

    async def disconnect(self, close_code):
        print(f"WebSocket disconnected with code: {close_code}")

    async def receive(self, text_data):
        try:
            text_data_json = json.loads(text_data)
            transcription = text_data_json.get('message', '')
            
            # Add transcription to conversation history
            self.conversation_history.append(transcription)
            
            # Use HybridRAG to process the transcription
            user_context = {
                "technical_level": "intermediate",
                "detail_preference": "balanced",
                "prior_knowledge": "some"
            }
            
            # Process with HybridRAG asynchronously
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                lambda: self.hybrid_rag.query(
                    question=transcription,
                    style="conversation",
                    user_context=user_context
                )
            )

            # Send enhanced response back
            await self.send(text_data=json.dumps({
                'message': transcription,
                'enhanced_response': result['answer'],
                'confidence': result['confidence'],
                'style_used': result['style_used'],
                'sources': result.get('sources', [])
            }))

        except Exception as e:
            print(f"Error in receive: {str(e)}")
            await self.send(text_data=json.dumps({
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

    async def send(self, text_data=None, bytes_data=None):
        # This method is inherited from AsyncWebsocketConsumer