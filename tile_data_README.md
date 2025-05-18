# Tile Data Management for PostgreSQL on Port 5541

This document explains how to use the tile data functionality, which allows you to store data in the `tile_data` table in PostgreSQL on port 5541.

## Table Schema

The `tile_data` table has the following schema:

```sql
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
```

## Methods to Add or Update Tile Data

### 1. Using the Websearch Bar

You can add or update tile data directly by using the websearch bar with natural language. Include the keyword "tile data" or "save tile" in your query and make sure to specify at least the "tile_name" field:

Examples:
- "Create a new tile with tile_name 'Server Status', notification_type 'Warning', motion 'Increasing', customer 'IT Department', issue 'Server load high'"
- "Update tile data with tile_name 'System Health' and change issue to 'System operating at reduced capacity'"

The system will use AI to extract the structured data from your query and store it in the PostgreSQL database.

### 2. Using the CSV Upload Endpoint

For bulk operations, you can upload a CSV file with tile data using the `/api/files/upload-tile-csv` endpoint:

```bash
curl -X POST "http://localhost:8000/api/files/upload-tile-csv" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@example_tiles.csv"
```

The CSV file must include at least the `tile_name` column and can include any of the other columns from the schema: `notification_type`, `motion`, `customer`, and `issue`.

## Example CSV Format

Here's an example of a valid CSV file format:

```csv
tile_name,notification_type,motion,customer,issue
Abnormal Price Spike,Alert,Increasing,Energy Corp,Unexpected energy price spike detected in market
System Maintenance,Info,Steady,All Users,Scheduled system maintenance tonight from 2-4 AM
Server Load Warning,Warning,Increasing,Internal,High server load detected on production cluster
```

## Implementation Details

- If a tile with the same `tile_name` already exists, it will be updated with the new values
- Only the fields specified in your request will be updated; other fields will remain unchanged
- The `created_at` field is set when a record is first created
- The `updated_at` field is updated whenever the record is modified

## Error Handling

- If you try to add tile data without specifying a `tile_name`, the operation will fail
- Any fields not matching the schema will be ignored
- In case of a database error, the operation will be rolled back 