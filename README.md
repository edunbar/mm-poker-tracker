# 🃏 HomeGame

A comprehensive web application for analyzing poker games from both PokerNow sessions and live home games. Built with Flask backend, React frontend, PostgreSQL database, and Google Sheets integration.

## ✨ Features

- **PokerNow Import**: Import game sessions directly from PokerNow URLs
- **Live Game Entry**: Manual entry for home games with balance validation
- **Live Game Tracking**: Real-time buy-in/cash-out management with instant SSE updates
- **Player Management**: Track players across sessions with verification system
- **Advanced Analytics**: Comprehensive game summaries and player statistics
- **Google Sheets Integration**: Automatic data export to spreadsheets
- **Audit System**: Complete audit trail of all changes
- **Balance Detection**: Automatic validation of game money flows

## 🏗️ Architecture

```
poker-analytics/
├── backend/                # Flask API server
│   ├── src/
│   │   ├── app.py         # Main Flask application
│   │   ├── db/            # Database models and config
│   │   ├── routes/        # API endpoints
│   │   └── services/      # Business logic layer
│   ├── migrations/        # Database migrations (Alembic)
│   └── requirements.txt   # Python dependencies
├── frontend/              # React application
│   ├── src/
│   │   ├── features/      # Feature-based components
│   │   ├── shared/        # Reusable components
│   │   └── app/           # App-level routing and layout
│   └── package.json       # Node.js dependencies
├── docker-compose.yml     # Docker services definition
└── .env                   # Environment configuration
```

## 🚀 Quick Start (Docker - Recommended)

### Prerequisites
- Docker and Docker Compose
- Git

### 1. Clone the Repository
```bash
git clone <repository-url>
cd poker-analytics
```

### 2. Environment Setup
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env file with your settings (optional - defaults work for development)
# Key settings to review:
# - POSTGRES_PASSWORD: Database password
# - REACT_APP_PUBLIC_CODE: Your game's public code  
# - REACT_APP_ADMIN_CODE: Your game's admin code (should be 32+ characters)

# The .env.example file contains detailed documentation for all configuration options
```

### 3. Start All Services
```bash
docker-compose up -d
```

This starts:
- **PostgreSQL** database (port 5432)
- **Backend** API server (port 8000) 
- **pgAdmin** database UI (port 5050)

### 4. Access the Application

**Frontend Development Server** (run separately):
```bash
cd frontend
npm install
npm start
```
Open [http://localhost:3000](http://localhost:3000)

**API Server**: [http://localhost:8000](http://localhost:8000)

**pgAdmin** (Database UI): [http://localhost:5050](http://localhost:5050)
- Email: `admin@example.com`
- Password: `adminadmin`

### 5. First Time Setup

The database will be automatically initialized with all necessary tables when the backend starts.

## 🛠️ Manual Development Setup

### Prerequisites
- Python 3.11+
- Node.js 16+
- PostgreSQL 16+

### Backend Setup
```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate

# Install dependencies
pip install -r requirements.txt

# Set up database
export DATABASE_URL="postgresql+psycopg2://pokeruser:supersecret@localhost:5432/poker_analytics"

# Run migrations
alembic upgrade head

# Start development server
python src/app.py
```

### Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm start
```

### Database Setup (Manual)
```sql
-- Connect to PostgreSQL and create database
CREATE DATABASE poker_analytics;
CREATE USER pokeruser WITH ENCRYPTED PASSWORD 'supersecret';
GRANT ALL PRIVILEGES ON DATABASE poker_analytics TO pokeruser;
```

## 🎮 Usage Guide

### For Game Players
1. Navigate to `http://localhost:3000`
2. View game summaries and statistics
3. Check your performance across sessions

### For Game Administrators
1. **Access admin features**: Click "Login as Admin" and enter your admin code
2. **Import PokerNow games**: Go to "PokerNow Import" and paste game URLs
3. **Enter live games**: Go to "Live Game Entry" and manually input results
4. **Manage players**: Use "Player Verification" to link player names
5. **Analyze data**: Review "Ledger Analysis" for detailed insights

