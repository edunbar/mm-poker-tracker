# 🛠️ Development Guide - Poker Analytics

Comprehensive guide for developers working on the Poker Analytics application. Covers setup, debugging, troubleshooting, and development workflows.

## 🚀 Quick Setup for New Developers

### 1. Prerequisites Check
```bash
# Check required tools
docker --version          # Should be 20.0+
docker-compose --version  # Should be 1.29+
node --version            # Should be 16.0+
python3 --version         # Should be 3.11+
git --version             # Any recent version
```

### 2. Repository Setup
```bash
# Clone the repository
git clone <your-repo-url>
cd poker-analytics

# Copy environment configuration
cp .env.example .env

# Review and update .env file
nano .env  # or your preferred editor
```

### 3. Choose Your Development Method

#### Option A: Full Docker (Recommended for beginners)
```bash
# Start all services
docker-compose up -d

# Access services
# Frontend: http://localhost:3000 (after running npm start in frontend/)
# Backend: http://localhost:8000  
# pgAdmin: http://localhost:5050
```

#### Option B: Hybrid (Backend in Docker, Frontend local)
```bash
# Start backend services only
docker-compose up db pgadmin -d

# Start backend in Docker
docker-compose up backend -d

# Start frontend locally
cd frontend
npm install
npm start
```

#### Option C: Fully Local
```bash
# Start PostgreSQL
docker-compose up db -d

# Backend setup
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL="postgresql+psycopg2://pokeruser:supersecret@localhost:5432/poker_analytics"
alembic upgrade head
python src/app.py

# Frontend setup (new terminal)
cd frontend  
npm install
npm start
```

## 🐛 Common Issues & Solutions

### Database Issues

**Issue: Database connection refused**
```bash
# Check if PostgreSQL is running
docker-compose ps

# If not running, start it
docker-compose up db -d

# Check connection
PGPASSWORD=supersecret psql -h localhost -U pokeruser -d poker_analytics -c "SELECT 1;"
```

**Issue: Database migrations fail**
```bash
# Check current migration state
cd backend
source venv/bin/activate
alembic current

# View migration history
alembic history

# If stuck, reset to specific revision
alembic downgrade <revision-id>
alembic upgrade head

# Nuclear option: reset all migrations
docker-compose down -v  # WARNING: Deletes all data
docker-compose up db -d
alembic upgrade head
```

**Issue: Permission denied on database files**
```bash
# Fix Docker volume permissions
docker-compose down
docker volume rm poker-analytics_db_data
docker-compose up db -d
```

### Backend Issues

**Issue: Import errors - "No module named 'src'"**
```bash
# Set Python path
export PYTHONPATH=/path/to/backend/src

# Or run from correct directory
cd backend
python src/app.py

# For Docker builds
# Check that Dockerfile sets PYTHONPATH correctly
```

**Issue: Google Sheets API errors**
```bash
# Check service account file exists
ls -la backend/mm-poker-tracker-*.json

# Verify file permissions
chmod 600 backend/mm-poker-tracker-*.json

# Test service account
cd backend
python -c "
import json
with open('mm-poker-tracker-[your-file].json') as f:
    data = json.load(f)
    print('Service Account Email:', data['client_email'])
"
```

**Issue: Flask app doesn't reload on changes**
```bash
# Make sure you're running in debug mode
export FLASK_ENV=development
python src/app.py

# For Docker, ensure volumes are mounted correctly
# Check docker-compose.yml volumes section
```

### Frontend Issues

**Issue: npm install fails**
```bash
# Clear npm cache
npm cache clean --force

# Remove node_modules and package-lock.json
rm -rf node_modules package-lock.json

# Try with specific npm version
npm install --legacy-peer-deps

# Or try yarn instead
npm install -g yarn
yarn install
```

**Issue: TypeScript compilation errors**
```bash
# Check TypeScript version
npm list typescript

# Update TypeScript (if compatible)
npm install typescript@latest

# Skip type checking (temporary fix)
npm start -- --no-type-check
```

**Issue: Tailwind styles not working**
```bash
# Rebuild Tailwind
npm run build:css

# Check Tailwind configuration
npx tailwindcss -i src/index.css -o dist/output.css --watch

# Clear browser cache
# Use browser dev tools > Network > Disable cache
```

**Issue: React Query cache issues**
```bash
# In browser dev tools console:
# Clear all queries
queryClient.clear()

# Invalidate specific query
queryClient.invalidateQueries(['gameData'])

# Reset to initial state  
queryClient.resetQueries()
```

