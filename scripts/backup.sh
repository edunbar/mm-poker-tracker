#!/bin/bash

# Database Backup Script for Poker Analytics
# Usage: ./scripts/backup.sh [manual|auto]

set -e

BACKUP_TYPE=${1:-manual}
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="$PROJECT_ROOT/backups"
DATE=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$BACKUP_DIR/backup.log"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Logging
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

# Create backup directory
mkdir -p "$BACKUP_DIR"

log "Starting $BACKUP_TYPE backup..."

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

# Get container name
DB_CONTAINER=$(docker ps | grep "poker_db" | awk '{print $NF}')
log "Found database container: $DB_CONTAINER"

# Create backup filename
BACKUP_FILE="$BACKUP_DIR/poker_analytics_${BACKUP_TYPE}_${DATE}.sql"

# Perform backup
log "Creating database backup..."
docker exec "$DB_CONTAINER" pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > "$BACKUP_FILE"

if [ $? -eq 0 ] && [ -s "$BACKUP_FILE" ]; then
    # Get file size
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    success "Backup created successfully: $BACKUP_FILE ($BACKUP_SIZE)"

    # Compress backup
    log "Compressing backup..."
    gzip "$BACKUP_FILE"
    COMPRESSED_FILE="${BACKUP_FILE}.gz"
    COMPRESSED_SIZE=$(du -h "$COMPRESSED_FILE" | cut -f1)
    success "Backup compressed: $COMPRESSED_FILE ($COMPRESSED_SIZE)"

    # Update latest symlink
    ln -sf "$(basename "$COMPRESSED_FILE")" "$BACKUP_DIR/latest_backup.sql.gz"

else
    error "Backup failed or file is empty"
fi

# Cleanup old backups (keep last 30 days for manual, 7 days for auto)
if [ "$BACKUP_TYPE" = "auto" ]; then
    RETENTION_DAYS=7
else
    RETENTION_DAYS=30
fi

log "Cleaning up backups older than $RETENTION_DAYS days..."
find "$BACKUP_DIR" -name "poker_analytics_${BACKUP_TYPE}_*.sql.gz" -mtime +$RETENTION_DAYS -delete

# List recent backups
log "Recent backups:"
ls -lah "$BACKUP_DIR"/poker_analytics_*.sql.gz | tail -5 | tee -a "$LOG_FILE"

# Backup verification
log "Verifying backup integrity..."
if zcat "$COMPRESSED_FILE" | head -10 | grep -q "PostgreSQL database dump"; then
    success "Backup verification passed"
else
    error "Backup verification failed"
fi

success "Backup process completed successfully"