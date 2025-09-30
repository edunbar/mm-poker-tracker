# Rollback Procedure

This document describes the step-by-step process for rolling back a failed deployment.

## When to Rollback

Initiate a rollback if you observe:

- ❌ Health checks failing after deployment
- ❌ Critical errors in application logs
- ❌ Database migration failures
- ❌ Significant increase in error rates
- ❌ User-facing functionality broken

## Prerequisites

Before you begin, ensure you have:

- [ ] Access to production server (SSH or deployment console)
- [ ] Database backup created before deployment
- [ ] Git commit hash of last known good deployment
- [ ] Database credentials with appropriate permissions
- [ ] Notification sent to team about rollback in progress

## Rollback Steps

### Step 1: Assess the Situation (5 minutes)

```bash
# Check application logs for errors
tail -f /var/log/app/error.log

# Check database connection
psql -U pokeruser -h localhost -d poker_analytics -c "SELECT 1;"

# Check current git commit
git log -1 --oneline

# Check current migration version
cd backend
python -m alembic current
```

**Decision Point:** Determine if the issue is:
- Code-related → Proceed with code rollback (Step 2)
- Migration-related → Proceed with database rollback (Step 3) then code
- Configuration-related → Fix configuration first, avoid rollback if possible

### Step 2: Rollback Application Code (10 minutes)

```bash
# Identify last known good commit
git log --oneline -10

# Stop the application
sudo systemctl stop poker-app
# OR for Docker:
# docker-compose down

# Checkout previous version
git checkout <LAST_GOOD_COMMIT_HASH>

# Reinstall dependencies (if requirements changed)
cd backend
pip install -r requirements.txt

# Rebuild frontend (if frontend changed)
cd ../frontend
npm install
npm run build

# Restart application
sudo systemctl start poker-app
# OR for Docker:
# docker-compose up -d

# Wait for startup (adjust time as needed)
sleep 15

# Verify application is running
curl -I http://localhost:8000/health || echo "⚠️ Health check failed"
```

### Step 3: Rollback Database Migrations (15 minutes)

⚠️ **WARNING:** Database rollbacks can cause data loss. Only proceed if:
- You have a recent backup
- You understand what data will be lost
- The failed migration is newer than your backup

#### Option A: Downgrade Migration (Preferred if available)

```bash
cd backend

# Check current migration version
python -m alembic current

# List recent migrations
python -m alembic history -r -10

# Downgrade to previous version
python -m alembic downgrade -1

# Verify downgrade succeeded
python -m alembic current
```

#### Option B: Restore from Backup (If downgrade unavailable)

```bash
# 1. Create a backup of current state (safety net)
pg_dump -U pokeruser -h localhost -d poker_analytics \
  -f "/backups/pre_rollback_$(date +%Y%m%d_%H%M%S).sql"

# 2. Identify the backup file
ls -lht /backups/*.sql | head -5

# 3. Stop application to prevent writes
sudo systemctl stop poker-app

# 4. Restore from backup
psql -U pokeruser -h localhost -d poker_analytics \
  -f /backups/pre_deployment_YYYYMMDD_HHMMSS.sql

# 5. Verify restore
psql -U pokeruser -h localhost -d poker_analytics \
  -c "SELECT COUNT(*) FROM games;" \
  -c "SELECT COUNT(*) FROM sessions;"

# 6. Restart application
sudo systemctl start poker-app
```

### Step 4: Verify Rollback Success (10 minutes)

Run these checks to confirm rollback was successful:

```bash
# 1. Health check
curl http://localhost:8000/health
# Expected: HTTP 200 OK

# 2. Database connectivity
psql -U pokeruser -h localhost -d poker_analytics -c "SELECT 1;"
# Expected: Returns 1

# 3. API endpoint check
curl http://localhost:8000/api/games
# Expected: Returns valid JSON (even if empty array)

# 4. Check error logs (should be clean)
tail -n 50 /var/log/app/error.log | grep ERROR

# 5. Check migration version matches expectation
cd backend
python -m alembic current
# Expected: Matches last known good version

# 6. Verify critical data exists
psql -U pokeruser -h localhost -d poker_analytics -c "
  SELECT
    COUNT(*) as total_games,
    COUNT(DISTINCT public_code) as unique_codes
  FROM games;
"
```

### Step 5: Notify and Document (5 minutes)

```bash
# Create rollback report
cat > rollback_report_$(date +%Y%m%d_%H%M%S).txt << EOF
ROLLBACK REPORT
================
Date: $(date)
Rolled back from: <FAILED_COMMIT_HASH>
Rolled back to: <GOOD_COMMIT_HASH>
Reason: <REASON_FOR_ROLLBACK>

Health checks: PASSING
Database status: HEALTHY
Application status: RUNNING

Next steps:
1. Monitor error rates for next 30 minutes
2. Investigate root cause of deployment failure
3. Create fix in development environment
4. Test thoroughly before redeploying

EOF

cat rollback_report_*.txt
```

