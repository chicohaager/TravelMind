#!/bin/bash

# TravelMind - Push Docker Images to Docker Hub
# Usage: ./push-docker-images.sh [version]

set -e

VERSION=${1:-latest}
DOCKER_USER="chicohaager"
IMAGE_PREFIX="${DOCKER_USER}/travelmind"

echo "================================"
echo "Pushing TravelMind Docker Images"
echo "Version: $VERSION"
echo "================================"
echo ""

# Check if logged in to Docker Hub
if ! docker info | grep -q "Username: ${DOCKER_USER}"; then
    echo "⚠️  Not logged in to Docker Hub"
    echo "Please run: docker login"
    exit 1
fi

# Push Backend Images
echo "📤 Pushing Backend Images..."
docker push ${IMAGE_PREFIX}-backend:${VERSION}
if [ "$VERSION" != "latest" ]; then
    docker push ${IMAGE_PREFIX}-backend:latest
fi
echo "✅ Backend images pushed"
echo ""

# Push Frontend Images
echo "📤 Pushing Frontend Images..."
docker push ${IMAGE_PREFIX}-frontend:${VERSION}
if [ "$VERSION" != "latest" ]; then
    docker push ${IMAGE_PREFIX}-frontend:latest
fi
echo "✅ Frontend images pushed"
echo ""

echo "================================"
echo "✅ All images pushed successfully!"
echo "================================"
echo ""
echo "Images available on Docker Hub:"
echo "  - https://hub.docker.com/r/${DOCKER_USER}/travelmind-backend"
echo "  - https://hub.docker.com/r/${DOCKER_USER}/travelmind-frontend"
echo ""
echo "Users can now deploy with:"
echo "  docker-compose -f docker-compose.hub.yml up -d"
echo ""
