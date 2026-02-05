#!/bin/bash
# Start script for Falsifi

cd "$(dirname "$0")"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate and install dependencies
source venv/bin/activate
pip install -q -r requirements.txt

# Start the server
echo "Starting Falsifi on http://localhost:5000"
python app.py