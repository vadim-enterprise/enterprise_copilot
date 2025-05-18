from fastapi import APIRouter, HTTPException
import psycopg2
import os
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
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT'),
            database=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER')
        )
        logger.info("Successfully connected to PostgreSQL database")
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to PostgreSQL database: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database connection error: {str(e)}")

@router.get("/api/tiles")
async def get_tiles():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # First check if the table exists
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'tile_analytics'
            );
        """)
        table_exists = cur.fetchone()['exists']
        
        if not table_exists:
            logger.error("tile_analytics table does not exist")
            raise HTTPException(status_code=404, detail="tile_analytics table not found")
        
        # Get the data from tile_analytics table
        cur.execute("""
            SELECT 
                name as tile_name,
                CASE 
                    WHEN color = 'red' THEN 'Alert'
                    WHEN color = 'green' THEN 'Good News'
                    WHEN color = 'yellow' THEN 'Warning'
                    ELSE 'Info'
                END as notification_type,
                title as motion,
                name as customer,
                description as issue,
                created_at,
                updated_at
            FROM tile_analytics 
            ORDER BY created_at DESC
        """)
        tiles = cur.fetchall()
        
        cur.close()
        conn.close()
        
        logger.info(f"Successfully fetched {len(tiles)} tiles from tile_analytics table")
        return {"tiles": [dict(tile) for tile in tiles]}
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 