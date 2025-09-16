#!/bin/bash

# Production Deployment Script for Poker Analytics
# Usage: ./scripts/deploy.sh [environment]

set -e  # Exit on any error

ENVIRONMENT=${1:-production}
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_FILE="$PROJECT_ROOT/logs/deploy-$(date +%Y%m%d-%H%M%S).log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
    exit 1
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

# Create logs directory
mkdir -p "$PROJECT_ROOT/logs"

log "Starting deployment for environment: $ENVIRONMENT"

# Check if environment file exists
ENV_FILE="$PROJECT_ROOT/.env.$ENVIRONMENT"
if [ ! -f "$ENV_FILE" ]; then
    error "Environment file $ENV_FILE not found!"
fi

log "Environment file found: $ENV_FILE"

# Pre-deployment checks
log "Running pre-deployment checks..."

# Check Docker
if ! command -v docker &> /dev/null; then
    error "Docker is not installed or not in PATH"
fi

# Check Docker Compose
if ! command -v docker-compose &> /dev/null; then
    error "Docker Compose is not installed or not in PATH"
fi

# Check required environment variables
log "Validating environment variables..."
source "$ENV_FILE"

REQUIRED_VARS=("POSTGRES_USER" "POSTGRES_PASSWORD" "POSTGRES_DB" "ALLOWED_ORIGINS")
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        error "Required environment variable $var is not set"
    fi
done

success "Pre-deployment checks passed"

# Backup current database (if exists)
log "Creating database backup..."
if docker ps | grep -q "poker_db_prod"; then
    BACKUP_FILE="$PROJECT_ROOT/backups/pre-deploy-$(date +%Y%m%d-%H%M%S).sql"
    mkdir -p "$PROJECT_ROOT/backups"

    docker exec poker_db_prod pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > "$BACKUP_FILE" || warning "Backup failed - continuing deployment"

    if [ -f "$BACKUP_FILE" ]; then
        success "Database backup created: $BACKUP_FILE"
    fi
fi

# Build frontend
log "Building frontend..."
cd "$PROJECT_ROOT/frontend"
if [ ! -f "package.json" ]; then
    error "Frontend package.json not found"
fi

npm ci || error "Frontend dependency installation failed"
npm run build || error "Frontend build failed"
success "Frontend built successfully"

cd "$PROJECT_ROOT"

# Stop existing containers
log "Stopping existing containers..."
docker-compose -f docker-compose.prod.yml down || warning "No existing containers to stop"

# Pull latest images
log "Pulling latest Docker images..."
docker-compose -f docker-compose.prod.yml pull

# Build new images
log "Building application images..."
docker-compose -f docker-compose.prod.yml build --no-cache

# Start services
log "Starting services..."
docker-compose -f docker-compose.prod.yml up -d

# Wait for services to be ready
log "Waiting for services to start..."
sleep 30

# Health check
log "Performing health checks..."
MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -f http://localhost/api/health &> /dev/null; then
        success "Health check passed"
        break
    fi

    RETRY_COUNT=$((RETRY_COUNT + 1))
    log "Health check attempt $RETRY_COUNT/$MAX_RETRIES failed, retrying in 10 seconds..."
    sleep 10
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    error "Health checks failed after $MAX_RETRIES attempts"
fi

# Run database migrations
log "Running database migrations..."
docker exec poker_backend_prod python -m alembic upgrade head || error "Database migration failed"

# Final health check
log "Performing final health check..."
curl -f http://localhost/api/health > /dev/null || error "Final health check failed"

# Show running containers
log "Deployment status:"
docker-compose -f docker-compose.prod.yml ps

success "Deployment completed successfully!"
log "Application is available at: https://$(echo $ALLOWED_ORIGINS | cut -d',' -f1 | sed 's|https://||')"
log "Health check: https://$(echo $ALLOWED_ORIGINS | cut -d',' -f1 | sed 's|https://||')/api/health"
log "Logs: docker-compose -f docker-compose.prod.yml logs -f"