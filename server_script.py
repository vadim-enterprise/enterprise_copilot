#!/usr/bin/env python3
import subprocess
import sys
import os
from pathlib import Path
import logging
import chromadb
from chromadb.config import Settings
from openai import OpenAI
from dotenv import load_dotenv
import signal
import time
import psutil

# Setup Django environment
BASE_DIR = Path(__file__).resolve().parent
DJANGO_PROJECT_DIR = BASE_DIR / 'django_project'
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')

import django
django.setup()

from django.conf import settings as django_settings

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def kill_process_on_port(port):
    """Kill any process running on the specified port"""
    try:
        for conn in psutil.net_connections(kind='inet'):
            if conn.laddr.port == port:
                try:
                    process = psutil.Process(conn.pid)
                    process.kill()
                    process.wait()
                    logger.info(f"Killed process {conn.pid} running on port {port}")
                    time.sleep(1)  # Wait for process to terminate
                    return
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
    except (psutil.AccessDenied, psutil.Error) as e:
        logger.warning(f"Could not check port {port}: {e}")
        # Fallback to platform-specific commands
        try:
            if sys.platform.startswith('win'):
                subprocess.run(['taskkill', '/F', '/PID', 
                    subprocess.check_output(f'netstat -ano | findstr :{port}', shell=True)
                    .decode().strip().split()[-1]], check=True)
            else:
                subprocess.run(f"lsof -ti :{port} | xargs kill -9", shell=True)
            logger.info(f"Killed process on port {port} using system command")
        except Exception as e:
            logger.error(f"Error killing process on port {port}: {e}")

def collect_static():
    """Collect Django static files"""
    try:
        manage_py = BASE_DIR / 'manage.py'
        if not manage_py.exists():
            logger.error(f"Error: manage.py not found at {manage_py}")
            return False
            
        result = subprocess.run(
            [sys.executable, str(manage_py), 'collectstatic', '--noinput'],
            capture_output=True,
            text=True
        )
        logger.info(result.stdout)
        return result.returncode == 0
    except Exception as e:
        logger.error(f"Error collecting static files: {e}")
        return False

def initialize_chroma():
    """Initialize or migrate ChromaDB"""
    try:
        chroma_dir = os.path.join(django_settings.BASE_DIR, 'chroma_data')
        os.makedirs(chroma_dir, exist_ok=True)
        
        # Initialize ChromaDB client with new architecture
        client = chromadb.PersistentClient(
            path=str(chroma_dir)
        )

        # Try to get or create knowledge base collection
        try:
            collection = client.get_collection("knowledge_base")
            logger.info("Existing knowledge base collection found")
        except:
            collection = client.create_collection(
                name="knowledge_base",
                metadata={"hnsw:space": "cosine"}
            )
            logger.info("Created new knowledge base collection")

        # Verify collection
        try:
            count = len(collection.get()['documents'])
            logger.info(f"Knowledge base contains {count} documents")
        except Exception as e:
            logger.error(f"Error verifying collection: {e}")
            return False

        return True

    except Exception as e:
        logger.error(f"Error initializing ChromaDB: {e}")
        return False

def verify_openai_key():
    """Verify OpenAI API key is working"""
    try:
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        # Test API key with a simple embedding request
        response = client.embeddings.create(
            input="test",
            model="text-embedding-ada-002"
        )
        logger.info("OpenAI API key verified successfully")
        return True
    except Exception as e:
        logger.error(f"Error verifying OpenAI API key: {e}")
        return False

def start_fastapi_server():
    """Start the FastAPI server"""
    # Check for OPENAI_API_KEY
    if not os.getenv('OPENAI_API_KEY'):
        print("Error: OPENAI_API_KEY environment variable is not set")
        print("Please set your OpenAI API key:")
        print("export OPENAI_API_KEY=your_api_key_here")
        sys.exit(1)

    # Kill any existing process on port 8001
    kill_process_on_port(8001)

    # Set up paths
    project_root = Path(__file__).resolve().parent
    fastapi_app_dir = project_root / 'software_auction' / 'fastapi_app'
    
    # Set PYTHONPATH
    os.environ['PYTHONPATH'] = f"{str(project_root)}:{os.environ.get('PYTHONPATH', '')}"
    
    # Start FastAPI server
    print("Starting FastAPI server...")
    fastapi_process = subprocess.Popen(
        [sys.executable, 'run.py'],
        cwd=str(fastapi_app_dir),
        env=os.environ.copy()
    )
    return fastapi_process

def apply_migrations():
    """Apply Django migrations"""
    try:
        from django.core.management import call_command
        call_command('migrate', interactive=False)
        logger.info("Database migrations applied successfully")
        return True
    except Exception as e:
        logger.error(f"Error applying migrations: {e}")
        return False

def main():
    """Main function to start both servers"""
    # Store the current working directory
    original_cwd = os.getcwd()
    
    try:
        # Kill any existing processes on both ports
        logger.info("Checking for existing processes...")
        kill_process_on_port(8000)  # Django port
        kill_process_on_port(8001)  # FastAPI port
        
        # Start FastAPI server
        logger.info("Starting FastAPI server...")
        fastapi_process = start_fastapi_server()
        
        # Wait a moment for FastAPI to start
        time.sleep(2)
        
        # Existing Django server startup code
        logger.info("Starting Django server...")
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
        
        # Apply migrations before other initializations
        if not apply_migrations():
            logger.error("Database migration failed")
            sys.exit(1)
        
        # Initialize required services
        if not verify_openai_key():
            logger.error("OpenAI API key verification failed")
            sys.exit(1)

        if not initialize_chroma():
            logger.error("ChromaDB initialization failed")
            sys.exit(1)
            
        if not collect_static():
            logger.error("Static file collection failed")
            sys.exit(1)
        
        # Start Django server
        from django.core.management import execute_from_command_line
        execute_from_command_line(['manage.py', 'runserver'])
        
    except KeyboardInterrupt:
        logger.info("\nShutting down servers...")
        if 'fastapi_process' in locals():
            fastapi_process.terminate()
            fastapi_process.wait()
        
    except Exception as e:
        logger.error(f"Error starting servers: {e}")
        if 'fastapi_process' in locals():
            fastapi_process.terminate()
            fastapi_process.wait()
        sys.exit(1)
        
    finally:
        # Restore the original working directory
        os.chdir(original_cwd)

if __name__ == '__main__':
    main() 