### Docker Issues

**Issue: Docker containers won't start**
```bash
# Check Docker daemon
docker info

# Check available resources
docker system df

# Clean up unused resources
docker system prune -f

# Check container logs
docker-compose logs backend
docker-compose logs db
```

**Issue: Port conflicts**
```bash
# Check what's using ports
lsof -i :3000  # Frontend
lsof -i :8000  # Backend  
lsof -i :5432  # PostgreSQL

# Kill processes or use different ports
# Update docker-compose.yml ports section
```

**Issue: Volume mounting problems**
```bash
# Check volume mounts
docker-compose config

# Recreate volumes
docker-compose down -v
docker-compose up -d

# Check file permissions
ls -la backend/src/
# Should be readable by Docker user
```

## 🧪 Testing & Debugging

### Backend Testing
```bash
# Run all backend tests
cd backend
source venv/bin/activate
python -m pytest tests/

# Run specific test
python -m pytest tests/test_live_game_service.py -v

# Run with coverage
python -m pytest --cov=src tests/

# Debug mode testing
python -m pytest -s tests/  # Shows print statements
```

### Frontend Testing
```bash
# Run all frontend tests  
cd frontend
npm test

# Run specific test file
npm test -- --testNamePattern="LiveGameForm"

# Run with coverage
npm test -- --coverage

# Update snapshots
npm test -- --updateSnapshot
```

### Manual API Testing
```bash
# Test backend health
curl -X GET http://localhost:8000/api/games/get_transactions

# Test live game endpoint
curl -X POST http://localhost:8000/api/games/upload_live \
  -H "Content-Type: application/json" \
  -H "X-Admin-Code: 2LT8wByw4sMLAwB_ISq2TMRwJ6zaUZ1oy4w7y4WQscE" \
  -d '{
    "public_code": "C4QROK",
    "session_name": "Test Game",
    "players": [
      {"name": "Alice", "buy_in": 100.00, "cash_out": 120.00, "in_game": 0.00}
    ]
  }'

# Test with invalid data (should return error)
curl -X POST http://localhost:8000/api/games/upload_live \
  -H "Content-Type: application/json" \
  -H "X-Admin-Code: wrong-code" \
  -d '{"invalid": "data"}'
```

### Database Debugging
```bash
# Connect to database directly
PGPASSWORD=supersecret psql -h localhost -U pokeruser -d poker_analytics

# Useful queries for debugging
\dt                              # List tables
SELECT * FROM games LIMIT 5;    # Check games
SELECT * FROM sessions WHERE session_type = 'live' ORDER BY created_at DESC LIMIT 3;
SELECT * FROM audit_log ORDER BY at DESC LIMIT 10;  # Recent audit entries

# Check data integrity
SELECT 
    g.public_code, 
    COUNT(s.id) as session_count,
    COUNT(sps.session_id) as player_summary_count
FROM games g 
LEFT JOIN sessions s ON g.id = s.game_id
LEFT JOIN session_player_summaries sps ON s.id = sps.session_id  
GROUP BY g.public_code;
```

## 🔧 Development Workflows

### Adding New Features

#### 1. Backend Endpoint
```bash
# 1. Create database migration (if needed)
cd backend
alembic revision -m "Add new feature table"
# Edit the generated migration file
alembic upgrade head

# 2. Update models (if needed)
# Edit src/db/models.py

# 3. Create service layer
# Add src/services/new_feature_service.py

# 4. Add API endpoint
# Edit src/routes/game.py

# 5. Add tests
# Add tests/test_new_feature.py

# 6. Test manually
python src/app.py
# Use curl or Postman to test
```

#### 2. Frontend Component
```bash
# 1. Create component
# Add frontend/src/features/[domain]/components/NewComponent.tsx

# 2. Add to routing (if needed)
# Edit frontend/src/app/routes.tsx

# 3. Add API integration
# Add frontend/src/features/[domain]/api/newFeature.ts

# 4. Add to navigation (if needed)
# Edit frontend/src/features/admin/nav.ts

# 5. Test component
npm test -- --testNamePattern="NewComponent"
```

### Code Style & Standards

#### Backend (Python)
```bash
# Format code
black src/
isort src/

# Lint code
flake8 src/
mypy src/

# Pre-commit setup
pip install pre-commit
pre-commit install
```

#### Frontend (TypeScript/React)
```bash
# Format code
npx prettier --write src/

# Lint code
npm run lint

# Type check
npm run type-check
```

