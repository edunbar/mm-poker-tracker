# Migration Safety Checklist

This checklist ensures safe deployment of database and service layer changes to production.

## Pre-Migration Checklist

### 1. Code Review
- [ ] All changes reviewed by at least one other developer
- [ ] Financial integrity tests passing (100% pass rate required)
- [ ] No breaking changes to existing API contracts
- [ ] Backward compatibility maintained for at least one version

### 2. Database Changes
- [ ] Migration scripts tested on staging database
- [ ] Rollback plan documented and tested
- [ ] Data integrity constraints verified
- [ ] Index performance impact analyzed
- [ ] Connection pool settings reviewed (pool_size, max_overflow)

### 3. Testing Requirements
- [ ] All critical financial tests passing (`tests/integration/test_financial_integrity.py`)
- [ ] Payment concurrency tests passing
- [ ] Payment atomicity tests passing
- [ ] Zero-sum financial invariants verified
- [ ] Manual QA completed on staging environment

### 4. Monitoring Setup
- [ ] Structured logging enabled for payment operations
- [ ] Database connection pool metrics configured
- [ ] Error alerting configured for financial operations
- [ ] Performance baselines established

## Migration Execution

### Phase 1: Staging Deployment
1. Deploy to staging environment
2. Run full test suite
3. Monitor logs for errors (minimum 24 hours)
4. Verify database performance metrics
5. Test rollback procedure

### Phase 2: Production Deployment (Low Traffic Window)
1. Create database backup
2. Enable maintenance mode (optional)
3. Run database migrations
4. Deploy application code
5. Run smoke tests
6. Monitor critical metrics for 1 hour

### Phase 3: Verification
- [ ] Financial integrity tests pass in production
- [ ] No error spikes in logs
- [ ] Database connection pool healthy
- [ ] Payment processing latency within SLA
- [ ] Zero-sum invariants maintained

## Post-Migration Checklist

### Immediate (First Hour)
- [ ] Monitor error rates (should be < 0.1%)
- [ ] Verify payment transaction flow
- [ ] Check database connection pool utilization
- [ ] Verify structured logging output

### Short-term (First 24 Hours)
- [ ] Review payment operation logs for anomalies
- [ ] Monitor database performance metrics
- [ ] Check for any balance discrepancies
- [ ] Verify settlement calculations

### Medium-term (First Week)
- [ ] Analyze payment operation durations
- [ ] Review structured log insights
- [ ] Verify no financial integrity violations
- [ ] User feedback review

## Rollback Procedure

### Triggers for Rollback
- Financial integrity test failures
- Error rate > 1% for payment operations
- Database connection pool exhaustion
- Zero-sum invariant violations
- Critical payment processing failures

### Rollback Steps
1. Stop application traffic (load balancer)
2. Revert database migrations (if applicable)
3. Deploy previous application version
4. Verify system health
5. Resume traffic gradually
6. Post-mortem analysis

## Critical Metrics to Monitor

### Financial Integrity
- Zero-sum invariant: `SUM(poker_net_winnings) = 0` per game
- Balance consistency: `poker_net + paid - received = balance`
- Transaction atomicity: All payment operations complete or rollback

### Performance
- Payment operation latency: p50 < 100ms, p99 < 500ms
- Database connection pool: utilization < 80%
- Error rate: < 0.1%
- Settlement calculation time: < 1s

### Database Health
- Connection pool size: 10 (configured)
- Max overflow: 20 (configured)
- Pool timeout: 30s (configured)
- Connection recycling: 3600s (configured)

## Emergency Contacts

- On-call Engineer: [Contact Info]
- Database Admin: [Contact Info]
- Product Owner: [Contact Info]

## Notes

- All production deployments require approval from at least 2 team members
- Critical financial operations require manual verification in staging
- Rollback decision should be made within 15 minutes of detecting issues
- Post-deployment monitoring required for minimum 1 hour