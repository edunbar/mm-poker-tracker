# HomeGame Poker Application - High-Level Overview

## What Is HomeGame?

**HomeGame** (https://homegame.gg) is a poker analytics and game management platform for home poker games. It helps poker groups track, analyze, and settle their games by importing data from PokerNow or tracking live games in real-time.

### Core Problem Solved
Home poker groups struggle to:
- Track who owes who money across multiple sessions
- Analyze player performance and statistics
- Keep detailed records of game history
- Manage buy-ins and cash-outs during live games
- Import and organize data from online poker platforms

### Solution
A centralized platform where groups can:
1. **Create a game** (get a shareable code)
2. **Import PokerNow sessions** or track live games
3. **View analytics** (player stats, hand history, trends)
4. **Track payments** and balances automatically
5. **Settle up** with accurate financial records

---

## User Types

### 1. Public Users (No Account)
Can access any game via public code to view:
- Game summaries and leaderboards
- Player statistics
- Hand analytics
- Payment ledger (who owes who)
- Game rules

### 2. Authenticated Users
Can create accounts to:
- Create and own games
- View all their games in one dashboard
- Claim player identities across games
- Join live games and log transactions
- Never lose admin codes (tied to account)

### 3. Game Admins
Anyone with the **admin code** for a game can:
- Import PokerNow session data
- Create and manage live games
- Approve buy-in and cash-out requests
- Edit game data and ledger entries
- Manage game rules
- View audit logs
- Merge duplicate player identities

**Note**: Admin access is code-based, not account-based. Anyone with the admin code has full control.

---

## Core Features

### 1. Game Management

#### Create Game
- Generate unique public code (5 characters, e.g., "C4QRO")
- Generate unique admin code (long secret token)
- Optional: Set game title (e.g., "Thursday Night Home Game")
- Share public code with players, keep admin code secret

#### Join Game
- Enter public code to view game
- Optional: Enter admin code for management access
- No account required for viewing

#### Game Settings
- Edit game title
- Manage game rules (markdown supported)
- Configure poker statistics thresholds
- View game audit log

---

### 2. Session Ingestion (PokerNow Import)

#### What It Does
Imports completed poker sessions from PokerNow.com into your game for tracking and analysis.

#### How It Works
1. Admin enters PokerNow session URL
2. System fetches game data via API
3. Parses player data, hands, transactions
4. Creates session record with:
   - Player buy-ins and cash-outs
   - Hand-by-hand history
   - Player statistics (VPIP, PFR, aggression)
   - Net win/loss for each player
5. Financial integrity validation (zero-sum check)
6. Updates payment balances automatically

#### Supported Data
- **Player summaries**: Buy-ins, cash-outs, in-game chips, net results
- **Hand logs**: Every hand played with actions and results
- **Event logs**: Detailed hand replayer data
- **Time series**: Game duration, hand timing

#### Financial Validation
- **Zero-sum invariant**: Total buy-ins = Total cash-outs + In-game chips
- Prevents data corruption
- Alerts on discrepancies
- Atomic transactions (all-or-nothing)

---

### 3. Live Game Tracking

#### What It Does
Real-time tracking of active poker games with buy-ins, cash-outs, and player balances.

#### Live Game Flow
1. **Admin creates live game**:
   - Set blinds, min/max buy-in
   - Generate unique join code (4 chars, e.g., "A3X7")
   - Share join code with players

2. **Players join**:
   - Enter join code
   - Create account or log in
   - Choose display name for game

3. **During game**:
   - Players log buy-ins and cash-outs
   - Transactions pending until admin approves
   - Real-time balance tracking
   - Admin view shows all pending transactions

4. **After game**:
   - Admin closes game
   - Final balances calculated
   - Session created for historical tracking
   - Payment ledger updated

#### Admin Controls
- Approve/reject buy-in requests
- Approve/reject cash-out requests
- Edit transaction amounts
- Track transaction history with edits
- See current chip counts for all players
- Close game and finalize session

#### Player View
- See their own buy-ins and cash-outs
- View current balance
- See pending transactions
- Simple buy-in/cash-out buttons

---

### 4. Analytics & Statistics

#### Game Summary Dashboard
**Aggregate statistics across all sessions**:
- Total hands played
- Total buy-ins and cash-outs
- Biggest winners and losers
- Player leaderboard (sorted by net profit)
- Session-by-session breakdown
- Interactive charts and graphs

#### Player Statistics
For each player across all sessions:
- **Financial**: Net win/loss, ROI, buy-in average
- **Poker stats**: VPIP, PFR, aggression frequency
- **Playing style**: Tight/Loose, Passive/Aggressive classification
- **Hand count**: Total hands played, sessions participated
- **Trend analysis**: Win rate over time

#### Advanced Analytics
- Session comparison
- Player vs player head-to-head
- Time-based analysis (win rate by session)
- Statistical anomaly detection

#### Hand Analytics (Replayer)
- Hand-by-hand replayer
- Action history for each hand
- Player hole cards (if available)
- Community cards progression
- Pot size tracking
- Winner/loser identification

---

### 5. Payment Ledger System

#### What It Tracks
Real-world money transfers between players outside of poker sessions.

#### Automatic Balance Calculation
For each player, the system calculates:
```
Poker Net = Σ(cash_outs) - Σ(buy_ins)
Payments Net = Σ(received) - Σ(paid)
Balance = Poker Net + Payments Net
```

**Positive balance** = Player is owed money
**Negative balance** = Player owes money

#### Recording Payments
Admins can log payments:
- Who paid who
- Amount
- Date
- Payment method (Venmo, Zelle, Cash, etc.)
- Optional notes and reference IDs
- Status (pending, completed, cancelled)

#### Payment Features
- Prevents duplicate payments (via reference ID)
- Tracks balance negative timestamps (when player went into debt)
- Shows payment history
- Suggests who owes who based on balances
- Auto-updates after every session import

---

### 6. Game Ledger Management

#### What It Shows
Detailed financial view of all sessions with:
- Session-by-session breakdown
- Player buy-ins and cash-outs per session
- Running balances
- Discrepancy detection

#### Admin Capabilities
- **Edit ledger entries**: Fix data entry errors
- **Delete ledger entries**: Remove incorrect sessions
- **Adjust balances**: Manual corrections (tracked in audit log)
- **Merge duplicate players**: Consolidate identities

#### Financial Integrity
- Real-time zero-sum validation
- Highlights discrepancies with red warnings
- Shows financial health of game
- Tracks every edit in audit log
- Rollback capability on errors

#### Ledger Analysis Page
Admin tool showing:
- Total buy-ins vs cash-outs
- In-game chips outstanding
- Zero-sum status (✓ or ✗)
- Session-level discrepancies
- Player-level anomalies

---

### 7. Audit Logging

#### What Gets Logged
Every action on the game:
- Session imports
- Ledger edits and deletions
- Payment recordings
- Rule changes
- Player identity merges
- Admin actions

#### Audit Log Fields
- **Who**: User or admin code
- **What**: Action type (CREATE, UPDATE, DELETE)
- **When**: Timestamp
- **Where**: Target table and ID
- **Before/After**: JSONB snapshots of data
- **Context**: IP address, notes

#### Use Cases
- Dispute resolution ("Who changed this?")
- Rollback data errors
- Compliance and transparency
- Trust verification for players

---

### 8. Game Rules Documentation

#### Features
- Markdown-supported rule pages
- Ordered rule list
- Editable by admins
- Public viewing (no admin code needed)
- Example rules:
  - Betting structures
  - House rules
  - Buy-in policies
  - Cash-out procedures
  - Dispute resolution

---

## User Workflows

### Workflow A: PokerNow Game Group (Most Common)

**Setup** (One-time):
1. Game host creates game on HomeGame
2. Gets public code and admin code
3. Shares public code in group chat

**After Each PokerNow Session**:
1. Host copies PokerNow session URL
2. Navigates to HomeGame admin page
3. Pastes URL and clicks "Import"
4. System fetches and processes data
5. Players can view updated stats

**Settling Up**:
1. Players check payment ledger
2. See who owes who
3. Make payments (Venmo, Zelle, etc.)
4. Host records payments in HomeGame
5. Balances update automatically

**Benefits**:
- Historical record of all games
- Accurate financial tracking
- Player performance analytics
- Dispute resolution via audit log

---

### Workflow B: Live Home Game (No PokerNow)

**Before Game**:
1. Host creates live game on HomeGame
2. Sets blinds and buy-in limits
3. Gets 4-character join code
4. Shares join code with players

**During Game**:
1. Players join via join code (accounts required)
2. Players log buy-ins when they buy chips
3. Host approves buy-ins
4. Players log cash-outs when they leave
5. Host approves cash-outs
6. Host can edit amounts if needed

**After Game**:
1. Host closes game
2. System creates permanent session record
3. Payment ledger updates
4. Players can view final results

**Benefits**:
- No need for PokerNow
- Real-time chip tracking
- Prevents buy-in/cash-out disputes
- Automatic ledger creation
- Same analytics as imported games

---

### Workflow C: Mixed Games (PokerNow + Live)

**Scenario**: Group plays both online (PokerNow) and in-person games.

**Process**:
1. Create one game on HomeGame
2. Import PokerNow sessions as they happen
3. Create live games for in-person sessions
4. All data aggregates in one game
5. Payment ledger spans all sessions
6. Complete historical tracking

**Benefits**:
- Unified view across online/offline
- Single payment system
- Combined player statistics
- Consistent financial tracking

---

## Technical Architecture (High-Level)

### Tech Stack
- **Frontend**: React + TypeScript, Tailwind CSS
- **Backend**: Python Flask, SQLAlchemy ORM
- **Database**: PostgreSQL with UUID primary keys
- **Hosting**: GCP Cloud Run (backend), Vercel (frontend)
- **Auth**: JWT tokens, bcrypt password hashing

### Data Model
```
Game (public_code, admin_code)
  └─ Sessions (PokerNow imports or live games)
      └─ SessionPlayerSummaries (per-player results)
  └─ Players (cross-session identities)
  └─ PaymentTransactions (real money transfers)
  └─ PaymentBalances (calculated balances)
  └─ AuditLog (all actions)
  └─ GameRules (markdown documentation)
```

### Security
- Admin operations require admin code (X-Admin-Code header)
- User operations require JWT token
- Dual authentication: User can be logged in + have admin session
- Rate limiting on all endpoints
- Audit logging of all changes
- Financial integrity validation

### Multi-Tenancy
- Games are completely isolated
- Public codes for sharing
- Admin codes for management
- No cross-game data leakage

---

## Key Integrations

### PokerNow API
- Fetches session data via public API
- Parses player statistics
- Extracts hand history
- Imports event logs
- No PokerNow account required

### Email Services (SendGrid)
- Password reset emails
- Security notifications
- Bug reports to admin

---

## Deployment & Infrastructure

### Production Environment
- **Domain**: https://homegame.gg
- **Backend**: GCP Cloud Run (auto-scaling)
- **Database**: GCP Cloud SQL (PostgreSQL)
- **Frontend**: Vercel (CDN-hosted)
- **CI/CD**: GitHub Actions

### Staging Environment
- **Frontend**: home-game-staging.vercel.app
- **Backend**: GCP Cloud Run staging instance
- **Database**: Separate staging database

### Development
- **Docker Compose** for local setup
- PostgreSQL container
- pgAdmin for database management
- Hot reload for development

---

## Feature Highlights

### What Makes HomeGame Unique

1. **Zero-Sum Financial Validation**
   - Guarantees data accuracy
   - Prevents corruption
   - Mathematical integrity

2. **Dual Game Modes**
   - PokerNow import for online games
   - Live game tracking for in-person
   - Mixed game support

3. **Comprehensive Analytics**
   - Professional poker statistics
   - Playing style classification
   - Hand replayer
   - Trend analysis

4. **Transparent Payment System**
   - Automatic balance calculation
   - Tracks real-world payments
   - Shows who owes who
   - Payment history

5. **Full Audit Trail**
   - Every action logged
   - Before/after snapshots
   - Rollback capability
   - Dispute resolution

6. **No Account Required for Viewing**
   - Share public code
   - Anyone can view stats
   - Optional authentication

7. **Mobile Responsive**
   - Works on phones, tablets, desktops
   - Optimized for mobile live games

---

## User Pain Points Addressed

### Before HomeGame
❌ Spreadsheets to track games (error-prone)
❌ Manual calculation of balances (tedious)
❌ "Who owes who?" disputes (no records)
❌ Lost game history (no backups)
❌ No player statistics (just guessing)
❌ Difficult to settle payments (manual tracking)

### With HomeGame
✅ Automatic data import from PokerNow
✅ Real-time live game tracking
✅ Automatic balance calculations
✅ Complete payment history
✅ Professional player analytics
✅ Permanent game records
✅ Audit trail for disputes
✅ Mobile-friendly interface

---

## Typical User Journey

### Discovery
1. Friend shares game code
2. Visit https://homegame.gg
3. Enter code, see game summary
4. Impressed by analytics

### Adoption
1. Create account (optional but recommended)
2. Create own game for their group
3. Get public + admin codes
4. Share public code with group

### Regular Use
1. Play poker on PokerNow
2. Import session to HomeGame
3. Players check stats and balances
4. Settle payments based on ledger
5. Repeat weekly/monthly

### Advanced Use
1. Create live games for in-person sessions
2. Track buy-ins/cash-outs in real-time
3. Mix PokerNow and live sessions
4. Analyze trends over months
5. Customize game rules
6. Manage player identities

---

## Monetization (Future Potential)

Currently free, but potential revenue streams:
- Premium features (advanced analytics, exports)
- Team/league subscriptions
- Tournament management
- Integration with payment providers (Venmo API)
- White-label for poker clubs
- Advertising (poker-related)

---

## Competitive Advantages

### vs. Spreadsheets
- Automatic calculations
- No manual entry errors
- Beautiful UI
- Mobile-friendly
- Historical tracking

### vs. PokerNow Alone
- Persistent game history
- Cross-session analytics
- Payment tracking
- Live game support
- Customizable rules

### vs. Other Poker Trackers
- Built specifically for home games
- Dual PokerNow + live game support
- Financial ledger integration
- Zero-sum validation
- Admin code system (no accounts needed)

---

## Roadmap & Future Features

### Near-Term
- Email verification for users
- Player identity claiming UI
- Push notifications
- Mobile app (React Native)
- More payment integrations

### Long-Term
- Tournament mode
- League/season tracking
- Advanced hand analysis (GTO solver)
- Video hand replayer
- Social features (comments, likes)
- Poker coaching tools

---

## Support & Community

### Documentation
- User guides (planned)
- Video tutorials (planned)
- API documentation (internal)

### Feedback
- In-app bug reporting
- Email support
- GitHub issues (open source consideration)

### Updates
- Frequent feature releases
- Zero-downtime deployments
- Automatic database migrations

---

## Summary

**HomeGame** is a comprehensive poker game management platform that bridges online and offline poker by:

1. **Importing PokerNow data** automatically
2. **Tracking live games** in real-time
3. **Calculating balances** accurately
4. **Providing analytics** for player improvement
5. **Managing payments** transparently
6. **Recording history** permanently

It solves the core problems of home poker groups: accurate tracking, easy settlement, and comprehensive analytics. The platform is designed to be accessible (no account required for viewing) while providing powerful admin tools for game management.

**Target Users**: Home poker groups, poker clubs, casual players who want professional-grade tracking without professional-grade complexity.

**Core Value Proposition**: "Track your home poker games like the pros, settle up fairly, and improve your game with real data."
