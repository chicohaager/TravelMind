#!/bin/bash

# TravelMind - Build Docker Images for Docker Hub
# Usage: ./build-docker-images.sh [version]

set -e

VERSION=${1:-latest}
DOCKER_USER="chicohaager"
IMAGE_PREFIX="${DOCKER_USER}/travelmind"

echo "================================"
echo "Building TravelMind Docker Images"
echo "Version: $VERSION"
echo "================================"
echo ""

# Build Backend Image
echo "📦 Building Backend Image..."
docker build \
  -t ${IMAGE_PREFIX}-backend:${VERSION} \
  -t ${IMAGE_PREFIX}-backend:latest \
  -f backend/Dockerfile.prod \
  backend/

echo "✅ Backend image built: ${IMAGE_PREFIX}-backend:${VERSION}"
echo ""

# Build Frontend Image
echo "📦 Building Frontend Image..."
docker build \
  -t ${IMAGE_PREFIX}-frontend:${VERSION} \
  -t ${IMAGE_PREFIX}-frontend:latest \
  --build-arg VITE_API_URL=http://localhost:8000 \
  -f frontend/Dockerfile.prod \
  frontend/

echo "✅ Frontend image built: ${IMAGE_PREFIX}-frontend:${VERSION}"
echo ""

echo "================================"
echo "✅ All images built successfully!"
echo "================================"
echo ""
echo "Images created:"
echo "  - ${IMAGE_PREFIX}-backend:${VERSION}"
echo "  - ${IMAGE_PREFIX}-backend:latest"
echo "  - ${IMAGE_PREFIX}-frontend:${VERSION}"
echo "  - ${IMAGE_PREFIX}-frontend:latest"
echo ""
echo "To push to Docker Hub, run:"
echo "  ./push-docker-images.sh $VERSION"
echo ""
