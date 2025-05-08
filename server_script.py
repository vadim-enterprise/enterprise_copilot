#!/usr/bin/env python3
import subprocess
import sys
import os
from pathlib import Path
import logging
from openai import OpenAI
from dotenv import load_dotenv
import signal
import time
import psutil
import socket

# Setup Django environment
BASE_DIR = Path(__file__).resolve().parent
DJANGO_PROJECT_DIR = BASE_DIR / 'django_project'
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')

import django
django.setup()

from django.conf import settings as django_settings
from django.db import connection

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def is_port_in_use(port):
    """Check if a port is in use"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def ensure_postgres_running():
    """Ensure PostgreSQL is running on port 5540"""
    if is_port_in_use(5540):
        logger.info("PostgreSQL is already running on port 5540")
        # Check if database exists
        try:
            result = subprocess.run([
                'psql',
                '-h', 'localhost',
                '-p', '5540',
                'postgres',
                '-c', 'SELECT 1 FROM pg_database WHERE datname = \'pred_genai\';',
                '-t'
            ], check=True, capture_output=True, text=True)
            if '1 row' in result.stdout:
                logger.info("Database pred_genai exists")
                return True
            logger.info("Database pred_genai does not exist, will create it")
        except subprocess.CalledProcessError as e:
            logger.error(f"Error checking database: {e.stderr}")
            return False

    logger.info("Starting PostgreSQL on port 5540...")
    try:
        # Create data directory if it doesn't exist
        data_dir = BASE_DIR / 'postgres_data'
        data_dir.mkdir(exist_ok=True)

        # Initialize database if it doesn't exist
        if not (data_dir / 'PG_VERSION').exists():
            logger.info("Initializing PostgreSQL database...")
            subprocess.run([
                'initdb',
                '-D', str(data_dir),
                '--auth=trust'
            ], check=True)

            # Configure PostgreSQL to allow local connections
            pg_hba_conf = data_dir / 'pg_hba.conf'
            with open(pg_hba_conf, 'w') as f:
                f.write("""# TYPE  DATABASE        USER            ADDRESS                 METHOD
local   all             all                                     trust
host    all             all             127.0.0.1/32            trust
host    all             all             ::1/128                 trust
""")

            # Configure PostgreSQL to listen on localhost and disable GSSAPI
            postgresql_conf = data_dir / 'postgresql.conf'
            with open(postgresql_conf, 'w') as f:
                f.write("""listen_addresses = 'localhost'
