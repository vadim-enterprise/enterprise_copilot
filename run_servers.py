import subprocess
import sys
import os
import time
import logging
import socket
import argparse
import django
from django.core.management import execute_from_command_line

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
REQUIRED_PORTS = [8000, 8001]
WAIT_TIME = 2  # seconds to wait for ports to be released
PROCESS_TIMEOUT = 3  # seconds to wait for process termination
MAX_PORT_CHECK_ATTEMPTS = 3
PORT_CHECK_TIMEOUT = 1  # seconds

def run_command(command, description):
    logger.info(f"\n=== {description} ===")
    try:
        result = subprocess.run(command, shell=True, check=True, text=True, capture_output=True)
        logger.info(f"Success: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error: {e.stderr}")
        return False
    
def force_kill_port(port: int) -> bool:
    """Force kill any process using the specified port"""
    try:
        if os.name == 'nt':  # Windows
            cmd = f"FOR /F \"tokens=5\" %P IN ('netstat -a -n -o | findstr :{port}') DO TaskKill /PID %P /F"
            subprocess.run(cmd, shell=True, stderr=subprocess.DEVNULL)
        else:  # Linux/Unix
            commands = [
                f"fuser -k {port}/tcp",
                f"pkill -f '.*:{port}.*'",
                f"kill -9 $(lsof -t -i:{port})"
            ]
            for cmd in commands:
                try:
                    subprocess.run(cmd, shell=True, stderr=subprocess.DEVNULL)
                except subprocess.CalledProcessError:
                    continue
        
        time.sleep(2)
        return not is_port_in_use(port)
    except Exception as e:
        logger.error(f"Error force killing port {port}: {str(e)}")
        return False

def get_process_details(port: int) -> str:
    """Get detailed information about processes using a port"""
    details = []
    try:
        if os.name == 'nt':  # Windows
            cmd = f"netstat -ano | findstr :{port}"
        else:  # Linux/Unix
            cmd = f"lsof -i :{port} && netstat -tulpn | grep :{port}"
        
        output = subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL)
        details.append(f"Port {port} usage details:\n{output}")
    except subprocess.CalledProcessError:
        details.append(f"No process details found for port {port}")
    return "\n".join(details)

def kill_process_on_port(port: int) -> bool:
    """Kill process running on specified port with enhanced error handling"""
    logger.info(f"Attempting to kill process on port {port}")
    logger.info(get_process_details(port))
    
    # First try graceful termination
    try:
        if os.name != 'nt':  # Linux/Unix
            subprocess.run(f"lsof -t -i:{port} | xargs kill -15", shell=True, stderr=subprocess.DEVNULL)
        time.sleep(2)
        
        if not is_port_in_use(port):
            return True
    except Exception:
        pass

    # If graceful termination failed, try force kill
    return force_kill_port(port)

