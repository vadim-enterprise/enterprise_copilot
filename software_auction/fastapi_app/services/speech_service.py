from pathlib import Path
import os
import logging
from openai import OpenAI
from fastapi import HTTPException
import uuid
from typing import Dict, Any
import asyncio
from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaRecorder
import aiohttp

logger = logging.getLogger(__name__)

class SpeechService:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        # Update path to be relative to Django project
        self.audio_dir = Path(__file__).resolve().parent.parent.parent.parent / 'media' / 'tts_audio'
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        
        # Realtime speech settings
        self.base_url = "https://api.openai.com/v1/realtime"
        self.model = "gpt-4o-realtime-preview-2024-12-17"
        self.pcs = set()
        self.recorder = None

    async def generate_speech(self, text: str, voice: str = "alloy") -> dict:
        """Generate speech from text and return the audio file path"""
        try:
            filename = f"speech_{uuid.uuid4()}.mp3"
            speech_file_path = self.audio_dir / filename
            
            response = self.client.audio.speech.create(
                model="tts-1",
                voice=voice,
                input=text
            )
            
            response.stream_to_file(str(speech_file_path))
            
            return {
                'status': 'success',
                'filename': filename,
                'audio_url': f"/media/tts_audio/{filename}"
            }

        except Exception as e:
            logger.error(f"Error generating speech: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    async def create_session(self) -> Dict[str, Any]:
        """Create a new realtime session"""
        try:
            # Create a session with OpenAI's realtime API
            headers = {
                "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.openai.com/v1/audio/realtime/sessions",
                    headers=headers,
                    json={
                        "model": "gpt-4o-realtime-preview-2024-12-17",
                        "voice": "verse"
                    }
                ) as response:
                    data = await response.json()
                    
                    if response.status != 200:
                        raise HTTPException(
                            status_code=response.status,
                            detail=f"OpenAI API error: {data.get('error', {}).get('message', 'Unknown error')}"
                        )
            
            return {
                "status": "success",
                "token": data["client_secret"]["value"],
                "expires_at": data["client_secret"]["expires_at"]
            }
        except Exception as e:
            logger.error(f"Error creating realtime session: {str(e)}")
            raise

    async def handle_realtime_events(self, websocket):
        """Handle realtime WebSocket events"""
        try:
            async for message in websocket:
                # Handle incoming WebSocket messages
                if message.type == "websocket.receive":
                    data = message.json()
                    if data["type"] == "start_listening":
                        # Start speech recognition
                        pass
                    elif data["type"] == "stop_listening":
                        # Stop speech recognition
                        pass
        except Exception as e:
            logger.error(f"Error handling realtime events: {str(e)}")
            raise

    async def handle_sdp_offer(self, sdp: str) -> str:
        """Handle SDP offer and return answer"""
        try:
            logger.info("Received SDP offer")
            pc = RTCPeerConnection()
            self.pcs.add(pc)

            @pc.on("connectionstatechange")
            async def on_connectionstatechange():
                logger.info(f"Connection state is {pc.connectionState}")
                if pc.connectionState == "failed":
                    await pc.close()
                    self.pcs.discard(pc)

            @pc.on("track")
            def on_track(track):
                logger.info(f"Track received: {track.kind}")
                if track.kind == "audio":
                    pc.addTrack(track)
                    if self.recorder is None:
                        self.recorder = MediaRecorder("audio.wav")
                    self.recorder.addTrack(track)

            # Set remote description
            logger.info("Setting remote description")
            offer = RTCSessionDescription(sdp=sdp, type="offer")
            await pc.setRemoteDescription(offer)

            # Create answer
            logger.info("Creating answer")
            answer = await pc.createAnswer()
            await pc.setLocalDescription(answer)

            logger.info("Returning SDP answer")
            return pc.localDescription.sdp

        except Exception as e:
            logger.error(f"Error handling SDP offer: {str(e)}")
            raise

    async def cleanup(self):
        """Cleanup resources"""
        coros = [pc.close() for pc in self.pcs]
        await asyncio.gather(*coros)
        self.pcs.clear()
        if self.recorder:
            await self.recorder.stop()

    def __del__(self):
        """Cleanup when the service is destroyed"""
        if self.pcs:
            asyncio.create_task(self.cleanup()) 