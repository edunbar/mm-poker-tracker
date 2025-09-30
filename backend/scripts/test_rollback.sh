#!/bin/bash

# Rollback Testing Script
# This script helps test the rollback procedure in a safe environment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}    Rollback Procedure Test Script${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Configuration
TEST_DB="poker_analytics_rollback_test"
BACKUP_DIR="./backups/rollback_test_$(date +%Y%m%d_%H%M%S)"

# Parse database credentials from DATABASE_URL or use defaults
if [ -z "$DATABASE_URL" ]; then
    DB_USER="postgres"
    DB_PASS="postgres"
    DB_HOST="localhost"
    DB_PORT="5432"
else
    # Extract credentials from DATABASE_URL
    DB_USER=$(echo "$DATABASE_URL" | sed -n 's|.*://\([^:]*\):.*|\1|p')
    DB_PASS=$(echo "$DATABASE_URL" | sed -n 's|.*://[^:]*:\([^@]*\)@.*|\1|p')
    DB_HOST=$(echo "$DATABASE_URL" | sed -n 's|.*@\([^:]*\):.*|\1|p')
    DB_PORT=$(echo "$DATABASE_URL" | sed -n 's|.*:\([0-9]*\)/.*|\1|p')
fi

# Override DATABASE_URL to point to test database
export DATABASE_URL="postgresql+psycopg2://${DB_USER}:${DB_PASS}@${DB_HOST}:${DB_PORT}/${TEST_DB}"
export PGPASSWORD="${DB_PASS}"

echo -e "${BLUE}Configuration:${NC}"
echo "  Database URL: $DATABASE_URL"
echo "  Backup directory: $BACKUP_DIR"
echo ""

# Step 1: Create test database
echo -e "${BLUE}━━━ Step 1: Create Test Database ━━━${NC}"
echo "Creating test database: $TEST_DB"
psql -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" -d postgres -c "DROP DATABASE IF EXISTS ${TEST_DB};" 2>/dev/null || true
psql -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" -d postgres -c "CREATE DATABASE ${TEST_DB};" || {
    echo -e "${RED}❌ Failed to create test database${NC}"
    echo -e "${YELLOW}Make sure PostgreSQL is running and accessible${NC}"
    exit 1
}
echo -e "${GREEN}✅ Test database created${NC}"
echo ""

# Step 2: Apply initial migrations
echo -e "${BLUE}━━━ Step 2: Apply Initial Migrations ━━━${NC}"
echo "Running: python -m alembic upgrade head"
python -m alembic upgrade head || {
    echo -e "${RED}❌ Failed to apply migrations${NC}"
    exit 1
}

# Get current migration version
INITIAL_VERSION=$(python -m alembic current | head -n 1 | awk '{print $1}')
echo -e "${GREEN}✅ Migrations applied${NC}"
echo "  Current version: $INITIAL_VERSION"
echo ""

# Step 3: Insert test data
echo -e "${BLUE}━━━ Step 3: Insert Test Data ━━━${NC}"
python << EOF
import sys
sys.path.insert(0, 'src')
from db.database import get_db_session
from db.models import Game, Player, Session
from datetime import datetime, timezone

session = get_db_session()
try:
    # Create a test game
    game = Game(
        public_code='ROLLTEST',
        admin_code='ROLLADMIN',
        name='Rollback Test Game',
        location='Test Location'
    )
    session.add(game)
    session.flush()

    # Create a test player
    player = Player(
        external_id='test_player_1',
        name='Test Player',
        email='test@example.com'
    )
    session.add(player)

    # Create a test session
    test_session = Session(
        game_id=game.id,
        external_id='test_session_1',
        log_filename='test.csv',
        start_date=datetime.now(timezone.utc),
        ingested_at=datetime.now(timezone.utc),
        raw_data={'test': 'data'}
    )
    session.add(test_session)

    session.commit()
    print("✅ Test data inserted successfully")
    print(f"  Game ID: {game.id}")
    print(f"  Player ID: {player.id}")
    print(f"  Session ID: {test_session.id}")
except Exception as e:
    session.rollback()
    print(f"❌ Failed to insert test data: {e}")
    sys.exit(1)
finally:
    session.close()
EOF

echo ""

# Step 4: Create backup
echo -e "${BLUE}━━━ Step 4: Create Database Backup ━━━${NC}"
mkdir -p "$BACKUP_DIR"
BACKUP_FILE="$BACKUP_DIR/database_backup.sql"

echo "Creating backup: $BACKUP_FILE"
pg_dump -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" -d "$TEST_DB" -f "$BACKUP_FILE" || {
    echo -e "${RED}❌ Failed to create backup${NC}"
    exit 1
}

