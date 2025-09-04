# 🃏 HomeGame Backend

Flask-based API server for the HomeGame application. Provides RESTful endpoints for game data ingestion, player management, and analytics with PostgreSQL persistence and Google Sheets integration.

## 🏗️ Architecture

### Application Structure
```
backend/
├── src/
│   ├── app.py                    # Flask application entry point
│   ├── db/
│   │   ├── database.py           # SQLAlchemy configuration
│   │   └── models.py             # Database models
│   ├── routes/
│   │   └── game.py              # API endpoints
│   └── services/                # Business logic layer
│       ├── session_ingestion_service.py  # Core session ingestion
│       ├── live_game_service.py      # Live game processing
│       ├── transaction_service.py    # PokerNow API integration
│       ├── game_summary_service.py   # Analytics and reporting
│       ├── player_*_service.py       # Player management
│       ├── sheets_service.py         # Google Sheets integration
│       ├── audit_service.py          # Audit log management
│       └── audit_middleware.py       # SQLAlchemy event tracking
├── migrations/                   # Alembic database migrations
├── scripts/                     # Utility scripts
├── requirements.txt             # Python dependencies
├── Dockerfile                   # Docker configuration
└── alembic.ini                 # Database migration config
```

### Key Design Patterns
- **Service Layer Architecture**: Business logic separated into focused service modules
- **Repository Pattern**: Database access abstracted through SQLAlchemy models
- **Event-Driven Auditing**: Comprehensive audit trail via SQLAlchemy events
- **Dual-Write Pattern**: Database and Google Sheets updated atomically

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 16+
- Virtual environment tool (venv, conda, etc.)

### 1. Environment Setup
```bash
cd backend

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Database Configuration
```bash
# Set database connection string
export DATABASE_URL="postgresql+psycopg2://pokeruser:supersecret@localhost:5432/poker_analytics"

# Run database migrations
alembic upgrade head
```

### 3. Start Development Server
```bash
# Start Flask development server
python src/app.py
```

Server runs on [http://localhost:8000](http://localhost:8000)

## 🗄️ Database Schema

### Core Models

#### Games Table
```sql
CREATE TABLE games (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    public_code CITEXT UNIQUE NOT NULL,           -- Shareable game identifier
    admin_code TEXT UNIQUE NOT NULL,              -- Secret admin access
    title TEXT,                                   -- Optional game name
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    meta JSONB DEFAULT '{}'::jsonb                -- Flexible metadata
);
```

#### Sessions Table
```sql
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    game_id UUID REFERENCES games(id) ON DELETE CASCADE,
    external_id TEXT,                             -- PokerNow session ID (nullable)
    session_type TEXT NOT NULL DEFAULT 'pokernow', -- 'pokernow' | 'live'
    session_name TEXT,                            -- Human-readable name for live games
    game_number BIGINT,                           -- Sequential game number
    started_at TIMESTAMP WITH TIME ZONE,
    ended_at TIMESTAMP WITH TIME ZONE,
    end_session_json JSONB,                       -- Raw session data
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    
    UNIQUE(game_id, external_id),                 -- Prevent duplicate imports
    UNIQUE(game_id, game_number)                  -- Unique game numbers per game
);
```

#### Players Table
```sql
CREATE TABLE players (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id TEXT UNIQUE,                      -- PokerNow player ID (nullable)
    display_name TEXT NOT NULL,                   -- Player's display name
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);
```

#### Session Player Summaries Table
```sql
CREATE TABLE session_player_summaries (
    session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
    player_id UUID REFERENCES players(id) ON DELETE CASCADE,
    buy_in_sum BIGINT NOT NULL,                   -- Total buy-ins in cents
    cash_out_sum BIGINT NOT NULL,                 -- Total cash-outs in cents
    in_game BIGINT NOT NULL,                      -- Chips still in play (cents)
    net BIGINT NOT NULL,                          -- Net profit/loss (cents)
    names TEXT[] NOT NULL,                        -- Array of names used in session
    
    PRIMARY KEY (session_id, player_id)
);
```

#### Audit Log Table
```sql
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    game_id UUID REFERENCES games(id) ON DELETE SET NULL,
    session_id UUID REFERENCES sessions(id) ON DELETE SET NULL,
    actor_kind TEXT NOT NULL,                     -- 'admin_code' | 'system'
    actor_id TEXT,                                -- Actor identifier
    action TEXT NOT NULL,                         -- 'CREATE' | 'UPDATE' | 'DELETE' | 'IMPORT'
    target_table TEXT NOT NULL,                   -- Modified table name
    target_id TEXT NOT NULL,                      -- Modified record ID
    before JSONB,                                 -- Before state
    after JSONB,                                  -- After state
    at TIMESTAMP WITH TIME ZONE DEFAULT now()
);
```

### Relationships
- **Games** ↔ **Sessions**: One-to-many (cascading delete)
- **Games** ↔ **Players**: Many-to-many via `game_players` table
- **Sessions** ↔ **Players**: Many-to-many via `session_player_summaries`
- **Audit Log**: References games and sessions (soft references)

## 🌐 API Endpoints

### Game Management

#### GET /api/games/get_transactions
Import game data from PokerNow URL.
```bash
curl "http://localhost:8000/api/games/get_transactions?url=https://pokernow.club/games/ABC123"
```

#### POST /api/games/upload
Upload PokerNow session data.
```bash
curl -X POST http://localhost:8000/api/games/upload \
  -H "Content-Type: application/json" \
  -H "X-Admin-Code: YOUR_ADMIN_CODE" \
  -d '{
    "public_code": "C4QROK",
    "sessionId": "pokernow-session-id",
    "game_data": {...},
    "date": "2025-08-11T00:00:00",
    "gameNumber": 15
  }'