**Notify team:**
- Post in deployment channel: "✅ Rollback completed successfully"
- Update incident ticket with rollback details
- Schedule postmortem meeting

### Step 6: Post-Rollback Monitoring (30 minutes)

Monitor these metrics closely:

```bash
# Watch error logs in real-time
tail -f /var/log/app/error.log

# Monitor database connections
watch -n 5 'psql -U pokeruser -h localhost -d postgres \
  -c "SELECT count(*) FROM pg_stat_activity WHERE datname = '\''poker_analytics'\'';"'

# Check application response times
for i in {1..10}; do
  curl -w "Response time: %{time_total}s\n" -o /dev/null -s http://localhost:8000/health
  sleep 5
done
```

## Testing Rollback Procedure

To test the rollback procedure in a safe environment, use the provided test script:

```bash
cd backend

# The script will:
# 1. Create a temporary test database
# 2. Apply migrations and add test data
# 3. Create a backup
# 4. Simulate a failure
# 5. Perform rollback
# 6. Verify data restoration

./scripts/test_rollback.sh
```

**Note:** The test script requires a database user with `CREATEDB` permissions. If your user doesn't have this permission, ask your DBA to run the test, or grant temporary permissions:

```sql
-- As database superuser:
ALTER USER pokeruser CREATEDB;

-- After testing, revoke if needed:
ALTER USER pokeruser NOCREATEDB;
```

## Common Rollback Scenarios

### Scenario 1: Migration Added Column, Application Can't Start

**Symptom:** Application fails to start after migration adds new column

**Solution:**
```bash
# 1. Rollback code first (new code expects new column)
git checkout <PREVIOUS_COMMIT>
sudo systemctl restart poker-app

# 2. Then rollback migration (if column causes issues)
cd backend
python -m alembic downgrade -1
```

### Scenario 2: Migration Dropped Column, Data Lost

**Symptom:** Migration dropped column, can't downgrade to restore it

**Solution:**
```bash
# Only option: Restore from backup
sudo systemctl stop poker-app

psql -U pokeruser -h localhost -d poker_analytics \
  -f /backups/pre_deployment_YYYYMMDD_HHMMSS.sql

git checkout <PREVIOUS_COMMIT>
sudo systemctl start poker-app
```

**Prevention:** Never drop columns in migrations. Instead:
1. Deploy code that ignores column
2. Wait 24 hours
3. Then drop column in separate migration

### Scenario 3: Code Works But Performance Degraded

**Symptom:** Deployment successful but response times increased 10x

**Solution:**
```bash
# Quick rollback to restore performance
git checkout <PREVIOUS_COMMIT>
sudo systemctl restart poker-app

# Then investigate in development:
# - Check for missing indexes
# - Profile slow queries
# - Review N+1 query patterns
```

## Rollback Checklist

Use this checklist during a rollback:

```
[ ] 1. Notify team that rollback is starting
[ ] 2. Create backup of current state (safety net)
[ ] 3. Stop application
[ ] 4. Rollback database (if needed)
[ ] 5. Rollback application code
[ ] 6. Restart application
[ ] 7. Verify health checks passing
[ ] 8. Verify database queries working
[ ] 9. Check error logs
[ ] 10. Monitor for 30 minutes
[ ] 11. Document what happened
[ ] 12. Update incident ticket
[ ] 13. Schedule postmortem
```

## Prevention

To minimize rollback needs:

1. **Always test migrations locally first**
   ```bash
   # In development:
   python -m alembic upgrade head
   python -m alembic downgrade -1
   python -m alembic upgrade head
   ```

2. **Use feature flags for risky changes**
   - Deploy code with feature disabled
   - Enable gradually
   - Can disable without rollback

3. **Run CI tests before deploying**
   - All tests must pass
   - Include migration tests
   - Test backward compatibility

4. **Take backup before every deployment**
   ```bash
   pg_dump -U pokeruser -d poker_analytics \
     -f "/backups/pre_deploy_$(date +%Y%m%d_%H%M%S).sql"
   ```

5. **Use the deployment workflow**
   - GitHub Actions includes safety checks
   - Pre-deployment migration validation
   - Post-deployment health checks

## Emergency Contacts

If rollback fails or you need assistance:

- **Database Team:** [Contact info]
- **DevOps Lead:** [Contact info]
- **On-call Engineer:** [PagerDuty/Phone]

## Related Documentation

- [Deployment Workflow](.github/workflows/deploy.yml)
- [Migration Guide](MIGRATION_SAFETY_CHECKLIST.md)
- [Health Check Endpoints](docs/health-checks.md)
- [Backup Procedures](docs/backup-procedures.md)

---

**Last Updated:** 2025-09-29
**Maintained By:** DevOps Team
**Review Schedule:** After each rollback event