def is_port_in_use(port: int) -> bool:
    """Check if a port is in use"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            result = s.connect_ex(('127.0.0.1', port))
            return result == 0
    except Exception as e:
        logger.error(f"Error checking port {port}: {str(e)}")
        return True

def free_required_ports() -> bool:
    """Free up required ports by killing existing processes"""
    max_attempts = 3
    
    for port in REQUIRED_PORTS:
        if is_port_in_use(port):
            logger.info(f"Port {port} is in use")
            logger.info(get_process_details(port))
            
            for attempt in range(max_attempts):
                logger.info(f"Attempt {attempt + 1}/{max_attempts} to free port {port}")
                
                if kill_process_on_port(port):
                    logger.info(f"Successfully freed port {port}")
                    break
                else:
                    if attempt == max_attempts - 1:
                        logger.error(f"Failed to free port {port} after {max_attempts} attempts")
                        return False
                    logger.warning(f"Port {port} still in use, trying again...")
                    time.sleep(2)
    
    # Final verification
    time.sleep(2)
    for port in REQUIRED_PORTS:
        if is_port_in_use(port):
            logger.error(f"Port {port} is still in use after all attempts")
            logger.error(get_process_details(port))
            return False
    
    logger.info("All ports successfully freed")
    return True

def collect_static():
    """Collect static files with better error handling"""
    try:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
        django.setup()
        
        logger.info("Collecting static files...")
        execute_from_command_line(['manage.py', 'collectstatic', '--noinput', '--clear'])
        return True
    except Exception as e:
        logger.error(f"Failed to collect static files: {e}")
        return False

def restart_gunicorn():
    commands = [
        "sudo systemctl restart gunicorn",
        "sudo systemctl status gunicorn"
    ]
    
    for cmd in commands:
        if not run_command(cmd, "Restarting Gunicorn"):
            return False
    return True

def restart_nginx():
    commands = [
        "sudo systemctl restart nginx",
        "sudo systemctl status nginx"
    ]
    
    for cmd in commands:
        if not run_command(cmd, "Restarting Nginx"):
            return False
    return True

def restart_fastapi():
    commands = [
        "sudo systemctl restart fastapi-transcription",
        "sudo systemctl status fastapi-transcription"
    ]
    
    for cmd in commands:
        if not run_command(cmd, "Restarting FastAPI service"):
            return False
    return True

def run_django():
    """Run Django development server"""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
    os.environ['DJANGO_ENV'] = 'development'
    
    # Use subprocess instead of direct execution
    try:
        return subprocess.Popen([
            sys.executable,
            "manage.py",
            "runserver",
            "0.0.0.0:8000"
        ])
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to start Django server: {e}")
        return None

def run_fastapi():
    subprocess.run([
        "uvicorn", 
        "predict_best_option.fastapi_app.main:app", 
        "--host", "127.0.0.1", 
        "--port", "8001",
        "--reload",
        "--log-level", "debug"
    ])

def deploy() -> bool:
    """Run full deployment process"""
    try:
        if not free_required_ports():
            logger.error("Failed to free required ports before deployment")
            return False

        steps = [
            ("Collecting static files", collect_static),
            ("Restarting Gunicorn", restart_gunicorn),
            ("Restarting Nginx", restart_nginx),
            ("Restarting FastAPI", restart_fastapi)
        ]

        for description, step in steps:
            logger.info(f"\n=== {description} ===")
            if not step():
                logger.error(f"\nError during {description}. Stopping deployment.")
                return False
            logger.info(f"{description} completed successfully.")

        logger.info("\n=== Deployment completed successfully! ===")
        return True
        
    except Exception as e:
        logger.error(f"Error during deployment: {str(e)}")
        return False

def kill_ports():
    """Kill processes on both required ports with verification"""
    def is_port_free(port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('127.0.0.1', port))
                s.close()
                return True
            except:
                return False

    for port in REQUIRED_PORTS:
        if not is_port_free(port):
            logger.info(f"Port {port} is in use, attempting to kill...")
            try:
                if os.name == 'nt':  # Windows
                    # Get process ID using subprocess instead of temporary file
                    cmd = f'netstat -ano | findstr :{port} | findstr LISTENING'
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                    
                    if result.stdout:
                        # Extract PID from the last column of netstat output
                        pid = result.stdout.strip().split()[-1]
                        subprocess.run(f'taskkill /F /PID {pid}', shell=True)
                else:  # Unix/Linux/MacOS
                    subprocess.run(f'lsof -ti:{port} | xargs kill -9', shell=True)
                
                time.sleep(2)  # Wait for port to be freed
                if not is_port_free(port):
                    logger.error(f"Failed to free port {port}")
                    return False
            except Exception as e:
                logger.error(f"Error killing process on port {port}: {e}")
                return False
    return True

def development():
    """Run development servers"""
    try:
        # Kill existing processes first
        if not kill_ports():
            logger.error("Failed to free required ports")
            sys.exit(1)
            
        # Set development environment
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
        os.environ['DJANGO_ENV'] = 'development'
        
        # Start Django server with error checking
        django_process = subprocess.Popen([
            sys.executable,
            "manage.py",
            "runserver",
            "0.0.0.0:8000"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Check if Django server started successfully
        time.sleep(2)
        if django_process.poll() is not None:
            _, error = django_process.communicate()
            logger.error(f"Django server failed to start: {error.decode()}")
            sys.exit(1)
            
        logger.info("Django server started successfully")
        
        # Continue with FastAPI server...
        
        # Start FastAPI server
        fastapi_process = subprocess.Popen([
            "uvicorn",
            "predict_best_option.fastapi_app.main:app",
            "--host", "127.0.0.1",
            "--port", "8001",
            "--reload"
        ])
        
        logger.info("Development servers started successfully")
        
        try:
            # Keep the script running
            while True:
                time.sleep(1)
                # Check if either process has terminated
                if django_process.poll() is not None or fastapi_process.poll() is not None:
                    logger.error("One of the servers has terminated unexpectedly")
                    raise Exception("Server terminated")
        except KeyboardInterrupt:
            logger.info("Shutting down servers...")
        finally:
            # Clean up processes
            for process in [django_process, fastapi_process]:
                if process and process.poll() is None:
                    process.terminate()
                    process.wait(timeout=5)
            
    except Exception as e:
        logger.error(f"Error in development mode: {e}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run servers or deploy application')
    parser.add_argument('--mode', choices=['dev', 'deploy'], default='dev',
                      help='Run in development mode or deploy to production')
    parser.add_argument('--step', choices=['static', 'gunicorn', 'nginx', 'fastapi', 'all'],
                      default='all', help='Specify which deployment step to run')
    
    args = parser.parse_args()
    
    try:
        if args.mode == 'deploy':
            if args.step == 'all':
                deploy()
            elif args.step == 'static':
                collect_static()
            elif args.step == 'gunicorn':
                restart_gunicorn()
            elif args.step == 'nginx':
                restart_nginx()
            elif args.step == 'fastapi':
                restart_fastapi()
        else:
            development()
    except KeyboardInterrupt:
        logger.info("\nShutting down gracefully...")
        sys.exit(0)