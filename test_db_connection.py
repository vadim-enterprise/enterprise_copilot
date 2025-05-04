import os
from sqlalchemy import create_engine, text
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database connection
DATABASE_URL = 'postgresql://glinskiyvadim@localhost:5540/pred_genai'
engine = create_engine(DATABASE_URL)

def test_connection():
    try:
        # Test basic connection
        with engine.connect() as conn:
            logger.info("Successfully connected to database")
            
            # Test if we can create a table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS test_table (
                    id SERIAL PRIMARY KEY,
                    test_column VARCHAR(255)
                )
            """))
            logger.info("Successfully created test table")
            
            # Test if we can insert data
            conn.execute(text("""
                INSERT INTO test_table (test_column) VALUES ('test_value')
            """))
            logger.info("Successfully inserted test data")
            
            # Test if we can read data
            result = conn.execute(text("SELECT * FROM test_table"))
            rows = result.fetchall()
            logger.info(f"Successfully read test data: {rows}")
            
            # Clean up
            conn.execute(text("DROP TABLE test_table"))
            logger.info("Successfully cleaned up test table")
            
            return True
            
    except Exception as e:
        logger.error(f"Database connection test failed: {str(e)}")
        return False

if __name__ == "__main__":
    test_connection() 