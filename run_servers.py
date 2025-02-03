#!/usr/bin/env python3
import os
import sys
from pathlib import Path

# Print immediate status
print("Starting server launcher...", flush=True)

# Get the directory containing this script
script_dir = Path(__file__).resolve().parent

# Check if server_script.py exists
server_script = script_dir / 'server_script.py'
if not server_script.exists():
    print(f"Error: {server_script} not found!", flush=True)
    sys.exit(1)

print(f"Found server script at: {server_script}", flush=True)

# Run the server script with unbuffered output
cmd = [sys.executable, '-u', str(server_script)]
os.execv(sys.executable, cmd) 