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

def ensure_tile_postgres_running():
    """Ensure PostgreSQL is running on port 5541 for tile analytics"""
    # Check if port is in use and kill any process using it
    if is_port_in_use(5541):
        logger.info("Port 5541 is already in use. Stopping existing PostgreSQL instance...")
        kill_process_on_port(5541)
        # Wait for the port to be released
        max_retries = 10
        for i in range(max_retries):
            if not is_port_in_use(5541):
                logger.info("Port 5541 is now available.")
                break
            logger.info(f"Waiting for port 5541 to be released... ({i+1}/{max_retries})")
            time.sleep(1)
        else:
            logger.error("Could not free up port 5541. Please check for running processes manually.")
            return False

    logger.info("Starting PostgreSQL on port 5541...")
    try:
        # Create data directory if it doesn't exist
        data_dir = BASE_DIR / 'postgres_tile_data'
        if data_dir.exists():
            logger.info("Removing existing PostgreSQL data directory...")
            import shutil
            shutil.rmtree(str(data_dir), ignore_errors=True)
        data_dir.mkdir(exist_ok=True)

        # Initialize database
        logger.info("Initializing PostgreSQL database for tiles...")
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

        # Configure PostgreSQL to listen on localhost
        postgresql_conf = data_dir / 'postgresql.conf'
        with open(postgresql_conf, 'w') as f:
            f.write("""# Basic PostgreSQL configuration
listen_addresses = 'localhost'
port = 5541
max_connections = 100
shared_buffers = 128MB
dynamic_shared_memory_type = posix
max_wal_size = 1GB
min_wal_size = 80MB
""")

        # Start PostgreSQL
        postgres_process = subprocess.Popen([
            'postgres',
            '-D', str(data_dir),
            '-p', '5541',
            '-c', 'listen_addresses=localhost'
        ])

        # Wait for PostgreSQL to start
        max_retries = 30
        for i in range(max_retries):
            if is_port_in_use(5541):
                logger.info("PostgreSQL started successfully on port 5541")
                break
            logger.info(f"Waiting for PostgreSQL to start... ({i+1}/{max_retries})")
            time.sleep(1)
        else:
            logger.error("Failed to start PostgreSQL on port 5541")
            return False

        # Wait for PostgreSQL to be ready for connections
        max_retries = 30
        for i in range(max_retries):
            try:
                result = subprocess.run([
                    'psql',
                    '-h', 'localhost',
                    '-p', '5541',
                    'postgres',
                    '-c', 'SELECT 1;'
                ], check=True, capture_output=True, text=True)
                logger.info("PostgreSQL is ready for connections")
                break
            except subprocess.CalledProcessError:
                if i == max_retries - 1:
                    logger.error("PostgreSQL failed to become ready for connections")
                    return False
                time.sleep(1)

        # Create database and tables
        try:
            logger.info("Creating database tile_analytics...")
            
            # Create the database
            subprocess.run([
                'psql',
                '-h', 'localhost',
                '-p', '5541',
                'postgres',
                '-c', 'CREATE DATABASE tile_analytics;'
            ], check=True, capture_output=True)
            logger.info("Created database tile_analytics")

            # Grant ownership
            subprocess.run([
                'psql',
                '-h', 'localhost',
                '-p', '5541',
                'postgres',
                '-c', 'ALTER DATABASE tile_analytics OWNER TO glinskiyvadim;'
            ], check=True, capture_output=True)
            logger.info("Changed database ownership to glinskiyvadim")

            # Create the tiles table
            subprocess.run([
                'psql',
                '-h', 'localhost',
                '-p', '5541',
                'tile_analytics',
                '-c', """
                CREATE TABLE IF NOT EXISTS tile_data (
                    id SERIAL PRIMARY KEY,
                    tile_name VARCHAR(100) NOT NULL,
                    notification_type TEXT,
                    motion TEXT,
                    customer TEXT,
                    issue TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
                
                -- Create trigger to update updated_at timestamp
                CREATE OR REPLACE FUNCTION update_updated_at_column()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = CURRENT_TIMESTAMP;
                    RETURN NEW;
                END;
                $$ language 'plpgsql';
                
                DROP TRIGGER IF EXISTS update_tile_data_updated_at ON tile_data;
                CREATE TRIGGER update_tile_data_updated_at
                    BEFORE UPDATE ON tile_data
                    FOR EACH ROW
                    EXECUTE FUNCTION update_updated_at_column();
                
                -- Clear existing data
                TRUNCATE TABLE tile_data RESTART IDENTITY;
                
                -- Insert initial data for 12 tiles
                INSERT INTO tile_data (tile_name) VALUES
                    ('Churn Analysis'),
                    ('Competitor Analysis'),
                    ('Market Share'),
                    ('Sales Performance'),
                    ('Customer Satisfaction'),
                    ('Growth Opportunities'),
                    ('Revenue Analysis'),
                    ('Product Performance'),
                    ('Customer Demographics'),
                    ('Market Trends'),
                    ('Regional Analysis'),
                    ('Competitive Landscape');
                """
            ], check=True, capture_output=True)
            logger.info("Created tile_data table and inserted initial data")

            # Grant privileges
            subprocess.run([
                'psql',
                '-h', 'localhost',
                '-p', '5541',
                'tile_analytics',
                '-c', 'GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO glinskiyvadim;'
            ], check=True, capture_output=True)
            
            subprocess.run([
                'psql',
                '-h', 'localhost',
                '-p', '5541',
                'tile_analytics',
                '-c', 'GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO glinskiyvadim;'
            ], check=True, capture_output=True)
            logger.info("Granted privileges to glinskiyvadim")

            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Error creating/verifying database: {e.stderr if hasattr(e, 'stderr') else str(e)}")
            return False

    except Exception as e:
        logger.error(f"Error starting PostgreSQL: {e}")
        return False

