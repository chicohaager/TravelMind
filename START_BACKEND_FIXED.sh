#!/bin/bash

# TravelMind Backend Startup Script (with all fixes applied)
# This script starts the backend with the correct DATABASE_URL

cd "$(dirname "$0")"

# Unset any existing environment variables to ensure .env file is used
unset JWT_SECRET
unset SECRET_KEY

# Export DATABASE_URL to ensure SQLite is used
export DATABASE_URL="sqlite:////home/holgi/dev/TravelMind/data/travelmind.db"

# Activate virtual environment
source venv/bin/activate

# Change to backend directory so .env is loaded correctly
cd backend

# Start backend
echo "Starting TravelMind Backend..."
echo "DATABASE_URL: $DATABASE_URL"
python main.py
