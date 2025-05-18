import os
from sqlalchemy import create_engine, text, inspect
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_database_url():
    """Get database URL from environment variables with defaults"""
    host = os.getenv('DB_HOST', 'localhost')
    port = os.getenv('DB_PORT', '5540')  # Default port is 5540
    database = os.getenv('DB_NAME', 'pred_genai')  # Default database is pred_genai
    user = os.getenv('DB_USER', 'glinskiyvadim')
    
    return f"postgresql://{user}@{host}:{port}/{database}"

def print_database_content():
    """Print database content using SQLAlchemy"""
    try:
        # Create engine using environment variables
        engine = create_engine(get_database_url())
        
        # Get all table names
        inspector = inspect(engine)
        table_names = inspector.get_table_names()
        
        if not table_names:
            logger.info("No tables found in the database")
            return
        
        print("\n=== Database Tables ===")
        for table_name in table_names:
            print(f"\nTable: {table_name}")
            print("-" * 50)
            
            # Get column information
            columns = inspector.get_columns(table_name)
            print("Columns:")
            for col in columns:
                print(f"  - {col['name']} ({col['type']})")
            
            # Get sample data
            try:
                with engine.connect() as conn:
                    result = conn.execute(text(f"SELECT * FROM {table_name} LIMIT 5"))
                    rows = result.fetchall()
                    
                    if rows:
                        print("\nSample Data:")
                        df = pd.DataFrame(rows)
                        print(df)
                    else:
                        print("\nNo data in table")
            except Exception as e:
                print(f"Error reading table {table_name}: {str(e)}")
            
            print("\n" + "="*50)
    except Exception as e:
        logger.error(f"Error in print_database_content: {str(e)}")
        logger.error("Please ensure your database environment variables are set correctly:")
        logger.error("DB_HOST (default: localhost)")
        logger.error("DB_PORT (default: 5540)")
        logger.error("DB_NAME (default: pred_genai)")
        logger.error("DB_USER (default: glinskiyvadim)")

def print_db_content():
    """Print database content using psycopg2"""
    try:
        logger.info("Attempting to connect to PostgreSQL database...")
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT'),
            database=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER')
        )
        logger.info("Successfully connected to PostgreSQL database")
            
        # Test if we can query the table
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Check if table exists
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'tile_data'
            );
        """)
        table_exists = cur.fetchone()['exists']
        
        if not table_exists:
            logger.error("tile_data table does not exist")
            return
            
        # Try to fetch some data
        cur.execute("SELECT * FROM tile_data ORDER BY id")
        tiles = cur.fetchall()
        logger.info(f"Successfully fetched {len(tiles)} tiles")
            
        # Print all tiles
        for tile in tiles:
            logger.info(f"Tile data: {dict(tile)}")
        
        cur.close()
        conn.close()
            
    except Exception as e:
        logger.error(f"Error: {str(e)}")

if __name__ == "__main__":
    print_database_content() 