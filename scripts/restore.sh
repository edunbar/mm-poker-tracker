#!/bin/bash

# Database Restore Script for Poker Analytics
# Usage: ./scripts/restore.sh <backup_file>

set -e

if [ $# -eq 0 ]; then
    echo "Usage: $0 <backup_file>"
    echo "Example: $0 backups/poker_analytics_manual_20231215_143022.sql.gz"
    exit 1
fi

BACKUP_FILE="$1"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_FILE="$PROJECT_ROOT/backups/restore.log"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "$(date +'%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
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

# Check if backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    error "Backup file not found: $BACKUP_FILE"
fi

log "Starting database restore from: $BACKUP_FILE"

# Load environment variables
if [ -f "$PROJECT_ROOT/.env.production" ]; then
    source "$PROJECT_ROOT/.env.production"
elif [ -f "$PROJECT_ROOT/.env" ]; then
    source "$PROJECT_ROOT/.env"
else
    error "No environment file found"
fi

# Check if database container is running
if ! docker ps | grep -q "poker_db"; then
    error "Database container is not running"
fi

DB_CONTAINER=$(docker ps | grep "poker_db" | awk '{print $NF}')
log "Found database container: $DB_CONTAINER"

# Create safety backup before restore
log "Creating safety backup before restore..."
SAFETY_BACKUP="$PROJECT_ROOT/backups/pre_restore_$(date +%Y%m%d_%H%M%S).sql"
docker exec "$DB_CONTAINER" pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > "$SAFETY_BACKUP"
gzip "$SAFETY_BACKUP"
success "Safety backup created: ${SAFETY_BACKUP}.gz"

# Confirmation prompt
echo -e "${YELLOW}WARNING: This will completely replace the current database!${NC}"
echo "Current database: $POSTGRES_DB"
echo "Backup file: $BACKUP_FILE"
echo "Safety backup: ${SAFETY_BACKUP}.gz"
read -p "Are you sure you want to continue? (yes/no): " -r

if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    log "Restore cancelled by user"
    exit 0
fi

# Stop backend to prevent new connections
log "Stopping backend services..."
docker-compose -f docker-compose.prod.yml stop backend || warning "Could not stop backend"

# Drop and recreate database
log "Dropping and recreating database..."
docker exec "$DB_CONTAINER" psql -U "$POSTGRES_USER" -d postgres -c "DROP DATABASE IF EXISTS $POSTGRES_DB;"
docker exec "$DB_CONTAINER" psql -U "$POSTGRES_USER" -d postgres -c "CREATE DATABASE $POSTGRES_DB;"

# Restore from backup
log "Restoring database from backup..."
if [[ "$BACKUP_FILE" == *.gz ]]; then
    # Compressed backup
    zcat "$BACKUP_FILE" | docker exec -i "$DB_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"
else
    # Uncompressed backup
    docker exec -i "$DB_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" < "$BACKUP_FILE"
fi

if [ $? -eq 0 ]; then
    success "Database restore completed successfully"
else
    error "Database restore failed"
fi

# Restart backend
log "Restarting backend services..."
docker-compose -f docker-compose.prod.yml start backend

# Wait for backend to be ready
log "Waiting for backend to start..."
sleep 15

# Health check
log "Performing health check..."
if curl -f http://localhost/api/health &> /dev/null; then
    success "Health check passed - restore completed successfully"
else
    warning "Health check failed - manual verification recommended"
fi

# Verify database content
log "Verifying database content..."
GAMES_COUNT=$(docker exec "$DB_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c "SELECT COUNT(*) FROM games;" | xargs)
PLAYERS_COUNT=$(docker exec "$DB_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c "SELECT COUNT(*) FROM players;" | xargs)

log "Database verification:"
log "  Games: $GAMES_COUNT"
log "  Players: $PLAYERS_COUNT"

success "Database restore process completed"
log "Safety backup is available at: ${SAFETY_BACKUP}.gz"