```

#### POST /api/games/upload_live
Upload live game session data.
```bash
curl -X POST http://localhost:8000/api/games/upload_live \
  -H "Content-Type: application/json" \
  -H "X-Admin-Code: YOUR_ADMIN_CODE" \
  -d '{
    "public_code": "C4QROK",
    "session_name": "Friday Night Poker",
    "players": [
      {"name": "Alice", "buy_in": 100.00, "cash_out": 120.00, "in_game": 0.00},
      {"name": "Bob", "buy_in": 100.00, "cash_out": 80.00, "in_game": 0.00}
    ],
    "date": "2025-08-11T00:00:00",
    "gameNumber": 15
  }'
```

### Analytics & Reporting

#### GET /api/games/{public_code}/summary
Get game summary with player statistics.
```bash
curl "http://localhost:8000/api/games/C4QROK/summary"
```

#### GET /api/games/{public_code}/ledger
Get detailed session ledger for admin view.
```bash
curl "http://localhost:8000/api/games/C4QROK/ledger"
```

#### GET /api/games/{public_code}/ledger-analysis
Advanced analytics and data validation.
```bash
curl "http://localhost:8000/api/games/C4QROK/ledger-analysis" \
  -H "X-Admin-Code: YOUR_ADMIN_CODE"
```

### Player Management

#### GET /api/games/{public_code}/unverified-players
Get players requiring verification.
```bash
curl "http://localhost:8000/api/games/C4QROK/unverified-players" \
  -H "X-Admin-Code: YOUR_ADMIN_CODE"
```

#### POST /api/games/{public_code}/verify-player
Link player names to external IDs.
```bash
curl -X POST "http://localhost:8000/api/games/C4QROK/verify-player" \
  -H "Content-Type: application/json" \
  -H "X-Admin-Code: YOUR_ADMIN_CODE" \
  -d '{
    "display_name": "Alice",
    "external_id": "pokernow_player_123"
  }'
```

## 🔧 Configuration

### Environment Variables
```bash
# Database Configuration
DATABASE_URL=postgresql+psycopg2://user:password@host:port/database

# Flask Configuration
PORT=8000
FLASK_ENV=development  # or 'production'

# Google Sheets (Optional)
# Service account JSON file path is hardcoded in sheets_service.py
```

### Google Sheets Integration Setup
1. **Create Google Cloud Project**
   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Create new project or select existing

2. **Enable APIs**
   ```bash
   # Enable Google Sheets API
   # Enable Google Drive API (for file access)
   ```

3. **Create Service Account**
   - Go to IAM & Admin > Service Accounts
   - Create service account
   - Generate JSON key file

4. **Configure Application**
   ```python
   # Update backend/src/services/sheets_service.py
   CREDENTIALS_PATH = "/path/to/your/service-account.json"
   ```

5. **Share Spreadsheet**
   - Share your Google Sheet with service account email
   - Grant "Editor" permissions

### Database Connection Pooling
```python
# Configured in src/db/database.py
engine = create_engine(
    DATABASE_URL,
    future=True,
    pool_pre_ping=True,        # Health check connections
    pool_size=10,              # Connection pool size
    max_overflow=20,           # Additional connections
    pool_recycle=3600          # Recycle connections hourly
)
```

## 🧪 Testing

### Unit Tests
```bash
# Run all tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_live_game_service.py

# Run with coverage
python -m pytest --cov=src tests/
```

### API Testing
```bash
# Test live game endpoint
python scripts/test_live_game.py

# Test PokerNow import
python scripts/test_pokernow_import.py
```

### Manual Testing
```bash
# Start test database
docker run -d --name test-postgres \
  -e POSTGRES_USER=testuser \
  -e POSTGRES_PASSWORD=testpass \
  -e POSTGRES_DB=test_poker \
  -p 5433:5432 postgres:16

