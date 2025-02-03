#!/bin/bash
# Make sure the script is executable: chmod +x start.sh

# Make the script executable
chmod +x "$(dirname "$0")/start.sh"

# Kill any existing process on port 8001
pid=$(lsof -ti:8001)
if [ ! -z "$pid" ]; then
    echo "Killing existing process on port 8001"
    kill -9 $pid
fi

# Activate virtual environment if it exists
if [ -f "../../../django_venv/bin/activate" ]; then
    source "../../../django_venv/bin/activate"
fi

# Check for OPENAI_API_KEY in environment
if [ -z "$OPENAI_API_KEY" ]; then
    echo "Error: OPENAI_API_KEY environment variable is not set"
    echo "Please set your OpenAI API key:"
    echo "export OPENAI_API_KEY=your_api_key_here"
    exit 1
fi

# Set the PYTHONPATH
export PYTHONPATH="$(dirname "$0")/../..:$PYTHONPATH"

# Start the FastAPI server
echo "Starting FastAPI server..."
cd "$(dirname "$0")"
python run.py 