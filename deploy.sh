#!/bin/bash
#
# TravelMind Production Deployment Script
#
# Usage:
#   ./deploy.sh                  # Deploy/update
#   ./deploy.sh --build          # Force rebuild images
#   ./deploy.sh --down           # Stop all services
#   ./deploy.sh --logs           # View logs
#   ./deploy.sh --status         # Check status
#   ./deploy.sh --backup         # Create database backup
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="docker-compose.prod.yml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check requirements
check_requirements() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose is not installed"
        exit 1
    fi
}

# Check environment
check_env() {
    if [ ! -f "$SCRIPT_DIR/.env" ]; then
        log_error ".env file not found!"
        log_info "Copy .env.example to .env and configure it:"
        log_info "  cp .env.example .env"
        log_info "  nano .env"
        exit 1
    fi
    
    # Check required variables
    source "$SCRIPT_DIR/.env"
    
    if [ -z "$JWT_SECRET" ] || [ "$JWT_SECRET" = "your-super-secret-jwt-key-change-this-in-production" ]; then
        log_error "JWT_SECRET is not configured!"
        log_info "Generate one with: python3 -c \"import secrets; print(secrets.token_urlsafe(32))\""
        exit 1
    fi
    
    if [ -z "$SECRET_KEY" ] || [ "$SECRET_KEY" = "default-secret-key-change-this" ]; then
        log_error "SECRET_KEY is not configured!"
        log_info "Generate one with: python3 -c \"import secrets; print(secrets.token_urlsafe(32))\""
        exit 1
    fi
    
    if [ -z "$POSTGRES_PASSWORD" ]; then
        log_error "POSTGRES_PASSWORD is not configured!"
        exit 1
    fi
    
    log_info "Environment check passed"
}

# Docker Compose command (supports both v1 and v2)
docker_compose() {
    if docker compose version &> /dev/null 2>&1; then
        docker compose -f "$SCRIPT_DIR/$COMPOSE_FILE" "$@"
    else
        docker-compose -f "$SCRIPT_DIR/$COMPOSE_FILE" "$@"
    fi
}

# Deploy or update
deploy() {
    log_info "Starting TravelMind deployment..."
    
    cd "$SCRIPT_DIR"
    
    # Pull latest images
    log_info "Pulling latest base images..."
    docker_compose pull db redis 2>/dev/null || true
    
    # Build application images
    if [ "$1" = "--build" ]; then
        log_info "Building images (forced rebuild)..."
        docker_compose build --no-cache
    else
        log_info "Building images..."
        docker_compose build
    fi
    
    # Start services
    log_info "Starting services..."
    docker_compose up -d
    
    # Wait for health checks
    log_info "Waiting for services to be healthy..."
    sleep 10
    
    # Check status
    docker_compose ps
    
    log_info "Deployment complete!"
    log_info "Frontend: http://localhost (or your configured domain)"
    log_info "API Docs: http://localhost/api/docs"
}

# Stop all services
stop() {
    log_info "Stopping TravelMind services..."
    docker_compose down
    log_info "Services stopped"
}

# View logs
logs() {
    docker_compose logs -f "$@"
}

# Check status
status() {
    log_info "TravelMind Service Status:"
    docker_compose ps
    
    echo ""
    log_info "Health Checks:"
    
    # Check backend health
    if curl -s http://localhost:8000/api/health/live > /dev/null 2>&1; then
        echo -e "  Backend: ${GREEN}healthy${NC}"
    else
        echo -e "  Backend: ${RED}unhealthy${NC}"
    fi
    
    # Check frontend health
    if curl -s http://localhost/health > /dev/null 2>&1; then
        echo -e "  Frontend: ${GREEN}healthy${NC}"
    else
        echo -e "  Frontend: ${RED}unhealthy${NC}"
    fi
}

# Create backup
backup() {
    log_info "Creating database backup..."
    
    BACKUP_FILE="backup_$(date +%Y%m%d_%H%M%S).sql"
    
    docker_compose exec -T db pg_dump -U "${POSTGRES_USER:-travelmind}" "${POSTGRES_DB:-travelmind}" > "$SCRIPT_DIR/backups/$BACKUP_FILE"
    
    if [ -f "$SCRIPT_DIR/backups/$BACKUP_FILE" ]; then
        log_info "Backup created: backups/$BACKUP_FILE"
        ls -lh "$SCRIPT_DIR/backups/$BACKUP_FILE"
    else
        log_error "Backup failed!"
        exit 1
    fi
}

# Main
main() {
    check_requirements
    
    case "${1:-}" in
        --build)
            check_env
            deploy --build
            ;;
        --down|--stop)
            stop
            ;;
        --logs)
            shift
            logs "$@"
            ;;
        --status)
            status
            ;;
        --backup)
            backup
            ;;
        --help|-h)
            echo "TravelMind Deployment Script"
            echo ""
            echo "Usage: $0 [OPTION]"
            echo ""
            echo "Options:"
            echo "  --build     Force rebuild of Docker images"
            echo "  --down      Stop all services"
            echo "  --logs      View service logs (add service name for specific logs)"
            echo "  --status    Check service status"
            echo "  --backup    Create database backup"
            echo "  --help      Show this help"
            echo ""
            echo "Without options: Deploy or update TravelMind"
            ;;
        *)
            check_env
            deploy
            ;;
    esac
}

main "$@"