### Live Game Tracking
**Real-time game management for players and admins:**

**For Admins:**
1. Click **"Start Live Game"** on your game dashboard
2. Configure settings (min/max buy-in, blinds)
3. Share the **4-character join code** with players (e.g., "A7X2")
4. Approve/reject player buy-in and cash-out requests in real-time
5. Monitor game balance and active players
6. Close the game when finished (automatically saves final ledger)

**For Players:**
1. Join using the link: `https://homegame.gg/join-live/{joinCode}`
2. Request buy-ins and cash-outs via mobile-friendly UI
3. See instant updates when transactions are approved (via SSE)
4. Track your chip count and net result in real-time
5. View other players' chip counts and activity

**Real-Time Features:**
- **Instant Updates**: All participants see changes within 50ms via Server-Sent Events
- **Auto-Reconnection**: Handles network interruptions gracefully
- **Balance Validation**: Zero-sum financial integrity checks
- **Audit Trail**: Complete transaction history

See detailed documentation:
- **User Guide**: `docs/LIVE_GAME_USER_GUIDE.md`
- **API Reference**: `docs/LIVE_GAME_API.md`
- **SSE Production Setup**: `docs/SSE_REDIS_UPGRADE.md`

### API Usage
```bash
# Import PokerNow game
curl -X POST http://localhost:8000/api/games/upload \
  -H "Content-Type: application/json" \
  -H "X-Admin-Code: YOUR_ADMIN_CODE" \
  -d '{
    "public_code": "C4QROK",
    "sessionId": "pokernow-session-id",
    "game_data": {...}
  }'

# Submit live game
curl -X POST http://localhost:8000/api/games/upload_live \
  -H "Content-Type: application/json" \
  -H "X-Admin-Code: YOUR_ADMIN_CODE" \
  -d '{
    "public_code": "C4QROK",
    "session_name": "Friday Night Poker",
    "players": [
      {"name": "Alice", "buy_in": 100.00, "cash_out": 120.00, "in_game": 0.00}
    ]
  }'

# Create Live Game (real-time tracking)
curl -X POST http://localhost:8000/api/live-games \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "game_id": "550e8400-e29b-41d4-a716-446655440000",
    "min_buy_in": 20.00,
    "max_buy_in": 200.00,
    "small_blind": 0.25,
    "big_blind": 0.50
  }'

# Join Live Game as participant
curl -X POST http://localhost:8000/api/live-games/A7X2/join \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Request buy-in
curl -X POST http://localhost:8000/api/live-games/A7X2/transactions/buy-in \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"amount": 50.00}'

# Approve transaction (admin)
curl -X POST http://localhost:8000/api/live-games/A7X2/transactions/TRANSACTION_ID/approve \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Close Live Game (admin)
curl -X POST http://localhost:8000/api/live-games/A7X2/close \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Live Game API Documentation**: See `docs/LIVE_GAME_API.md` for complete endpoint reference with request/response schemas, error codes, and SSE event types.

## 🔧 Configuration

### Environment Variables Reference

#### Backend Environment Variables

**Required for all environments:**

| Variable | Description | Example | Default |
|----------|-------------|---------|---------|
| `FLASK_ENV` | Environment mode | `development`, `staging`, `production` | `development` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+psycopg2://user:pass@host/db` | - |
| `USE_DOMAIN_SERVICES` | Enable V2 domain-driven services | `true`, `false` | `false` |

**Production/Staging specific:**

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `ALLOWED_ORIGINS` | CORS allowed origins (comma-separated) | `https://homegame.gg,https://www.homegame.gg` | Yes |
| `DATABASE_URL` | Cloud SQL connection with socket path | `postgresql://user:pass@/db?host=/cloudsql/project:region:instance` | Yes |

**Optional:**

| Variable | Description | Default |
|----------|-------------|---------|
| `PORT` | Server port | `8000` |
| `PYTHONPATH` | Python module search path (must be `src` for imports) | `src` |

