#!/bin/bash

# Kill any existing processes on ports 8000 and 8001
kill_port() {
    local port=$1
    pid=$(lsof -ti:$port)
    if [ ! -z "$pid" ]; then
        echo "Killing process on port $port"
        kill -9 $pid
    fi
}

kill_port 8001

# Start FastAPI server
echo "Starting FastAPI server..."
cd "$(dirname "$0")"
python run.py &

# Wait for FastAPI server to start
echo "Waiting for FastAPI server to start..."
sleep 5

# Test FastAPI server
python test_server.py

echo "Servers should be running now"
echo "FastAPI: http://127.0.0.1:8001" 