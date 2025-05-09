from fastapi import APIRouter, HTTPException
import psycopg2
from psycopg2.extras import RealDictCursor
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

def get_db_connection():
    try:
        logger.info("Attempting to connect to PostgreSQL database...")
        conn = psycopg2.connect(
            host="localhost",
            port=5541,
            database="tile_analytics",
            user="glinskiyvadim"
        )
        logger.info("Successfully connected to PostgreSQL database")
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to PostgreSQL database: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database connection error: {str(e)}")

@router.get("/tiles")
async def get_tiles():
    try:
        logger.info("Fetching tiles from database...")
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # First, check if the table exists
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'tile_data'
            );
        """)
        table_exists = cur.fetchone()['exists']
        
        if not table_exists:
            logger.error("tile_data table does not exist")
            raise HTTPException(status_code=404, detail="tile_data table not found")
        
        # Get the data
        cur.execute("SELECT * FROM tile_data ORDER BY id")
        tiles = cur.fetchall()
        logger.info(f"Successfully fetched {len(tiles)} tiles")
        
        cur.close()
        conn.close()
        
        return {"tiles": [dict(tile) for tile in tiles]}
    except psycopg2.Error as e:
        logger.error(f"PostgreSQL error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 