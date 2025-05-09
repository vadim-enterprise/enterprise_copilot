import subprocess
import logging
import time
from pathlib import Path
import sys

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_table_exists(table_name):
    """Check if a table exists in the database"""
    try:
        result = subprocess.run([
            'psql',
            '-h', 'localhost',
            '-p', '5541',
            'tile_analytics',
            '-t',  # tuple only output
            '-c', f"SELECT EXISTS (SELECT FROM pg_tables WHERE tablename = '{table_name}');"
        ], check=True, capture_output=True, text=True)
        return result.stdout.strip() == 't'
    except subprocess.CalledProcessError:
        return False

def ensure_tile_data_table():
    """Ensure the tile_data table exists with proper constraints"""
    try:
        # Drop the table if it exists to ensure clean state
        subprocess.run([
            'psql',
            '-h', 'localhost',
            '-p', '5541',
            'tile_analytics',
            '-c', "DROP TABLE IF EXISTS tile_data CASCADE;"
        ], check=True, capture_output=True)
        
        # Create the table with proper constraints
        subprocess.run([
            'psql',
            '-h', 'localhost',
            '-p', '5541',
            'tile_analytics',
            '-c', """
            CREATE TABLE tile_data (
                id SERIAL PRIMARY KEY,
                tile_name VARCHAR(100) NOT NULL UNIQUE,
                notification_type TEXT,
                motion TEXT,
                customer TEXT,
                issue TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
            """
        ], check=True, capture_output=True)
        
        # Verify the table was created with the constraint
        result = subprocess.run([
            'psql',
            '-h', 'localhost',
            '-p', '5541',
            'tile_analytics',
            '-t',  # tuple only output
            '-c', """
            SELECT EXISTS (
                SELECT 1 
                FROM pg_constraint 
                WHERE conrelid = 'tile_data'::regclass 
                AND conname = 'tile_data_tile_name_key'
            );
            """
        ], check=True, capture_output=True, text=True)
        
        if result.stdout.strip() != 't':
            logger.error("Failed to create unique constraint on tile_name")
            return False
            
        logger.info("Successfully created tile_data table with proper constraints")
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Error ensuring tile_data table: {e.stderr.decode()}")
        return False

def upload_csv_to_tile_db():
    """Upload example_tiles.csv data to the tile PostgreSQL instance
    
    Returns:
        bool: True if upload was successful, False otherwise
    """
    try:
        csv_file_path = Path('example_tiles.csv')
        if not csv_file_path.exists():
            logger.error(f"Error: File {csv_file_path} does not exist")
            return False
            
        logger.info(f"Uploading {csv_file_path} to tile database...")
        
        # Ensure tile_data table exists with proper constraints
        if not ensure_tile_data_table():
            logger.error("Failed to ensure tile_data table exists with proper constraints")
            return False
        
        # Create a temporary staging table for the CSV data
        staging_table = f"staging_tiles_{int(time.time())}"
        
        # First, ensure any existing staging table is dropped
        try:
            subprocess.run([
                'psql',
                '-h', 'localhost',
                '-p', '5541',
                'tile_analytics',
                '-c', f"DROP TABLE IF EXISTS {staging_table};"
            ], check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            logger.warning(f"Warning: Could not drop existing staging table: {e.stderr.decode()}")
        
        # Create temporary table with the same structure as tile_data
        logger.info(f"Creating staging table {staging_table}...")
        subprocess.run([
            'psql',
            '-h', 'localhost',
            '-p', '5541',
            'tile_analytics',
            '-c', f"""
            CREATE TABLE {staging_table} (
                id SERIAL PRIMARY KEY,
                tile_name VARCHAR(100) NOT NULL,
                notification_type TEXT,
                motion TEXT,
                customer TEXT,
                issue TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
            """
        ], check=True, capture_output=True)
        
        # Verify the table was created
        if not check_table_exists(staging_table):
            logger.error(f"Failed to create staging table {staging_table}")
            return False
            
        logger.info("Staging table created successfully")
        
        # Copy data from example_tiles.csv to the staging table
        logger.info("Copying data from CSV to staging table...")
        subprocess.run([
            'psql',
            '-h', 'localhost',
            '-p', '5541',
            'tile_analytics',
            '-c', f"\\COPY {staging_table} (tile_name, notification_type, motion, customer, issue) FROM '{csv_file_path}' WITH CSV HEADER;"
        ], check=True, capture_output=True)
        
        # Update existing records and insert new ones from the staging table
        logger.info("Updating main table with data from staging table...")
        subprocess.run([
            'psql',
            '-h', 'localhost',
            '-p', '5541',
            'tile_analytics',
            '-c', f"""
            INSERT INTO tile_data (tile_name, notification_type, motion, customer, issue)
            SELECT t.tile_name, t.notification_type, t.motion, t.customer, t.issue
            FROM {staging_table} t
            ON CONFLICT (tile_name) DO UPDATE
            SET 
                notification_type = EXCLUDED.notification_type,
                motion = EXCLUDED.motion,
                customer = EXCLUDED.customer,
                issue = EXCLUDED.issue,
                updated_at = CURRENT_TIMESTAMP;
            """
        ], check=True, capture_output=True)
        
        # Clean up: Drop the staging table
        logger.info("Cleaning up staging table...")
        subprocess.run([
            'psql',
            '-h', 'localhost',
            '-p', '5541',
            'tile_analytics',
            '-c', f"DROP TABLE IF EXISTS {staging_table};"
        ], check=True, capture_output=True)
        
        logger.info("CSV data successfully uploaded to tile database")
        return True
            
    except subprocess.CalledProcessError as e:
        logger.error(f"Error uploading CSV to tile database: {e.stderr.decode()}")
        return False
    except Exception as e:
        logger.error(f"Error processing CSV file: {e}")
        return False

if __name__ == "__main__":
    success = upload_csv_to_tile_db()
    if success:
        print("CSV uploaded successfully")
        sys.exit(0)
    else:
        print("Failed to upload CSV")
        sys.exit(1) 