port = 5540
krb_server_keyfile = ''
gss_accept_delegation = off
ssl = off
""")

        # Start PostgreSQL
        subprocess.Popen([
            'postgres',
            '-D', str(data_dir),
            '-p', '5540'
        ])

        # Wait for PostgreSQL to start
        max_retries = 30
        for i in range(max_retries):
            if is_port_in_use(5540):
                logger.info("PostgreSQL started successfully")
                break
            time.sleep(1)
        else:
            logger.error("Failed to start PostgreSQL")
            return False

        # Wait for PostgreSQL to be ready to accept connections
        max_retries = 30
        for i in range(max_retries):
            try:
                subprocess.run([
                    'psql',
                    '-h', 'localhost',
                    '-p', '5540',
                    'postgres',
                    '-c', 'SELECT 1;'
                ], check=True, capture_output=True)
                break
            except subprocess.CalledProcessError:
                if i == max_retries - 1:
                    logger.error("PostgreSQL failed to accept connections")
                    return False
                time.sleep(1)

        # Create database if it doesn't exist
        try:
            # First connect to postgres database to create our database
            logger.info("Creating database pred_genai...")
            
            # Drop existing connections to the database
            subprocess.run([
                'psql',
                '-h', 'localhost',
                '-p', '5540',
                'postgres',
                '-c', """
                SELECT pg_terminate_backend(pg_stat_activity.pid)
                FROM pg_stat_activity
                WHERE pg_stat_activity.datname = 'pred_genai'
                AND pid <> pg_backend_pid();
                """
            ], check=True, capture_output=True)
            
            # Drop and recreate the database
            subprocess.run([
                'psql',
                '-h', 'localhost',
                '-p', '5540',
                'postgres',
                '-c', 'DROP DATABASE IF EXISTS pred_genai;'
            ], check=True, capture_output=True)
            
            subprocess.run([
                'psql',
                '-h', 'localhost',
                '-p', '5540',
                'postgres',
                '-c', 'CREATE DATABASE pred_genai OWNER glinskiyvadim;'
            ], check=True, capture_output=True)
            logger.info("Created database pred_genai")

            # Grant all privileges to the user
            subprocess.run([
                'psql',
                '-h', 'localhost',
                '-p', '5540',
                'pred_genai',
                '-c', 'GRANT ALL PRIVILEGES ON DATABASE pred_genai TO glinskiyvadim;'
            ], check=True, capture_output=True)
            logger.info("Granted privileges to glinskiyvadim")

            # Set up the database with proper transaction handling
            subprocess.run([
                'psql',
                '-h', 'localhost',
                '-p', '5540',
                'pred_genai',
                '-c', """
                ALTER DATABASE pred_genai SET default_transaction_isolation TO 'read committed';
                ALTER DATABASE pred_genai SET default_transaction_read_only TO off;
                """
            ], check=True, capture_output=True)
            logger.info("Configured database transaction settings")

            # Verify database exists and is accessible
            result = subprocess.run([
                'psql',
                '-h', 'localhost',
                '-p', '5540',
                'pred_genai',
                '-c', 'SELECT 1;'
            ], check=True, capture_output=True, text=True)
            
            if '1 row' in result.stdout:
                logger.info("Successfully verified database pred_genai is accessible")
                return True
            else:
                logger.error("Database verification failed")
                return False

        except subprocess.CalledProcessError as e:
            logger.error(f"Error creating/verifying database: {e.stderr.decode()}")
            return False

    except Exception as e:
        logger.error(f"Error starting PostgreSQL: {e}")
        return False

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

def setup_pgvector():
    """Setup pgvector extension in PostgreSQL"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            logger.info("pgvector extension created or already exists")
        return True
    except Exception as e:
        logger.error(f"Error setting up pgvector: {e}")
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
        # Ensure PostgreSQL is running
        if not ensure_postgres_running():
            logger.error("Failed to start PostgreSQL")
            sys.exit(1)

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

        if not setup_pgvector():
            logger.error("pgvector setup failed")
            sys.exit(1)
            
        if not collect_static():
            logger.error("Static file collection failed")
            sys.exit(1)
        
        # Start Django server
        logger.info("Starting Django development server...")
        manage_py = BASE_DIR / 'manage.py'
        if not manage_py.exists():
            logger.error(f"manage.py not found at {manage_py}")
            sys.exit(1)
            
        logger.info(f"Using manage.py at: {manage_py}")
        django_process = subprocess.Popen(
            [sys.executable, str(manage_py), 'runserver', '0.0.0.0:8000'],
            cwd=str(BASE_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Check if Django server started successfully
        time.sleep(2)
        if django_process.poll() is not None:
            stdout, stderr = django_process.communicate()
            logger.error(f"Django server failed to start. Exit code: {django_process.returncode}")
            logger.error(f"stdout: {stdout}")
            logger.error(f"stderr: {stderr}")
            sys.exit(1)
            
        logger.info("Django server started successfully")
        
        # Wait for both processes
        try:
            while True:
                if fastapi_process.poll() is not None:
                    logger.error("FastAPI server stopped unexpectedly")
                    break
                if django_process.poll() is not None:
                    logger.error("Django server stopped unexpectedly")
                    break
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("\nShutting down servers...")
            fastapi_process.terminate()
            django_process.terminate()
            fastapi_process.wait()
            django_process.wait()
        
    except Exception as e:
        logger.error(f"Error starting servers: {e}")
        if 'fastapi_process' in locals():
            fastapi_process.terminate()
            fastapi_process.wait()
        if 'django_process' in locals():
            django_process.terminate()
            django_process.wait()
        sys.exit(1)
        
    finally:
        # Restore the original working directory
        os.chdir(original_cwd)

if __name__ == '__main__':
    main() 