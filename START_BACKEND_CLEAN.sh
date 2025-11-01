#!/bin/bash

# TravelMind Backend Startup Script (Clean Environment)
# This script ensures no conflicting environment variables

cd "$(dirname "$0")"

echo "🌍 Starting TravelMind Backend (Clean Environment)..."
echo ""
echo "🔍 Checking environment..."

# Unset any conflicting environment variables
unset DATABASE_URL
echo "  ✓ Cleared DATABASE_URL from environment"

# Check if data directory exists
if [ ! -d "data" ]; then
    echo "  ✓ Creating data directory..."
    mkdir -p data
fi

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "  ❌ Error: Virtual environment not found!"
    echo "  Please run: python3 -m venv venv"
    exit 1
fi

echo "  ✓ Virtual environment found"

# Activate virtual environment
source venv/bin/activate

echo "  ✓ Virtual environment activated"
echo ""
echo "🚀 Starting backend on port 8001..."
echo "   Press Ctrl+C to stop"
echo ""

# Navigate to backend directory and start
cd backend
exec python main.py
