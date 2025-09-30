# GCP Staging Environment Setup Guide

## Overview

Your staging environment runs on the same GCP infrastructure as production:
- **Cloud Run Service**: `poker-backend-staging` (separate from production)
- **Database**: `home_game_staging` (same Cloud SQL instance, separate database)
- **Cost**: ~$5-10/month (scales to zero when not in use)

## One-Time Setup

### 1. Create Staging Database and Service

```bash
# Run the setup script
./setup-staging.sh
```

This will:
- Create `home_game_staging` database on your existing Cloud SQL instance
- Deploy `poker-backend-staging` Cloud Run service
- Configure environment variables from `backend/cloud-run-env-staging.yaml`

### 2. Run Initial Migrations

```bash
# Run migrations on staging database
./run-staging-migrations.sh
```

### 3. Test Staging Environment

```bash
# Get the staging URL
STAGING_URL=$(gcloud run services describe poker-backend-staging --region=us-central1 --format='value(status.url)')

# Test health endpoint
curl $STAGING_URL/api/health

# Should return:
# {"status":"healthy","environment":"staging",...}
```

### 4. Configure GitHub Secrets

Add these secrets in GitHub Settings → Secrets → Actions:

1. **GCP_SA_KEY**: Service account JSON key
   ```bash
   # Create service account with Cloud Run and SQL permissions
   gcloud iam service-accounts create github-actions \
     --display-name="GitHub Actions"

   # Grant permissions
   gcloud projects add-iam-policy-binding home-game-472415 \
     --member="serviceAccount:github-actions@home-game-472415.iam.gserviceaccount.com" \
     --role="roles/run.admin"

   gcloud projects add-iam-policy-binding home-game-472415 \
     --member="serviceAccount:github-actions@home-game-472415.iam.gserviceaccount.com" \
     --role="roles/cloudsql.client"

   # Create and download key
   gcloud iam service-accounts keys create github-actions-key.json \
     --iam-account=github-actions@home-game-472415.iam.gserviceaccount.com

   # Copy the entire contents of github-actions-key.json to GitHub secret GCP_SA_KEY
   ```

2. **STAGING_HEALTH_CHECK_URL**: `https://poker-backend-staging-xxxxx-uc.a.run.app/api/health`
3. **STAGING_API_URL**: `https://poker-backend-staging-xxxxx-uc.a.run.app/api`
4. **PROD_HEALTH_CHECK_URL**: `https://homegame.gg/api/health`
5. **PROD_API_URL**: `https://homegame.gg/api`

### 5. Deploy Frontend Staging (Optional)

If using Vercel:
```bash
# Create staging environment in Vercel
vercel env add REACT_APP_API_URL staging
# Enter: https://poker-backend-staging-xxxxx-uc.a.run.app/api

# Deploy to staging
vercel --target staging
```

## Using the CI/CD Pipeline

### Deploy to Staging

1. Go to GitHub Actions → Deploy workflow
2. Click "Run workflow"
3. Select environment: **staging**
4. Click "Run workflow"

The pipeline will:
1. ✅ Run all tests
2. ✅ Check migrations for dangerous operations
3. 🚀 Deploy to `poker-backend-staging`
4. 📊 Run database migrations (if any)
5. 🏥 Run health checks

### Deploy to Production

Same steps but select **production** environment.

## Manual Deployment Commands

### Deploy Staging Manually
```bash
gcloud run deploy poker-backend-staging \
  --source ./backend \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --env-vars-file backend/cloud-run-env-staging.yaml \
  --add-cloudsql-instances home-game-472415:us-central1:home-game-db \
  --memory 1Gi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 2
```

### Run Migrations
```bash
./run-staging-migrations.sh
```

### View Logs
```bash
# View staging logs
gcloud run services logs read poker-backend-staging --region=us-central1 --limit=50

# Stream logs
gcloud run services logs tail poker-backend-staging --region=us-central1
```

### Get Service URL
```bash
gcloud run services describe poker-backend-staging --region=us-central1 --format='value(status.url)'
```

## Testing in Staging

### 1. Health Check
```bash
curl https://poker-backend-staging-xxxxx-uc.a.run.app/api/health
```

### 2. Create Test Game
```bash
curl -X POST https://poker-backend-staging-xxxxx-uc.a.run.app/api/games/create \
  -H "Content-Type: application/json" \
  -d '{"title":"Staging Test Game"}'
```

### 3. Test with Frontend
Point your frontend staging environment to the staging backend URL.

## Cost Optimization

Staging is configured to scale to zero:
- **min_instances: 0** - No cost when idle
- **max_instances: 2** - Limited scaling
- **Estimated cost**: $5-10/month with light usage

To check costs:
```bash
# View Cloud Run costs
gcloud billing accounts list
gcloud beta billing projects describe home-game-472415
```

## Troubleshooting

### Database Connection Issues
```bash
# Verify database exists
gcloud sql databases list --instance=home-game-db

# Check Cloud SQL instance status
gcloud sql instances describe home-game-db
```

### Service Not Starting
```bash
# View detailed logs
gcloud run services logs read poker-backend-staging --region=us-central1 --limit=100

# Check service description
gcloud run services describe poker-backend-staging --region=us-central1
```

### Migration Failures
```bash
# Connect to database directly
gcloud sql connect home-game-db --user=postgres --database=home_game_staging

# Check migration status
SELECT * FROM alembic_version;
```

## Rollback Staging

```bash
# List revisions
gcloud run revisions list --service=poker-backend-staging --region=us-central1

# Rollback to previous revision
gcloud run services update-traffic poker-backend-staging \
  --region=us-central1 \
  --to-revisions=REVISION-NAME=100

# Or via GitHub Actions: Deploy an older commit to staging
```

## Next Steps

1. ✅ Complete one-time setup above
2. ✅ Test manual staging deployment
3. ✅ Configure GitHub secrets
4. ✅ Test GitHub Actions deployment to staging
5. ✅ Deploy frontend staging (optional)
6. 🚀 Deploy to production with confidence!