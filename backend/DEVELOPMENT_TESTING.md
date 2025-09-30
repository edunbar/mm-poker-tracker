# Development Testing Guide for Domain Migration

This guide provides step-by-step instructions for testing the domain layer migration in your development environment before deploying to production.

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL database running
- All dependencies installed (`pip install -r requirements.txt`)
- Domain layer files created (already done)

### Environment Setup

```bash
# Navigate to backend directory
cd backend

# Set environment variable to use legacy services initially
export USE_DOMAIN_SERVICES=false

# Verify current service selection
python -c "from src.services import get_service_info; print(get_service_info())"
```

Expected output:
```json
{
  "use_domain_services": false,
  "live_game_service": "legacy",
  "payment_service": "legacy",
  "session_ingestion_service": "legacy",
  "environment_var": "false"
}
```

## 📋 Testing Phases

### Phase 1: Domain Layer Unit Testing (Day 1)

#### Step 1.1: Run Domain Unit Tests
```bash
# Test value objects
python -m pytest tests/unit/domain/test_value_objects.py -v

# Test poker session entity
python -m pytest tests/unit/domain/test_poker_session.py -v

# Run all domain tests
python -m pytest tests/unit/domain/ -v --tb=short
```

**Expected Results:**
- All tests should pass
- ~95 unit tests covering all business rules
- No import errors or missing dependencies

**If Tests Fail:**
```bash
# Check Python path
export PYTHONPATH=./src:$PYTHONPATH

# Install missing dependencies
pip install pytest

# Check specific test failures
python -m pytest tests/unit/domain/test_value_objects.py::TestMoney::test_create_money_from_various_types -v
```

#### Step 1.2: Test Coverage Analysis
```bash
# Install coverage tool
pip install coverage

# Run tests with coverage
coverage run -m pytest tests/unit/domain/
coverage report --include="src/domain/*"
coverage html --include="src/domain/*"

# View coverage report
open htmlcov/index.html  # On macOS
# or browse to htmlcov/index.html
```

**Success Criteria:**
- Domain code coverage > 95%
- All critical paths tested
- All business rules verified

---

### Phase 2: Integration Testing (Day 2-3)

#### Step 2.1: Run Integration Tests
```bash
# Test service compatibility
python -m pytest tests/integration/test_domain_services.py -v

# If database issues, check connection
python -c "from src.db.database import SessionLocal; db = SessionLocal(); print('DB connected:', db is not None); db.close()"
```

**Expected Results:**
- All parity tests should pass
- Services should instantiate without errors
- Database operations should work correctly

#### Step 2.2: Run Migration Verification Script
```bash
# Make script executable
chmod +x scripts/test_domain_migration.py

# Run full migration test
python scripts/test_domain_migration.py
```

**Expected Output:**
```
🧪 Domain Migration Verification Tool
=====================================
Environment: USE_DOMAIN_SERVICES = false
✅ Legacy services are currently active.

🔥 Running Quick Smoke Test...
   ✅ All service imports successful
   ✅ All services instantiate successfully
   ✅ Domain layer imports successful
   ✅ Domain objects work correctly
   🎉 Smoke test PASSED!

📊 Phase 1: Comparing Service Outputs
   ✅ Payment service comparison complete

🗄️ Phase 2: Verifying Database Compatibility
   📊 Found 0 active sessions
   ✅ Repository save/retrieve works correctly

⚡ Phase 3: Performance Comparison
   🚀 Performance improved by 15.2% for game TESTG

🚨 Phase 4: Error Handling Verification
   ✅ Correctly handles invalid session ID
   ✅ Correctly handles negative amounts

📋 MIGRATION VERIFICATION REPORT
===============================
🎉 ALL TESTS PASSED - Migration ready for deployment!
```

**If Issues Found:**
1. Check database connection and schema
2. Verify all domain files were created correctly
3. Check import paths and Python path
4. Review error messages for specific failures

---

### Phase 3: Side-by-Side Testing (Day 4-5)

