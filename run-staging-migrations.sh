#!/bin/bash
set -e

echo "📊 Running staging database migrations..."
echo ""

PROJECT_ID="home-game-472415"
REGION="us-central1"
SERVICE_NAME="poker-backend-staging"

# Get the latest deployed image
echo "🔍 Getting latest staging image..."
IMAGE=$(gcloud run services describe $SERVICE_NAME \
  --region=$REGION \
  --format='value(spec.template.spec.containers[0].image)')

echo "Using image: $IMAGE"
echo ""

# Create temporary migration job
JOB_NAME="migrate-staging-manual-$(date +%s)"

echo "🚀 Creating and running migration job..."

# Create job with environment variables
# Note: PYTHONPATH is already set in Dockerfile to /app/src
gcloud run jobs create $JOB_NAME \
  --image $IMAGE \
  --region $REGION \
  --set-cloudsql-instances $PROJECT_ID:$REGION:home-game-db \
  --env-vars-file backend/cloud-run-env-staging.yaml \
  --execute-now \
  --wait \
  --command="python" \
  --args="-m","alembic","upgrade","head"

# Clean up job
echo "🧹 Cleaning up temporary job..."
gcloud run jobs delete $JOB_NAME --region $REGION --quiet

echo ""
echo "✅ Staging migrations completed successfully!"