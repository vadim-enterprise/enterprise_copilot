import os
import sys
from pathlib import Path
import socket
import logging
import uvicorn

# Load environment variables
from software_auction.fastapi_app.utils.env_loader import load_env_variables
load_env_variables()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

def check_port(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(('127.0.0.1', port))
        sock.close()
        return True
    except OSError:
        return False

if __name__ == "__main__":
    # Add the Django project root to Python path
    project_root = Path(__file__).resolve().parent.parent.parent
    sys.path.insert(0, str(project_root))
    
    # Verify OPENAI_API_KEY is set
    if not os.getenv('OPENAI_API_KEY'):
        logger.error("OPENAI_API_KEY environment variable is not set!")
        sys.exit(1)
    
    PORT = 8001
    
    if not check_port(PORT):
        logger.error(f"Port {PORT} is already in use!")
        logger.error("Make sure no other process is using this port")
        sys.exit(1)
    
    logger.info("Starting FastAPI server...")
    logger.info(f"Project root: {project_root}")
    
    try:
        uvicorn.run(
            "software_auction.fastapi_app.main:app",
            host="127.0.0.1",
            port=PORT,
            reload=False,
            reload_dirs=[str(project_root)],
            log_level="info",
            workers=1
        )
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        sys.exit(1) 