#### Step 3.1: Create Test Data
```bash
# Create test script
cat > test_sample_data.py << 'EOF'
#!/usr/bin/env python3
import sys
sys.path.insert(0, 'src')

from db.database import SessionLocal
from db.models import Game, Player, GamePlayer
from datetime import datetime

# Create sample test data
db = SessionLocal()
try:
    # Create test game
    game = Game(
        public_code="TEST1",
        admin_code="ADMIN123",
        title="Test Game for Domain Migration"
    )
    db.add(game)
    db.flush()

    # Create test players
    players = []
    for name in ["Alice", "Bob", "Charlie", "Dave"]:
        player = Player(
            display_name=name,
            external_id=f"{name.lower()}_test_123"
        )
        db.add(player)
        players.append(player)

    db.flush()

    # Link players to game
    for player in players:
        game_player = GamePlayer(
            game_id=game.id,
            player_id=player.id
        )
        db.add(game_player)

    db.commit()
    print(f"✅ Created test game {game.public_code} with {len(players)} players")

except Exception as e:
    print(f"❌ Error creating test data: {e}")
    db.rollback()
finally:
    db.close()
EOF

python test_sample_data.py
```

#### Step 3.2: Test with Legacy Services
```bash
# Ensure legacy services are active
export USE_DOMAIN_SERVICES=false

# Test payment service
python -c "
from src.services import PaymentService, get_service_info
print('Service info:', get_service_info())

service = PaymentService()
summary = service.get_payment_summary('test-game-id')
print(f'Payment summary retrieved: {len(summary)} players')
print('✅ Legacy services working')
"
```

#### Step 3.3: Switch to Domain Services
```bash
# Switch to domain services
export USE_DOMAIN_SERVICES=true

# Verify switch
python -c "from src.services import get_service_info; print(get_service_info())"
```

Expected output:
```json
{
  "use_domain_services": true,
  "live_game_service": "domain",
  "payment_service": "domain",
  "session_ingestion_service": "domain",
  "environment_var": "true"
}
```

#### Step 3.4: Test Domain Services
```bash
# Test domain services
python -c "
from src.services import PaymentService, LiveGameService, get_service_info
print('Service info:', get_service_info())

# Test PaymentService
payment_service = PaymentService()
print('✅ PaymentService instantiated')

# Test LiveGameService
live_service = LiveGameService()
print('✅ LiveGameService instantiated')

print('✅ Domain services working')
"
```

---

### Phase 4: Application Integration Testing (Week 2)

#### Step 4.1: Start Flask Application
```bash
# Start with domain services
export USE_DOMAIN_SERVICES=true
python src/app.py
```

**Expected Output:**
```
🎯 Using DOMAIN-BASED services
 * Running on http://127.0.0.1:8000
 * Debug mode: on
```

#### Step 4.2: Test API Endpoints

**Test Payment Endpoints:**
```bash
# Test getting payment summary (should work with both services)
curl -X GET "http://localhost:8000/api/games/TEST1/payments/summary"

# Test recording payment
curl -X POST "http://localhost:8000/api/games/TEST1/payments" \
  -H "Content-Type: application/json" \
  -d '{
    "payer_id": "player_uuid_here",
    "recipient_id": "player_uuid_here",
    "amount": 25.00,
    "payment_method": "test"
  }'
```

**Test Session Endpoints:**
```bash
# Test session creation
curl -X POST "http://localhost:8000/api/games/TEST1/sessions" \
  -H "Content-Type: application/json" \
  -d '{
    "player_id": "player_uuid_here",
    "buy_in_amount": 100.00,
    "session_type": "live"
  }'

# Test ending session
curl -X PUT "http://localhost:8000/api/sessions/session_id_here/end" \
  -H "Content-Type: application/json" \
  -d '{"cash_out_amount": 150.00}'
```

#### Step 4.3: Monitor Application Logs
```bash
# In another terminal, watch logs
tail -f logs/app.log

# Look for:
# ✅ "Using DOMAIN-BASED services"
# ✅ Successful API responses
# ❌ Any error messages or stack traces
```

---

### Phase 5: Load Testing (Week 2)