# Get backup file size
BACKUP_SIZE=$(ls -lh "$BACKUP_FILE" | awk '{print $5}')
echo -e "${GREEN}✅ Backup created successfully${NC}"
echo "  Backup file: $BACKUP_FILE"
echo "  Backup size: $BACKUP_SIZE"
echo ""

# Step 5: Simulate a problematic migration
echo -e "${BLUE}━━━ Step 5: Simulate Problematic Change ━━━${NC}"
echo -e "${YELLOW}⚠️  Simulating a destructive operation...${NC}"
psql -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" -d "$TEST_DB" -c "DELETE FROM games WHERE public_code = 'ROLLTEST';" || {
    echo -e "${RED}❌ Failed to simulate problematic change${NC}"
    exit 1
}
echo -e "${GREEN}✅ Problematic change applied (test data deleted)${NC}"
echo ""

# Verify data is gone
echo "Verifying data is deleted..."
python << EOF
import sys
sys.path.insert(0, 'src')
from db.database import get_db_session
from db.models import Game

session = get_db_session()
try:
    game = session.query(Game).filter_by(public_code='ROLLTEST').first()
    if game:
        print("❌ ERROR: Data still exists!")
        sys.exit(1)
    else:
        print("✅ Confirmed: Test data has been deleted")
except Exception as e:
    print(f"❌ Error checking data: {e}")
    sys.exit(1)
finally:
    session.close()
EOF

echo ""

# Step 6: Perform rollback
echo -e "${BLUE}━━━ Step 6: Perform Rollback ━━━${NC}"
echo -e "${YELLOW}⚠️  Rolling back to previous state...${NC}"

# Drop and recreate database
psql -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" -d postgres -c "DROP DATABASE ${TEST_DB};" || {
    echo -e "${RED}❌ Failed to drop database${NC}"
    exit 1
}
psql -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" -d postgres -c "CREATE DATABASE ${TEST_DB};" || {
    echo -e "${RED}❌ Failed to recreate database${NC}"
    exit 1
}

# Restore from backup
echo "Restoring from backup: $BACKUP_FILE"
psql -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" -d "$TEST_DB" -f "$BACKUP_FILE" > /dev/null 2>&1 || {
    echo -e "${RED}❌ Failed to restore from backup${NC}"
    exit 1
}

echo -e "${GREEN}✅ Database restored from backup${NC}"
echo ""

# Step 7: Verify rollback success
echo -e "${BLUE}━━━ Step 7: Verify Rollback Success ━━━${NC}"
echo "Checking if data was restored..."
python << EOF
import sys
sys.path.insert(0, 'src')
from db.database import get_db_session
from db.models import Game, Player

session = get_db_session()
try:
    game = session.query(Game).filter_by(public_code='ROLLTEST').first()
    if not game:
        print("❌ ERROR: Data was not restored!")
        sys.exit(1)

    player = session.query(Player).filter_by(external_id='test_player_1').first()
    if not player:
        print("❌ ERROR: Player data was not restored!")
        sys.exit(1)

    print("✅ Rollback verification successful")
    print(f"  Game restored: {game.name}")
    print(f"  Player restored: {player.name}")

except Exception as e:
    print(f"❌ Error during verification: {e}")
    sys.exit(1)
finally:
    session.close()
EOF

echo ""

# Step 8: Cleanup
echo -e "${BLUE}━━━ Step 8: Cleanup ━━━${NC}"
echo -e "${YELLOW}Do you want to keep the test database and backup? (y/N)${NC}"
read -r KEEP_TEST

if [[ ! "$KEEP_TEST" =~ ^[Yy]$ ]]; then
    echo "Cleaning up test database..."
    psql -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" -d postgres -c "DROP DATABASE ${TEST_DB};" 2>/dev/null || true
    echo -e "${GREEN}✅ Test database dropped${NC}"
else
    echo -e "${BLUE}ℹ️  Test database kept: $TEST_DB${NC}"
    echo -e "${BLUE}ℹ️  Backup kept: $BACKUP_DIR${NC}"
fi

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}    ✅ Rollback Test Complete!${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${GREEN}Summary:${NC}"
echo "  1. ✅ Created test database"
echo "  2. ✅ Applied migrations"
echo "  3. ✅ Inserted test data"
echo "  4. ✅ Created backup"
echo "  5. ✅ Simulated problematic change"
echo "  6. ✅ Performed rollback"
echo "  7. ✅ Verified rollback success"
echo ""
echo -e "${BLUE}Rollback procedure validated successfully!${NC}"