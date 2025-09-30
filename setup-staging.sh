#!/bin/bash
set -e

echo "🚀 Setting up GCP Staging Environment"
echo "======================================"
echo ""

# Configuration
PROJECT_ID="home-game-472415"
REGION="us-central1"
SQL_INSTANCE="home-game-db"
STAGING_DB="home_game_staging"

echo "📋 Configuration:"
echo "  Project: $PROJECT_ID"
echo "  Region: $REGION"
echo "  SQL Instance: $SQL_INSTANCE"
echo "  Staging Database: $STAGING_DB"
echo ""

# Set project
echo "🔧 Setting GCP project..."
gcloud config set project $PROJECT_ID

# Create staging database (using existing Cloud SQL instance)
echo "📊 Creating staging database..."
gcloud sql databases create $STAGING_DB --instance=$SQL_INSTANCE || echo "Database may already exist"

# Deploy staging Cloud Run service
echo "🚀 Deploying staging Cloud Run service..."
gcloud run deploy poker-backend-staging \
  --source ./backend \
  --region $REGION \
  --platform managed \
  --allow-unauthenticated \
  --env-vars-file backend/cloud-run-env-staging.yaml \
  --add-cloudsql-instances $PROJECT_ID:$REGION:$SQL_INSTANCE \
  --memory 1Gi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 2 \
  --timeout 300

# Get the service URL
SERVICE_URL=$(gcloud run services describe poker-backend-staging --region=$REGION --format='value(status.url)')

echo ""
echo "✅ Staging environment setup complete!"
echo ""
echo "📍 Staging Service URL: $SERVICE_URL"
echo ""
echo "🔧 Next steps:"
echo "  1. Run migrations: ./run-staging-migrations.sh"
echo "  2. Test health endpoint: curl $SERVICE_URL/api/health"
echo "  3. Update frontend staging environment to use: $SERVICE_URL"
echo "  4. Add to GitHub secrets:"
echo "     - STAGING_HEALTH_CHECK_URL=$SERVICE_URL/api/health"
echo "     - STAGING_API_URL=$SERVICE_URL/api"
echo ""