### Git Workflow
```bash
# Start new feature
git checkout main
git pull origin main
git checkout -b feature/your-feature-name

# Make changes
git add .
git commit -m "feat: add your feature description"

# Push and create PR
git push origin feature/your-feature-name
# Open PR in GitHub/GitLab
```

## 🚀 Performance Optimization

### Backend Performance
```bash
# Profile database queries
# Enable in src/db/database.py:
import logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

# Monitor query performance in PostgreSQL
SELECT query, mean_exec_time, calls 
FROM pg_stat_statements 
ORDER BY mean_exec_time DESC 
LIMIT 10;

# Add indexes for slow queries
CREATE INDEX idx_custom ON table_name (column_name);
```

### Frontend Performance
```bash
# Bundle analysis
npm run build
npx webpack-bundle-analyzer build/static/js/*.js

# Performance profiling in browser
# Use React DevTools Profiler
# Monitor Core Web Vitals

# Optimize images
# Convert to WebP format
# Use lazy loading
```

### Database Optimization
```sql
-- Add useful indexes
CREATE INDEX idx_sessions_game_started_at ON sessions(game_id, started_at);
CREATE INDEX idx_players_display_name_lower ON players(LOWER(display_name));
CREATE INDEX idx_audit_log_game_at ON audit_log(game_id, at);

-- Analyze query performance
EXPLAIN ANALYZE SELECT * FROM sessions s 
JOIN session_player_summaries sps ON s.id = sps.session_id 
WHERE s.game_id = 'your-game-uuid';

-- Update table statistics
ANALYZE sessions;
ANALYZE session_player_summaries;
```

## 🔐 Security Considerations

### Development Security
```bash
# Never commit secrets
git log --oneline | grep -i "password\|secret\|key"

# Use environment variables
echo ".env" >> .gitignore

# Validate admin codes  
# Should be 32+ characters, random
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Production Security Checklist
- [ ] Change default passwords
- [ ] Use HTTPS in production
- [ ] Set secure admin codes
- [ ] Enable database SSL
- [ ] Configure CORS properly
- [ ] Set up rate limiting
- [ ] Enable audit logging
- [ ] Regular security updates

## 📊 Monitoring & Observability

### Application Monitoring
```bash
# Enable debug logging
export DEBUG=true
export LOG_LEVEL=DEBUG

# Monitor API requests
tail -f backend/logs/app.log | grep "POST\|GET"

# Database monitoring
SELECT * FROM pg_stat_activity 
WHERE datname = 'poker_analytics';

# Check connection pool usage
SELECT 
    numbackends,
    xact_commit,
    xact_rollback,
    blks_read,
    blks_hit
FROM pg_stat_database 
WHERE datname = 'poker_analytics';
```

### Error Tracking
```python
# Add to production Flask app
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

sentry_sdk.init(
    dsn="YOUR_SENTRY_DSN",
    integrations=[FlaskIntegration()]
)
```

## 🤝 Contributing Guidelines

### Before Submitting PR
1. Run all tests: `npm test && python -m pytest`
2. Check code style: `npm run lint && black src/`
3. Update documentation if needed
4. Test manually with different scenarios
5. Check for security issues
6. Verify database migrations work

### PR Checklist Template
```markdown
## Changes
- [ ] Backend changes tested
- [ ] Frontend changes tested  
- [ ] Database migrations tested
- [ ] Documentation updated
- [ ] No secrets in code
- [ ] Error handling added
- [ ] Tests added/updated
```

---

## 🆘 Getting Help

### Debug Information to Collect
When asking for help, include:

1. **Environment info**:
   ```bash
   docker --version
   node --version
   python --version
   # Your OS version
   ```

2. **Error logs**:
   ```bash
   docker-compose logs backend --tail=50
   # Browser console errors (F12 > Console)
   # Terminal error output
   ```

3. **Configuration**:
   ```bash
   # Sanitized .env file (remove secrets)
   # docker-compose.yml relevant sections
   ```

4. **Steps to reproduce**:
   - Exact steps taken
   - Expected vs actual behavior
   - Any recent changes made

### Resources
- **Documentation**: README files in root, backend/, frontend/
- **Issues**: GitHub Issues for bug reports
- **API Testing**: Use Postman collection (if available)
- **Database**: pgAdmin at http://localhost:5050

---

**Remember**: When in doubt, start with a fresh environment using Docker. Most issues are environment-related and can be solved by rebuilding containers and volumes. 🐳