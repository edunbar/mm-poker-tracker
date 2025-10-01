# Deployment Checklist

> **Version 2.0** - Updated 2025-10-01 after production rollout post-mortem

## Pre-Deployment Checklist

### Code Quality
- [ ] All tests passing locally (`cd backend && PYTHONPATH=src pytest tests/ -v`)
- [ ] Frontend builds successfully (`cd frontend && npm run build`)
- [ ] No ESLint errors in frontend
- [ ] Critical financial tests passing (test_financial_integrity.py)

### Configuration
- [ ] Environment variables updated (if backend URL changed)
  - [ ] `frontend/.env.production`
  - [ ] `backend/cloud-run-env.yaml` (production)
  - [ ] `backend/cloud-run-env-staging.yaml` (staging)
- [ ] GitHub Secrets updated (if needed)
  - [ ] `PROD_HEALTH_CHECK_URL`
  - [ ] `STAGING_HEALTH_CHECK_URL`
- [ ] Vercel environment variables verified
  - [ ] `REACT_APP_API_URL` set correctly

### Database
- [ ] Database migrations created (if schema changes)
- [ ] Migrations reviewed for dangerous operations (DROP TABLE, DROP COLUMN, etc.)
- [ ] Migration tested in staging
- [ ] Backup taken (if major schema change)

### Documentation
- [ ] CHANGELOG.md updated
- [ ] Breaking changes documented
- [ ] Environment variable changes documented

---

## Deployment Process

### Staging Deployment

**Backend:**
1. Commit and push changes to GitHub
2. Go to GitHub Actions → Deploy workflow
3. Click "Run workflow"
4. Select **"staging"** environment
5. Review migration safety (skip if needed)
6. Wait for deployment to complete
7. Verify health checks pass

**Frontend:**
- Automatically deploys via Vercel on push to GitHub
- Check Vercel dashboard for deployment status

**Verification:**
- [ ] Visit staging site and test critical flows
- [ ] Check browser console for errors
- [ ] Verify API calls going to correct backend
- [ ] Test session ingestion
- [ ] Test payment ledger
- [ ] Test game summary

### Production Deployment

**Backend:**
1. Ensure staging deployment successful
2. Go to GitHub Actions → Deploy workflow
3. Click "Run workflow"
4. Select **"production"** environment
5. **Do NOT skip migration check** (unless intentional)
6. Wait for deployment to complete
7. Monitor health checks

**Frontend:**
- If needed, trigger manual redeploy in Vercel
- Or merge to main branch for auto-deploy

**Verification:**
- [ ] Visit https://homegame.gg in incognito
- [ ] Open DevTools → Network tab
- [ ] Verify all API calls go to `poker-backend-*.run.app`
- [ ] Test critical user flows
- [ ] Monitor error logs for 15 minutes
- [ ] Check Cloud Run metrics

---

## Post-Deployment

### Monitoring (First 30 minutes)
- [ ] Check Cloud Run logs for errors
  ```bash
  gcloud run services logs tail poker-backend --region=us-central1
  ```
- [ ] Monitor error rates in GCP Console
- [ ] Check user reports (if applicable)
- [ ] Verify database connections healthy

### Cleanup
- [ ] Delete old preview deployments in Vercel (if applicable)
- [ ] Delete old Cloud Run services (after verification period)
- [ ] Clear old Docker images (if storage is an issue)

---

## Rollback Procedure

### If Deployment Fails:

**Backend Rollback:**
```bash
# 1. Find previous working revision
gcloud run revisions list --service=poker-backend --region=us-central1

# 2. Rollback to specific revision
gcloud run services update-traffic poker-backend \
  --region=us-central1 \
  --to-revisions=REVISION_NAME=100

# 3. If database migration ran, revert it
# (Create down migration or restore backup)
```

**Frontend Rollback:**
1. Go to Vercel → Deployments
2. Find last working deployment
3. Click "Redeploy"

**Database Rollback:**
```bash
# If migration needs to be reverted
cd backend
python -m alembic downgrade -1  # Or specific revision
```

---

## Common Issues & Solutions

### Build Fails on Vercel
- **Issue:** `react-scripts: command not found`
- **Solution:** Clear build cache, redeploy without cache

### Health Check Fails
- **Issue:** HTTP 307 redirects
- **Solution:** Update GitHub secret URLs, ensure HTTPS

### Frontend Calls Wrong Backend
- **Issue:** Calls localhost or old backend
- **Solution:** Update `REACT_APP_API_URL` in Vercel env vars, redeploy

### Migration Doesn't Run
- **Issue:** Migration step shows 0s
- **Solution:** Check migration path in workflow, run manually if needed

---

## Infrastructure Changes Checklist

**When changing service names, URLs, or major infrastructure:**

- [ ] Update all environment files
  - [ ] `frontend/.env.production`
  - [ ] `frontend/.env.staging.local`
  - [ ] `backend/cloud-run-env.yaml`
  - [ ] `backend/cloud-run-env-staging.yaml`
- [ ] Update GitHub Actions secrets
- [ ] Update Vercel environment variables
- [ ] Update health check URLs
- [ ] Document the change in CHANGELOG.md
- [ ] Plan migration period (run both old/new in parallel)
- [ ] Set calendar reminder to delete old services after 1 week
- [ ] Update monitoring/alerting configurations

---

## Current Infrastructure (as of 2025-10-01)

### Production
- **Frontend**: https://homegame.gg (Vercel)
- **Backend**: `poker-backend` → https://poker-backend-6t2w34itkq-uc.a.run.app
- **Database**: Cloud SQL `home-game-db` → `home_game` database
- **Project**: `home-game-472415`

### Staging
- **Frontend**: https://home-game-staging.vercel.app (Vercel)
- **Backend**: `poker-backend-staging` → https://poker-backend-staging-6t2w34itkq-uc.a.run.app
- **Database**: Cloud SQL `home-game-db` → `home_game_staging` database
- **Project**: `home-game-472415`

### Deprecated (to be deleted)
- ~~`poker-analytics-backend`~~ (old production, replace with poker-backend)
- ~~`poker-analytics`~~ (unknown purpose)

---

## Manual Database Migration

If automated migration doesn't run, use this procedure:

```bash
# Get the deployed image
IMAGE=$(gcloud run services describe poker-backend \
  --region=us-central1 \
  --format='value(spec.template.spec.containers[0].image)')

# Create and run migration job
gcloud run jobs create migrate-prod-manual \
  --image $IMAGE \
  --region us-central1 \
  --set-cloudsql-instances home-game-472415:us-central1:home-game-db \
  --env-vars-file backend/cloud-run-env.yaml \
  --execute-now \
  --wait \
  --command="python" \
  --args="-m","alembic","upgrade","head"

# Clean up
gcloud run jobs delete migrate-prod-manual --region us-central1 --quiet
```

---

## Emergency Contacts

- **Primary:** Eric Dunbar
- **GCP Console:** https://console.cloud.google.com/run?project=home-game-472415
- **Vercel Dashboard:** https://vercel.com/dashboard
- **GitHub Actions:** https://github.com/edunbar/mm-poker-tracker/actions

---

## Version History

- **v2.0** - 2025-10-01 - Updated after production rollout issues, added infrastructure changes checklist
- **v1.0** - 2025-09-17 - Initial deployment documentation
