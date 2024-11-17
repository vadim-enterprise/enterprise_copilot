from fastapi import WebSocket, WebSocketDisconnect
from typing import Set
import json
from .speech_service import SpeechService

class TranscriptionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.speech_service = SpeechService()
        self.buffer_size = 4096  # Smaller buffer for faster processing

    async def handle_connection(self, websocket: WebSocket):
        try:
            while True:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                if "audio_data" in message:
                    # Process in smaller chunks
                    transcription = await self.speech_service.transcribe_audio(
                        message["audio_data"],
                        message.get("sample_rate", 44100),
                        message.get("channels", 1)
                    )
                    
                    if transcription:
                        # Send immediately when we get any text
                        await websocket.send_json({
                            "status": "transcription",
                            "text": transcription.strip()
                        })
                    
        except WebSocketDisconnect:
            await self.disconnect(websocket)
        except Exception as e:
            print(f"Error in handle_connection: {e}")
            await websocket.send_json({
                "status": "error",
                "error": str(e)
            })