import psycopg2
from psycopg2.extras import RealDictCursor
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_db_connection():
    try:
        logger.info("Attempting to connect to PostgreSQL database...")
        conn = psycopg2.connect(
            host="localhost",
            port=5541,
            database="tile_analytics",
            user="glinskiyvadim"
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
            return False
            
        # Try to fetch some data
        cur.execute("SELECT * FROM tile_data ORDER BY id")
        tiles = cur.fetchall()
        logger.info(f"Successfully fetched {len(tiles)} tiles")
        
        # Print the first tile as a sample
        if tiles:
            logger.info(f"Sample tile data: {dict(tiles[0])}")
        
        cur.close()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_db_connection()
    if success:
        logger.info("Database connection test passed!")
    else:
        logger.error("Database connection test failed!") 