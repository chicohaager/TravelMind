#!/bin/bash

echo "Stopping backend..."
sudo pkill -9 -f "uvicorn main:app"

sleep 2

echo "Starting backend..."
cd /home/holgi/dev/TravelMind/backend
sudo /usr/local/bin/python3.11 /usr/local/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --reload &

echo "Backend restarted!"
echo "Check logs at: sudo journalctl -u uvicorn -f"