#### Frontend Environment Variables

**Development (`.env.local`):**

| Variable | Description | Example |
|----------|-------------|---------|
| `REACT_APP_API_URL` | Backend API URL | `http://localhost:8000` |

**Staging (`frontend/.env.staging.local` - gitignored):**

| Variable | Description | Value |
|----------|-------------|-------|
| `REACT_APP_API_URL` | Staging backend URL | `https://poker-backend-staging-6t2w34itkq-uc.a.run.app` |

**Production (`frontend/.env.production` - tracked in git):**

| Variable | Description | Value |
|----------|-------------|-------|
| `REACT_APP_API_URL` | Production backend URL | `https://poker-backend-6t2w34itkq-uc.a.run.app` |

> ⚠️ **Important**: `frontend/.env.production` is tracked in git because it only contains the public backend URL (not secrets). Backend `.env` files are gitignored because they contain database credentials.

#### GCP Cloud Run Configuration

**Managed via:**
- Production: `backend/cloud-run-env.yaml`
- Staging: `backend/cloud-run-env-staging.yaml`

These files are tracked in git and deployed via GitHub Actions.

#### Vercel Configuration

**Managed via Vercel Dashboard:**
- Project: HomeGame
- Production: `REACT_APP_API_URL` → `https://poker-backend-6t2w34itkq-uc.a.run.app`
- Preview deployments: Use staging backend URL

### Local Development (.env)

For Docker-based development, copy `.env.example` to `.env`:

```bash
# Database Configuration
POSTGRES_USER=pokeruser
POSTGRES_PASSWORD=supersecret
POSTGRES_DB=poker_analytics
POSTGRES_PORT=5432

# Backend Configuration
PORT=8000
DATABASE_URL=postgresql+psycopg2://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:${POSTGRES_PORT}/${POSTGRES_DB}
USE_DOMAIN_SERVICES=true

# pgAdmin Configuration
PGADMIN_DEFAULT_EMAIL=admin@example.com
PGADMIN_DEFAULT_PASSWORD=adminadmin
```

### Common Configuration Issues

**Frontend calling wrong backend:**
- Check `REACT_APP_API_URL` in Vercel environment variables
- For production, verify `frontend/.env.production` has correct URL
- Clear Vercel build cache if changes don't take effect

**Database connection errors:**
- Development: Check `DATABASE_URL` in `.env` matches Docker service name (`db`)
- Production/Staging: Verify Cloud SQL instance name and socket path
- Ensure `PYTHONPATH=src` is set for backend imports

**CORS errors:**
- Add frontend URL to `ALLOWED_ORIGINS` in backend environment
- Format: comma-separated, no trailing slashes
- Example: `https://homegame.gg,https://www.homegame.gg`

### Google Sheets Integration (Optional)
1. Create a Google Cloud project
2. Enable Google Sheets API
3. Create service account credentials
4. Download JSON key file as `backend/mm-poker-tracker-[id].json`
5. Update hardcoded path in `backend/src/services/sheets_service.py`

## 🧪 Testing

### Backend Tests
```bash
cd backend
source venv/bin/activate
python -m pytest tests/
```

### Frontend Tests
```bash
cd frontend
npm test
```

### API Testing
```bash
# Test live game endpoint
curl -X POST http://localhost:8000/api/games/upload_live \
  -H "Content-Type: application/json" \
  -H "X-Admin-Code: 2LT8wByw4sMLAwB_ISq2TMRwJ6zaUZ1oy4w7y4WQscE" \
  -d '{
    "public_code": "C4QROK",
    "session_name": "Test Game",
    "players": [
      {"name": "Alice", "buy_in": 100.00, "cash_out": 120.00, "in_game": 0.00},
      {"name": "Bob", "buy_in": 100.00, "cash_out": 80.00, "in_game": 0.00}
    ]
  }'
```

## 🔍 Troubleshooting

### Common Issues

