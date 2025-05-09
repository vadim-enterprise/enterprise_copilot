import os
from sqlalchemy import create_engine, text, inspect
import pandas as pd

# Database connection
DATABASE_URL = 'postgresql://glinskiyvadim@localhost:5541/tile_analytics'
engine = create_engine(DATABASE_URL)

def print_database_content():
    # Get all table names
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    
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

if __name__ == "__main__":
    print_database_content() 