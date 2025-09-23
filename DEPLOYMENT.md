# Deployment Process

This document outlines the deployment process for the poker analytics application.

## Production Environment Overview

- **Frontend**: Vercel (https://www.homegame.gg)
- **Backend**: Google Cloud Run (`poker-analytics-backend`)
- **Database**: Google Cloud SQL PostgreSQL (`home-game-db`)
- **Project**: `home-game-472415`

## Prerequisites

1. **Environment Variables**:
   - Frontend: `.env.production` with `REACT_APP_API_URL=https://poker-analytics-backend-360080248475.us-central1.run.app`
   - Backend: Environment variables configured in Cloud Run (see `backend/env-vars.yaml`)

2. **Required Tools**:
   - `gcloud` CLI
   - `vercel` CLI
   - `cloud_sql_proxy` (for database migrations)
   - `psql` (PostgreSQL client)

## Frontend Deployment

```bash
cd frontend
ESLINT_NO_DEV_ERRORS=true npx vercel --prod
```

**Common Issues**:
- ESLint errors: Use `ESLINT_NO_DEV_ERRORS=true` flag
- Build cache issues: Clear with `rm -rf node_modules/.cache .eslintcache`

## Backend Deployment

```bash
cd backend
gcloud run deploy poker-analytics-backend --source . --region us-central1
```

**Post-deployment Configuration**:
```bash
# Set environment variables (if needed)
gcloud run services update poker-analytics-backend \
  --region us-central1 \
  --env-vars-file cloud-run-env.yaml

# Add Cloud SQL connection (if needed)
gcloud run services update poker-analytics-backend \
  --region us-central1 \
  --add-cloudsql-instances home-game-472415:us-central1:home-game-db
```

## Database Migrations

### 1. Connect via Cloud SQL Proxy

Check if proxy is already running:
```bash
lsof -i :5433
```

If not running, start it:
```bash
./cloud_sql_proxy -instances=home-game-472415:us-central1:home-game-db=tcp:5433 &
```

### 2. Run Migration

```bash
PGPASSWORD='O1XbT66.^#H!83[fds234' psql "postgresql://poker_user@localhost:5433/home_game" < migration_file.sql
```

### 3. Verify Migration

```bash
PGPASSWORD='O1XbT66.^#H!83[fds234' psql "postgresql://poker_user@localhost:5433/home_game" -c "\dt table_name"
```

## Full Deployment Checklist

### 1. Backend Changes
- [ ] Make code changes
- [ ] Create migration files (if database changes)
- [ ] Test locally
- [ ] Deploy to Cloud Run: `gcloud run deploy poker-analytics-backend --source . --region us-central1`
- [ ] Verify environment variables and Cloud SQL connection

### 2. Database Changes (if needed)
- [ ] Connect via Cloud SQL Proxy
- [ ] Run migrations via `psql`
- [ ] Verify tables/changes exist

### 3. Frontend Changes
- [ ] Update `.env.production` if API changes
- [ ] Test locally with production API
- [ ] Deploy to Vercel: `ESLINT_NO_DEV_ERRORS=true npx vercel --prod`

### 4. Verification
- [ ] Check health endpoint: `curl https://poker-analytics-backend-360080248475.us-central1.run.app/api/health`
- [ ] Test specific endpoints
- [ ] Verify frontend loads and connects to backend
- [ ] Check Cloud Run logs for errors: `gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=poker-analytics-backend"`

## Common Issues & Solutions

### Cloud SQL Connection Issues
- **Symptom**: "relation does not exist" errors
- **Solution**: Ensure Cloud SQL instance is connected to Cloud Run service
- **Command**: `gcloud run services update poker-analytics-backend --region us-central1 --add-cloudsql-instances home-game-472415:us-central1:home-game-db`

### Environment Variable Issues
- **Symptom**: "Expected string or URL object, got None"
- **Solution**: Update environment variables from `env-vars.yaml`
- **Command**: `gcloud run services update poker-analytics-backend --region us-central1 --env-vars-file cloud-run-env.yaml`

### Frontend API Connection Issues
- **Symptom**: 404 errors on API calls
- **Solution**: Verify `REACT_APP_API_URL` in `.env.production` points to correct backend service
- **Current URL**: `https://poker-analytics-backend-360080248475.us-central1.run.app`

### Migration Access Issues
- **Symptom**: Can't connect to database for migrations
- **Solution**: Use Cloud SQL Proxy method above
- **Alternative**: Use Cloud Shell for database access

## Service URLs

- **Frontend Production**: https://www.homegame.gg
- **Backend API**: https://poker-analytics-backend-360080248475.us-central1.run.app
- **Health Check**: https://poker-analytics-backend-360080248475.us-central1.run.app/api/health

## Environment Files

- `frontend/.env.production`: Frontend production environment variables
- `backend/env-vars.yaml`: Backend Cloud Run environment variables
- `backend/cloud-run-env.yaml`: Cloud Run environment variables format

## Notes

- Always test health endpoint after backend deployment
- Frontend uses the backend URL from `.env.production` during build
- Database migrations require Cloud SQL Proxy connection
- Cloud Run services need explicit Cloud SQL instance connection
- Use `ESLINT_NO_DEV_ERRORS=true` for frontend deployments to handle linting issues