**Database Connection Error**
```bash
# Check if PostgreSQL is running
docker-compose ps

# View database logs
docker-compose logs db

# Reset database
docker-compose down -v
docker-compose up -d
```

**Frontend Won't Start**
```bash
# Clear node_modules and reinstall
cd frontend
rm -rf node_modules package-lock.json
npm install
npm start
```

**Backend Import Error**
```bash
# Check Python path
cd backend
export PYTHONPATH=/app/src
source venv/bin/activate
python src/app.py
```

**Google Sheets Integration Issues**
- Verify service account JSON file is correctly placed
- Check file permissions
- Ensure Google Sheets API is enabled in Google Cloud Console

### Useful Commands
```bash
# View all running containers
docker-compose ps

# View application logs
docker-compose logs -f backend
docker-compose logs -f db

# Access database directly
docker-compose exec db psql -U pokeruser -d poker_analytics

# Rebuild containers
docker-compose down
docker-compose up --build

# Run database migrations
docker-compose exec backend python -m alembic upgrade head
```

## 📊 Database Schema

**Key Tables:**
- `games`: Game containers with public/admin codes
- `sessions`: Individual poker sessions (PokerNow or live)
- `players`: Player entities across all games  
- `session_player_summaries`: Per-session player statistics
- `audit_log`: Complete audit trail of changes

## 🚢 Deployment

**Production Infrastructure:**
- **Frontend**: Vercel → https://homegame.gg
- **Backend**: GCP Cloud Run → `poker-backend` service
- **Database**: GCP Cloud SQL → PostgreSQL 16
- **CI/CD**: GitHub Actions (automated testing + deployment)

**Staging Infrastructure:**
- **Frontend**: Vercel → https://home-game-staging.vercel.app
- **Backend**: GCP Cloud Run → `poker-backend-staging` service
- **Database**: GCP Cloud SQL → `home_game_staging` database

### Deployment Process

For detailed deployment procedures, pre-flight checklists, rollback procedures, and troubleshooting guides, see:

**📋 [DEPLOYMENT.md](./DEPLOYMENT.md)** - Comprehensive deployment documentation including:
- Pre-deployment checklist (tests, config verification, database migrations)
- Step-by-step deployment process for staging and production
- Post-deployment monitoring and verification
- Rollback procedures
- Common issues and solutions
- Infrastructure change management

### Quick Deploy

**Staging:**
1. Push changes to GitHub
2. Go to [GitHub Actions](https://github.com/edunbar/mm-poker-tracker/actions)
3. Run "Deploy" workflow → Select "staging" environment
4. Monitor deployment and health checks

**Production:**
1. Verify staging deployment successful
2. Run "Deploy" workflow → Select "production" environment
3. ⚠️ **Do NOT skip migration check** unless intentional
4. Monitor for 30 minutes after deployment

### Emergency Rollback

```bash
# Backend rollback
gcloud run revisions list --service=poker-backend --region=us-central1
gcloud run services update-traffic poker-backend \
  --region=us-central1 \
  --to-revisions=PREVIOUS_REVISION=100

# Frontend rollback
# Go to Vercel → Deployments → Select previous deployment → Redeploy
```

For complete rollback procedures including database migrations, see [DEPLOYMENT.md](./DEPLOYMENT.md).

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes
4. Run tests: `npm test` and `python -m pytest`
5. Commit changes: `git commit -m 'Add amazing feature'`
6. Push to branch: `git push origin feature/amazing-feature`
7. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📞 Support

- **Issues**: Create an issue in the GitHub repository
- **Documentation**:
  - General: `backend/README.md` and `frontend/README.md` for detailed component documentation
  - **Live Game**: `docs/LIVE_GAME_USER_GUIDE.md` for user guide and troubleshooting
  - **API Reference**: `docs/LIVE_GAME_API.md` for complete endpoint documentation
  - **SSE Production**: `docs/SSE_REDIS_UPGRADE.md` for multi-instance deployment
- **API Documentation**: Visit `http://localhost:8000/api/games/` when running locally

---

**Happy Poker Analytics!** 🎰