# Run tests against test database
export DATABASE_URL="postgresql+psycopg2://testuser:testpass@localhost:5433/test_poker"
python -m pytest
```

## 🔍 Debugging & Monitoring

### Logging Configuration
```python
# Configured in src/app.py
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s'
)
```

### Database Query Logging
```python
# Enable SQLAlchemy query logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
```

### Audit Trail Monitoring
```sql
-- View recent audit entries
SELECT actor_kind, action, target_table, at 
FROM audit_log 
ORDER BY at DESC 
LIMIT 20;

-- Track specific game changes
SELECT * FROM audit_log 
WHERE game_id = 'your-game-uuid'
ORDER BY at DESC;
```

### Performance Monitoring
```sql
-- Check slow queries (PostgreSQL)
SELECT query, mean_exec_time, total_exec_time 
FROM pg_stat_statements 
ORDER BY mean_exec_time DESC;

-- Monitor connection usage
SELECT * FROM pg_stat_activity 
WHERE datname = 'poker_analytics';
```

## 🚢 Deployment

### Docker Production Setup
```dockerfile
# Multi-stage build for production
FROM python:3.11-slim as builder
COPY requirements.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements.txt

FROM python:3.11-slim
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY . /app
WORKDIR /app
EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "src.app:app"]
```

### Production Environment Variables
```bash
# Production settings
FLASK_ENV=production
DATABASE_URL=postgresql://user:password@prod-db:5432/poker_analytics

# Security
SECRET_KEY=your-secret-key-here

# Performance
SQLALCHEMY_POOL_SIZE=20
SQLALCHEMY_MAX_OVERFLOW=40
```

### Database Migration in Production
```bash
# Run migrations before deployment
docker run --rm -v $(pwd):/app \
  -e DATABASE_URL=$PROD_DATABASE_URL \
  poker-analytics-backend \
  python -m alembic upgrade head
```

## 🔐 Security Considerations

### Authentication
- Admin codes are validated via headers (`X-Admin-Code`)
- No user authentication system (single-game focus)
- Admin codes should be long, random strings

### Data Protection
- All financial amounts stored as integers (cents) to avoid floating-point errors
- Input validation on all endpoints
- SQL injection protection via SQLAlchemy ORM
- XSS protection via JSON serialization

### Audit Trail
- Complete audit log of all data modifications
- Actor tracking for all changes
- Immutable audit entries (append-only)

### Rate Limiting (Recommended)
```python
# Add to production deployment
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["1000 per hour"]
)
```

## 🐛 Troubleshooting

### Common Issues

**Import Error: No module named 'src'**
```bash
# Set Python path
export PYTHONPATH=/path/to/backend/src
# Or run from backend directory
cd backend && python src/app.py
```

**Database Connection Error**
```bash
# Check PostgreSQL is running
pg_isready -h localhost -p 5432

# Test connection
python -c "import sqlalchemy; sqlalchemy.create_engine('$DATABASE_URL').connect()"
```

**Google Sheets API Error**
```bash
# Check service account file exists
ls -la mm-poker-tracker-*.json

# Verify permissions
python -c "
import json
with open('your-service-account.json') as f:
    data = json.load(f)
    print(f'Service Account: {data[\"client_email\"]}')
"
```

**Alembic Migration Error**
```bash
# Check current migration state
alembic current

# View migration history
alembic history

# Reset to specific revision
alembic downgrade <revision>
alembic upgrade head
```

### Debug Mode
```python
# Enable debug logging
import logging
logging.getLogger().setLevel(logging.DEBUG)

# Enable Flask debug mode
app.run(debug=True, host="0.0.0.0", port=8000)
```

## 📈 Performance Tuning

### Database Optimization
```sql
-- Add indexes for common queries
CREATE INDEX idx_sessions_game_started_at ON sessions(game_id, started_at);
CREATE INDEX idx_players_display_name_lower ON players(LOWER(display_name));
CREATE INDEX idx_audit_log_game_at ON audit_log(game_id, at);
```

### Connection Pool Tuning
```python
# Adjust for your workload
engine = create_engine(
    DATABASE_URL,
    pool_size=20,              # Increase for high concurrency
    max_overflow=40,           # Additional connections
    pool_timeout=30,           # Connection wait timeout
    pool_recycle=7200          # Recycle connections every 2 hours
)
```

### Caching Considerations
- Game summaries can be cached (they change infrequently)
- Player verification data is suitable for caching
- Audit logs should never be cached

## 🤝 Contributing

### Code Style
- Follow PEP 8 guidelines
- Use type hints where appropriate
- Document all functions with docstrings
- Keep service methods focused and testable

### Adding New Endpoints
1. Add route to `src/routes/game.py`
2. Implement business logic in appropriate service
3. Add comprehensive tests
4. Update API documentation
5. Add audit logging if data is modified

### Database Schema Changes
1. Create Alembic migration: `alembic revision -m "Description"`
2. Implement `upgrade()` and `downgrade()` functions
3. Test migration on sample data
4. Update model classes in `src/db/models.py`

---

**For questions or issues, check the main project README or create an issue on GitHub.**