#### Step 5.1: Install Load Testing Tools
```bash
# Install locust for load testing
pip install locust

# Create load test script
cat > loadtest.py << 'EOF'
from locust import HttpUser, task, between
import random

class PokerUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        # Setup test data
        self.game_id = "TEST1"

    @task(1)
    def get_payment_summary(self):
        self.client.get(f"/api/games/{self.game_id}/payments/summary")

    @task(1)
    def get_settlement_suggestions(self):
        self.client.get(f"/api/games/{self.game_id}/payments/settlements")

    @task(2)
    def get_game_summary(self):
        self.client.get(f"/api/games/{self.game_id}/summary")
EOF
```

#### Step 5.2: Run Load Tests
```bash
# Test with legacy services
export USE_DOMAIN_SERVICES=false
python src/app.py &
SERVER_PID=$!

# Run load test
locust -f loadtest.py --host=http://localhost:8000 --users=10 --spawn-rate=2 --run-time=60s --headless

# Stop server
kill $SERVER_PID

# Test with domain services
export USE_DOMAIN_SERVICES=true
python src/app.py &
SERVER_PID=$!

# Run load test again
locust -f loadtest.py --host=http://localhost:8000 --users=10 --spawn-rate=2 --run-time=60s --headless

# Stop server
kill $SERVER_PID
```

**Compare Results:**
- Response times should be similar or better
- Error rates should be zero for both
- Memory usage should not increase significantly

---

### Phase 6: Error Scenarios Testing (Week 3)

#### Step 6.1: Test Error Handling
```bash
# Test with invalid data
curl -X POST "http://localhost:8000/api/games/INVALID/sessions" \
  -H "Content-Type: application/json" \
  -d '{"player_id": "invalid", "buy_in_amount": -100}'

# Should return 400 Bad Request with meaningful error message

# Test with missing authentication
curl -X POST "http://localhost:8000/api/games/TEST1/admin/sessions/ingest" \
  -H "Content-Type: application/json" \
  -d '{}'

# Should return 401 Unauthorized

# Test ending non-existent session
curl -X PUT "http://localhost:8000/api/sessions/nonexistent/end" \
  -H "Content-Type: application/json" \
  -d '{"cash_out_amount": 100}'

# Should return 404 Not Found
```

#### Step 6.2: Database Connection Testing
```bash
# Test with database down
sudo service postgresql stop  # Or equivalent for your system

# Try API calls - should return 500 with appropriate error
curl -X GET "http://localhost:8000/api/games/TEST1/summary"

# Restart database
sudo service postgresql start
```

---

### Phase 7: Rollback Testing (Week 3)

#### Step 7.1: Practice Rollback
```bash
# While application is running with domain services
export USE_DOMAIN_SERVICES=true
python src/app.py &
SERVER_PID=$!

# Test that it's using domain services
curl -X GET "http://localhost:8000/api/health" | grep -i domain

# Simulate rollback (would be done by changing env var and restarting)
kill $SERVER_PID

export USE_DOMAIN_SERVICES=false
python src/app.py &
SERVER_PID=$!

# Test that it's now using legacy services
curl -X GET "http://localhost:8000/api/health" | grep -i legacy

kill $SERVER_PID
```

#### Step 7.2: Data Integrity Check
```bash
# Verify no data was corrupted during testing
python scripts/test_domain_migration.py

# Check database for any inconsistencies
python -c "
from src.db.database import SessionLocal
from src.db.models import Game, Player, SessionPlayerSummary

db = SessionLocal()
games = db.query(Game).count()
players = db.query(Player).count()
summaries = db.query(SessionPlayerSummary).count()

print(f'Database integrity check:')
print(f'  Games: {games}')
print(f'  Players: {players}')
print(f'  Summaries: {summaries}')
print('✅ Data integrity maintained')
db.close()
"
```

---

## 🚨 Troubleshooting

### Common Issues and Solutions

#### Import Errors
```bash
# Error: ModuleNotFoundError: No module named 'src.domain'
export PYTHONPATH=./src:$PYTHONPATH

# Error: ImportError: attempted relative import with no known parent package
python -m pytest tests/unit/domain/test_poker_session.py
```