def kill_process_on_port(port):
    """Kill any process running on the specified port"""
    logger.info(f"Attempting to kill process on port {port}...")
    
    # First try using psutil
    try:
        for conn in psutil.net_connections(kind='inet'):
            if conn.laddr.port == port:
                try:
                    process = psutil.Process(conn.pid)
                    process_name = process.name()
                    logger.info(f"Found process {conn.pid} ({process_name}) running on port {port}")
                    process.terminate()
                    try:
                        process.wait(timeout=3)
                        logger.info(f"Successfully terminated process {conn.pid}")
                    except psutil.TimeoutExpired:
                        logger.info(f"Process {conn.pid} did not terminate, sending SIGKILL")
                        process.kill()
                    time.sleep(1)  # Wait for process to terminate
                    return
                except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                    logger.warning(f"Could not terminate process: {e}")
    except (psutil.AccessDenied, psutil.Error) as e:
        logger.warning(f"Could not check port {port} with psutil: {e}")
    
    # Fallback to platform-specific commands
    try:
        if sys.platform.startswith('win'):
            # Windows-specific command
            output = subprocess.check_output(f'netstat -ano | findstr :{port}', shell=True).decode().strip()
            if output:
                pid = output.split()[-1]
                subprocess.run(['taskkill', '/F', '/PID', pid], check=True)
                logger.info(f"Killed process with PID {pid} on port {port} using taskkill")
        elif sys.platform.startswith('darwin'):
            # macOS-specific commands for PostgreSQL
            # First check if this is a PostgreSQL process
            try:
                output = subprocess.check_output(f"lsof -i :{port} | grep LISTEN", shell=True).decode().strip()
                if 'postgres' in output.lower():
                    logger.info(f"Found PostgreSQL process on port {port}")
                    # Try finding the PID of the PostgreSQL process
                    pid_output = subprocess.check_output(f"ps aux | grep postgres | grep {port}", shell=True).decode().strip()
                    pid_lines = pid_output.split('\n')
                    for line in pid_lines:
                        if 'grep' not in line and str(port) in line:
                            pid = line.split()[1]
                            logger.info(f"Sending SIGTERM to PostgreSQL process with PID {pid}")
                            subprocess.run(f"kill {pid}", shell=True, check=False)
                            time.sleep(2)
                            if not is_port_in_use(port):
                                logger.info(f"Successfully terminated PostgreSQL process on port {port}")
                                return
                            
                            logger.info(f"PostgreSQL process did not terminate, sending SIGKILL")
                            subprocess.run(f"kill -9 {pid}", shell=True, check=False)
                            time.sleep(1)
                            if not is_port_in_use(port):
                                logger.info(f"Successfully killed PostgreSQL process on port {port}")
                                return
            except subprocess.CalledProcessError:
                logger.info("No postgres process found via lsof")
            
            # Generic approach if the above didn't work
            try:
                subprocess.run(f"lsof -ti :{port} | xargs kill", shell=True, check=False)
                time.sleep(2)
                if not is_port_in_use(port):
                    logger.info(f"Successfully terminated process on port {port}")
                    return
                
                # If still running, use force kill
                subprocess.run(f"lsof -ti :{port} | xargs kill -9", shell=True, check=False)
                time.sleep(1)
                if not is_port_in_use(port):
                    logger.info(f"Successfully force-killed process on port {port}")
                    return
            except Exception as e:
                logger.warning(f"Error with lsof kill command: {e}")
        else:
            # Linux and other Unix-like systems
            try:
                subprocess.run(f"fuser -k {port}/tcp", shell=True, check=False)
                time.sleep(1)
                if not is_port_in_use(port):
                    logger.info(f"Successfully killed process on port {port} using fuser")
                    return
            except Exception:
                # Try lsof as alternative
                try:
                    subprocess.run(f"lsof -ti :{port} | xargs kill -9", shell=True, check=False)
                    time.sleep(1)
                    logger.info(f"Sent SIGKILL to process on port {port} using lsof")
                except Exception as e:
                    logger.warning(f"Error with lsof kill command: {e}")
    except Exception as e:
        logger.error(f"Error killing process on port {port}: {e}")
    
    # Verify if port is still in use
    if is_port_in_use(port):
        logger.warning(f"Port {port} is still in use after kill attempts")
    else:
        logger.info(f"Port {port} is now available")

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

