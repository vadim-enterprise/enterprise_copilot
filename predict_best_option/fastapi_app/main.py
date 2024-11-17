from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from .transcription import TranscriptionManager

app = FastAPI()

ALLOWED_ORIGINS = [
    "https://www.b2bappstore.click",
    "http://localhost:8000",  # Keep for local development
    "http://127.0.0.1:8000"
]

# CORS settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize WebSocket manager
transcription_manager = TranscriptionManager()

@app.websocket("/ws/transcribe/")
async def websocket_endpoint(websocket: WebSocket):
    client_host = websocket.client.host
    print(f"WebSocket connection attempt from {client_host}")
    
    # Check origin
    origin = websocket.headers.get("origin", "")
    if origin not in ALLOWED_ORIGINS and not any(origin.endswith(host) for host in ALLOWED_ORIGINS):
        print(f"Rejected connection from unauthorized origin: {origin}")
        await websocket.close(code=1008)  # Policy violation
        return
        
    await transcription_manager.connect(websocket)
    try:
        await transcription_manager.handle_connection(websocket)
    except Exception as e:
        print(f"Error in WebSocket connection: {e}")
    finally:
        await transcription_manager.disconnect(websocket)