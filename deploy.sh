#!/bin/bash

# TravelMind Deployment Script
# This script deploys the TravelMind application in production mode

set -e  # Exit on error

echo "================================"
echo "TravelMind Deployment Script"
echo "================================"
echo ""

# Check if .env.prod exists
if [ ! -f ".env.prod" ]; then
    echo "❌ Error: .env.prod file not found!"
    echo "Please create .env.prod with your production configuration."
    echo "See .env.example for reference."
    exit 1
fi

# Load environment variables
export $(cat .env.prod | xargs)

# Confirm deployment
read -p "⚠️  Deploy to production? This will rebuild and restart all containers. (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled."
    exit 0
fi

echo ""
echo "📦 Building production images..."
docker-compose -f docker-compose.prod.yml build --no-cache

echo ""
echo "🔄 Stopping existing containers..."
docker-compose -f docker-compose.prod.yml down

echo ""
echo "🚀 Starting production containers..."
docker-compose -f docker-compose.prod.yml up -d

echo ""
echo "⏳ Waiting for services to be ready..."
sleep 10

echo ""
echo "🔍 Checking service status..."
docker-compose -f docker-compose.prod.yml ps

echo ""
echo "✅ Deployment complete!"
echo ""
echo "Services running at:"
echo "  - Backend:  http://localhost:8000"
echo "  - Frontend: http://localhost (port 80)"
echo "  - Database: localhost:5432"
echo ""
echo "To view logs:"
echo "  docker-compose -f docker-compose.prod.yml logs -f"
echo ""
echo "To create admin user:"
echo "  docker exec -it travelmind-backend-prod python create_admin.py"
echo ""
