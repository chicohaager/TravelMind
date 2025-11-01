#!/bin/bash

# TravelMind Backend Startup Script

cd "$(dirname "$0")"

echo "🌍 Starting TravelMind Backend..."
echo

# Unset any environment variables that might override .env file
unset DATABASE_URL

# Activate virtual environment
source venv/bin/activate

# Navigate to backend directory
cd backend

# Start the server
python main.py
