#!/bin/bash

# Startup script for Municipal Multi-Agent System UI

echo "Starting Municipal Multi-Agent System..."
echo ""

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Start Flask backend in background
echo "Starting Flask backend on port 5000..."
python app.py &
FLASK_PID=$!

# Wait a moment for Flask to start
sleep 3

# Start React frontend
echo "Starting React frontend on port 3000..."
cd frontend
npm start

# Cleanup on exit
trap "kill $FLASK_PID" EXIT