#### Database Connection Issues
```bash
# Error: could not connect to server
# Check PostgreSQL is running
sudo service postgresql status

# Check connection string
python -c "import os; print('DB URL:', os.getenv('DATABASE_URL', 'Not set'))"

# Test connection manually
python -c "
from src.db.database import SessionLocal
try:
    db = SessionLocal()
    db.execute('SELECT 1')
    print('✅ Database connected')
    db.close()
except Exception as e:
    print(f'❌ Database error: {e}')
"
```

#### Service Import Issues
```bash
# Error: cannot import domain services
python -c "
try:
    from src.services.live_game_service_v2 import LiveGameService
    print('✅ Domain services available')
except ImportError as e:
    print(f'❌ Domain import error: {e}')
    print('Check that all domain files were created correctly')
"
```

#### Memory Issues
```bash
# Monitor memory usage during testing
pip install psutil

python -c "
import psutil
import os

process = psutil.Process(os.getpid())
print(f'Memory usage: {process.memory_info().rss / 1024 / 1024:.2f} MB')
"
```

---

## 📊 Success Criteria

### Unit Tests
- [ ] All domain unit tests pass (95+ tests)
- [ ] Test coverage > 95% for domain code
- [ ] All business rules verified

### Integration Tests
- [ ] All service parity tests pass
- [ ] Database operations work correctly
- [ ] Repository save/retrieve verified

### Application Tests
- [ ] Flask app starts successfully with both service types
- [ ] All API endpoints respond correctly
- [ ] Error handling works as expected
- [ ] Performance is maintained or improved

### Load Tests
- [ ] Handle 10+ concurrent users
- [ ] Response times < 500ms for simple operations
- [ ] No memory leaks during extended operation
- [ ] Error rate < 1%

### Rollback Tests
- [ ] Can switch between service types instantly
- [ ] Data integrity maintained after rollback
- [ ] No service interruption during switch

---

## 🎯 Deployment Checklist

Before deploying to production:

### Pre-Deployment
- [ ] All tests passing in development
- [ ] Migration script runs successfully
- [ ] Performance benchmarks acceptable
- [ ] Error scenarios tested and handled
- [ ] Rollback procedure tested

### Deployment Day
- [ ] Backup database before deployment
- [ ] Deploy code with `USE_DOMAIN_SERVICES=false`
- [ ] Verify legacy services still work
- [ ] Switch to `USE_DOMAIN_SERVICES=true`
- [ ] Monitor application logs for errors
- [ ] Run health checks
- [ ] Monitor performance metrics

### Post-Deployment
- [ ] All endpoints responding correctly
- [ ] Database operations working
- [ ] No increase in error rates
- [ ] Performance within acceptable ranges
- [ ] User workflows functioning normally

### Emergency Rollback (if needed)
- [ ] Set `USE_DOMAIN_SERVICES=false`
- [ ] Restart application
- [ ] Verify legacy services working
- [ ] Monitor for stability
- [ ] Investigate issues in domain services

---

## 📞 Getting Help

If you encounter issues during testing:

1. **Check the logs first**: Most issues will show up in application logs
2. **Run the migration script**: `python scripts/test_domain_migration.py`
3. **Verify service selection**: Check `get_service_info()` output
4. **Test database connectivity**: Ensure PostgreSQL is running and accessible
5. **Check Python path**: Make sure `src` directory is in PYTHONPATH

**Debugging Commands:**
```bash
# Check current configuration
python -c "from src.services import get_service_info; print(get_service_info())"

# Validate services
python -c "from src.services import validate_service_compatibility; import json; print(json.dumps(validate_service_compatibility(), indent=2))"

# Test domain layer directly
python -c "from src.domain.poker.value_objects import Money; print(Money('100.50'))"

# Test database
python -c "from src.db.database import SessionLocal; db=SessionLocal(); print('✅ DB OK'); db.close()"
```

Remember: The goal is to ensure the domain-based services work identically to the legacy services before switching in production. Take your time with testing - it's better to catch issues in development than in production!

---

**Good luck with your domain migration! 🚀**