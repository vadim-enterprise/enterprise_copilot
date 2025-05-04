import os
from pathlib import Path
from dotenv import load_dotenv

def load_env_variables():
    """
    Load environment variables from .env file
    """
    # Get the project root directory
    project_root = Path(__file__).resolve().parent.parent.parent.parent
    
    # Load .env file from project root
    env_path = project_root / '.env'
    
    if env_path.exists():
        load_dotenv(env_path)
        print(f"Loaded environment variables from {env_path}")
    else:
        print(f"No .env file found at {env_path}")
    
    return True