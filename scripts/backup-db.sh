#!/bin/bash

# Database backup script for Cloud SQL
# Usage: ./backup-db.sh

set -e

# Configuration
PROJECT_ID=${GOOGLE_CLOUD_PROJECT}
INSTANCE_NAME="poker-analytics-db"
BACKUP_BUCKET="gs://your-backup-bucket-name"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="poker-analytics-backup-${TIMESTAMP}"

echo "Starting database backup..."

# Create Cloud SQL backup
gcloud sql backups create \
  --instance=${INSTANCE_NAME} \
  --description="Automated backup ${TIMESTAMP}" \
  --project=${PROJECT_ID}

echo "Cloud SQL backup created successfully"

# Export to GCS for additional safety
gcloud sql export sql ${INSTANCE_NAME} \
  ${BACKUP_BUCKET}/backups/${BACKUP_NAME}.sql \
  --database=poker_analytics \
  --project=${PROJECT_ID}

echo "Database exported to ${BACKUP_BUCKET}/backups/${BACKUP_NAME}.sql"

# Cleanup old backups (keep last 30 days)
gsutil -m rm "${BACKUP_BUCKET}/backups/*$(date -d '30 days ago' +%Y%m%d)*" || true

echo "Backup completed successfully"