def load_sample_tile_data():
    """Run the tile CSV uploader to load sample data"""
    logger.info("Loading sample tile data...")
    try:
        script_path = BASE_DIR / 'tile_csv_uploader.py'
        if not script_path.exists():
            logger.error(f"Tile CSV uploader script not found at {script_path}")
            return False
            
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            logger.error(f"Failed to load sample tile data: {result.stderr}")
            return False
            
        logger.info("Sample tile data loaded successfully")
        return True
    except Exception as e:
        logger.error(f"Error loading sample tile data: {e}")
        return False

def main():
    """Main function to start both servers"""
    # Store the current working directory
    original_cwd = os.getcwd()
    
    # Store processes to be terminated on exit
    processes_to_cleanup = []
    
    try:
        logger.info("Starting server launcher...")
        script_location = Path(sys.argv[0]).resolve()
        logger.info(f"Found server script at: {script_location}")
        
        # Ensure PostgreSQL instances are running
        logger.info("Starting main PostgreSQL server...")
        if not ensure_postgres_running():
            logger.error("Failed to start main PostgreSQL")
            sys.exit(1)
        
        logger.info("Starting tile analytics PostgreSQL server...")
        if not ensure_tile_postgres_running():
            logger.error("Failed to start tile PostgreSQL")
            sys.exit(1)
            
        # Load sample tile data
        if not load_sample_tile_data():
            logger.warning("Failed to load sample tile data, the tiles may not display proper information")
            
        # Kill any existing processes on both ports
        logger.info("Checking for existing processes on web ports...")
        kill_process_on_port(8000)  # Django port
        kill_process_on_port(8001)  # FastAPI port
        
        # Start FastAPI server
        logger.info("Starting FastAPI server...")
        fastapi_process = start_fastapi_server()
        if fastapi_process:
            processes_to_cleanup.append(('FastAPI', fastapi_process))
        else:
            logger.error("Failed to start FastAPI server")
            sys.exit(1)
        
        # Wait a moment for FastAPI to start
        time.sleep(2)
        
        # Application environment setup
        logger.info("Setting up Django environment...")
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
        
        # Apply migrations before other initializations
        logger.info("Applying database migrations...")
        if not apply_migrations():
            logger.error("Database migration failed")
            sys.exit(1)
        
        # Initialize required services
        logger.info("Verifying OpenAI API key...")
        if not verify_openai_key():
            logger.error("OpenAI API key verification failed")
            sys.exit(1)

        logger.info("Setting up pgvector extension...")
        if not setup_pgvector():
            logger.error("pgvector setup failed")
            sys.exit(1)
        
        logger.info("Collecting static files...")    
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
        if django_process:
            processes_to_cleanup.append(('Django', django_process))
        
        # Check if Django server started successfully
        time.sleep(2)
        if django_process.poll() is not None:
            stdout, stderr = django_process.communicate()
            logger.error(f"Django server failed to start. Exit code: {django_process.returncode}")
            logger.error(f"stdout: {stdout}")
            logger.error(f"stderr: {stderr}")
            sys.exit(1)
        
        # Verify Django server is available
        max_retries = 5
        for i in range(max_retries):
            if is_port_in_use(8000):
                logger.info("Django server started successfully")
                break
            logger.info(f"Waiting for Django server to start... ({i+1}/{max_retries})")
            time.sleep(1)
        else:
            logger.error("Django server not responding on port 8000")
            sys.exit(1)
            
        logger.info("All servers started successfully!")
        logger.info("Django server running at http://localhost:8000")
        logger.info("FastAPI server running at http://localhost:8001")
        
        # Wait for both processes
        try:
            while True:
                if fastapi_process.poll() is not None:
                    stdout, stderr = fastapi_process.communicate()
                    logger.error(f"FastAPI server stopped unexpectedly (exit code {fastapi_process.returncode})")
                    if stdout or stderr:
                        logger.error(f"FastAPI stdout: {stdout}")
                        logger.error(f"FastAPI stderr: {stderr}")
                    break
                if django_process.poll() is not None:
                    stdout, stderr = django_process.communicate()
                    logger.error(f"Django server stopped unexpectedly (exit code {django_process.returncode})")
                    if stdout or stderr:
                        logger.error(f"Django stdout: {stdout}")
                        logger.error(f"Django stderr: {stderr}")
                    break
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("\nShutting down servers...")
        
    except Exception as e:
        logger.error(f"Error starting servers: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
    finally:
        # Clean up all started processes
        for name, process in processes_to_cleanup:
            if process.poll() is None:  # If process is still running
                logger.info(f"Terminating {name} server...")
                try:
                    process.terminate()
                    process.wait(timeout=5)
                except (subprocess.TimeoutExpired, Exception) as e:
                    logger.warning(f"Error terminating {name} server gracefully: {e}")
                    try:
                        process.kill()
                    except Exception:
                        pass
        
        # Restore the original working directory
        os.chdir(original_cwd)
        
        logger.info("All servers shut down.")
        logger.info("Exiting...")

if __name__ == '__main__':
    main() 