# HomeGame User Account System - Comprehensive Overview

## Core Architecture

### User Model
- **UUID-based** primary keys
- **Email-based** authentication (unique, indexed)
- **Bcrypt password hashing** (72 character max)
- **Token versioning** for session invalidation
- **Timestamps**: created_at, last_login_at
- **Verification status**: email_verified flag (in schema, not fully implemented)

### Authentication Method
- **JWT tokens** with user_id, email, and token_version
- **Token expiry**: 7 days (604800 seconds)
- **Session invalidation**: Incrementing token_version invalidates all existing tokens
- **Bearer token** authentication via Authorization header

---

## User Journeys & Features

### 1. Registration Flow
**Route**: `POST /api/auth/register`

**Features**:
- Email validation (RFC-compliant format check)
- Display name (2-50 characters)
- Password requirements:
  - Minimum 8 characters
  - Maximum 72 characters (bcrypt limit)
  - Validated by password strength service
- Automatic login after registration (returns JWT token)
- Initial token_version set to 1

**Security**:
- Rate limited (inherited from Flask app config)
- Password hashed with bcrypt (cost factor 12)
- Duplicate email check with proper error messaging

**Frontend**:
- `/register` page
- Form validation with inline error messages
- Real-time password strength checking (optional, not on register page currently)
- Redirect to `/my-games` after successful registration

---

### 2. Login Flow
**Route**: `POST /api/auth/login`

**Features**:
- Email + password authentication
- Case-insensitive email lookup
- Updates last_login_at timestamp
- Returns JWT token + user profile

**Security**:
- **Rate limited**: 5 attempts per minute per IP
- **Generic error messages**: "Invalid credentials" (prevents email enumeration)
- Token includes token_version for session validation

**Frontend**:
- `/login` page
- "Forgot password?" link
- "Remember me" context (user can navigate back to original page after login)
- Redirect to intended page or `/my-games`

---

### 3. Password Reset Flow
**Route**:
- `POST /api/auth/forgot-password` - Request reset
- `POST /api/auth/reset-password` - Complete reset

**Features**:
#### Request Reset:
- Enter email address
- Always returns success (prevents email enumeration)
- Email sent only if account exists
- Reset link expires in 24 hours

#### Reset Password:
- Token from email URL parameter
- New password input with strength checking
- Confirm password validation
- Real-time password strength indicator
- Token validation checks:
  - Exists in database
  - Not expired
  - Not already used
  - Matches hashed version

**Security**:
- **Rate limiting**:
  - Forgot password: 3 requests per hour per IP
  - Reset password: 5 requests per hour per IP
- **Tokens**:
  - 256-bit cryptographically secure random tokens
  - Stored hashed (SHA256) in database
  - Single-use (marked as used_at after consumption)
  - 24-hour expiration
  - Timezone-aware datetime comparisons
- **Session invalidation**: token_version incremented (logs out all devices)
- **Confirmation email** sent after successful reset
- **Audit logging** for both request and completion

**Frontend**:
- `/forgot-password` page
  - Email input
  - Success state with instructions
  - Rate limit notice
- `/reset-password` page
  - Token from URL query parameter
  - New password + confirm password fields
  - Real-time strength indicator
  - Password requirements list
  - Success state with auto-redirect to login

**Backend Tables**:
```sql
password_reset_tokens:
  - id (UUID)
  - user_id (FK to users)
  - token_hash (SHA256, 64 chars)
  - created_at (timestamp with TZ)
  - expires_at (timestamp with TZ)
  - used_at (timestamp with TZ, nullable)
  - ip_address (for audit trail)
```

---

### 4. Password Change Flow (Authenticated)
**Route**: `PATCH /api/auth/password`

**Features**:
- Requires authentication (JWT token)
- Requires current password verification
- New password validation
- Cannot reuse current password

**Security**:
- **Requires auth**: Must be logged in
- **Current password verification**: Bcrypt comparison
- **Session invalidation**: token_version incremented (logs out all devices)
- **Confirmation email** sent to user
- **Audit logging**: PASSWORD_CHANGED action

**Frontend**:
- Settings page (`/settings`)
- Current password field
- New password field
- Password strength indicator
- Success notification

---

### 5. Profile Management
**Route**: `PATCH /api/auth/profile`

**Features**:
- Update display name (2-50 characters)
- Cannot change email (would require email verification)

**Frontend**:
- Settings page (`/settings`)
- Display name input
- Save button

---

### 6. Account Deletion
**Route**: `DELETE /api/auth/account`

**Features**:
- Requires authentication
- Requires password confirmation
- Requires typing "DELETE" for confirmation
- **IRREVERSIBLE** action

**Behavior**:
- User account deleted
- Games owned by user → owner_user_id set to NULL (orphaned)
- Poker identity claims → CASCADE deleted
- Live game participations → CASCADE deleted
- Audit logs → user_id set to NULL (preserved for audit trail)

**Security**:
- Password verification required
- Confirmation text must be exactly "DELETE" (case-sensitive)

**Frontend**:
- Settings page (`/settings`) - Delete Account section
- Confirmation modal with password input
- Type "DELETE" confirmation
- Warning about irreversibility

---

### 7. Current User Profile
**Route**: `GET /api/auth/me`

**Features**:
- Requires authentication
- Returns full user profile:
  - id, email, display_name
  - email_verified status
  - created_at, last_login_at timestamps

**Frontend**:
- Header user menu
- Settings page
- Used throughout app for user context

---

### 8. Session Management

**Token Lifecycle**:
1. Token generated on login/register
2. Token stored in localStorage
3. Auto-attached to all API requests (axios interceptor)
4. Validated on every protected route
5. Invalidated on password change (token_version increment)
6. Expired tokens → 401 response → auto-redirect to login

**Session Invalidation Triggers**:
- Password changed
- Password reset completed
- Manual logout

**Token Validation**:
- Checks user exists
- Checks token_version matches
- Checks token not expired

---

### 9. Password Strength Checking
**Route**: `POST /api/auth/password-strength`

**Features** (Public endpoint, no auth required):
- Real-time strength calculation
- Score 0-100
- Strength levels: weak, fair, good, strong
- Feedback messages for improvements
- Checks:
  - Length
  - Character variety (uppercase, lowercase, numbers, special)
  - Common password detection (10k most common passwords)
  - Repeated characters
  - Sequential characters
  - Dictionary words

**Frontend Integration**:
- Real-time checking on password change page
- Real-time checking on reset password page
- Visual strength bar (color-coded)
- Feedback list
- Debounced (300ms) to avoid excessive API calls

---

### 10. Email Verification (Partial Implementation)
**Status**: Schema exists, not fully implemented

**What Exists**:
- `email_verified` column in users table (defaults to false)
- Flag returned in user profile endpoints

**What's Missing**:
- Email sending for verification links
- Verification token system
- Verification endpoint
- UI for resending verification emails
- Enforcement of verification requirement

---

## Security Features

### Authentication Security
1. **Bcrypt password hashing** (cost factor 12)
2. **JWT tokens** with expiration (7 days)
3. **Token versioning** for session management
4. **Rate limiting**:
   - Login: 5 per minute
   - Forgot password: 3 per hour
   - Reset password: 5 per hour
   - Global: 2000/day, 500/hour in production
5. **Email enumeration prevention**:
   - Generic error messages on login
   - Always return success on forgot password
6. **Password requirements** enforced:
   - Length: 8-72 characters
   - Strength checking
   - Common password detection

### Audit Logging
**All security events logged**:
- Registration
- Login (successful and failed attempts tracked via rate limiting)
- Password changes (PASSWORD_CHANGED)
- Password reset requests (PASSWORD_RESET_REQUESTED)
- Password reset completions (PASSWORD_RESET_COMPLETED)
- Account deletions

**Audit Log Fields**:
- user_id, user_email
- action type
- timestamp
- IP address
- user agent
- method (e.g., "authenticated_change", "email_token_reset")
- before/after state (JSONB)

### Security Headers (Production)
- Content Security Policy
- X-Frame-Options
- X-Content-Type-Options
- Strict-Transport-Security

---

## User Context & Permissions

### Regular Users
**Can**:
- Create games (becomes owner)
- Claim player identities
- View games they own or have claimed players in
- Join live games
- Log buy-ins/cash-outs (pending approval)

**Cannot**:
- Access admin endpoints
- Approve transactions
- Edit game data
- Access other users' private data

### Admin System (Separate from User Auth)
**Admin codes** are separate from user accounts:
- Each game has unique admin_code
- Required for admin operations (via X-Admin-Code header)
- Can be entered in UI (stored in AdminSessionContext)
- Separate from JWT authentication

**Admin capabilities**:
- Import PokerNow sessions
- Create/edit live games
- Approve/reject live game transactions
- Edit player data
- Manage game rules
- Access ledger analysis
- View audit logs

**Dual Auth Support**:
- Users can be authenticated AND have admin session
- Admin operations require both (user auth + admin code)
- Admin session stored separately in context

---

## User-Game Relationships

### Game Ownership
- Users can create games → become owner
- Owner stored as `owner_user_id` FK
- Ownership is optional (games can exist without owners)
- Owner deletion → owner_user_id set to NULL (game preserved)

### Player Identity Claims
**System**:
- One player can only be claimed by one user
- One user can claim multiple players (across different games)
- Claims tracked in `poker_identity_claims` table

**Process** (Not fully implemented in UI):
1. User navigates to game
2. Sees list of players
3. Claims identity (verification_method stored)
4. Future sessions auto-associated

### Live Game Participation
- Users join live games with `join_code`
- Participation tracked in `live_game_participants`
- One user can only join a live game once
- User provides display_name for game
- Can log buy-ins and cash-outs
- Transactions require admin approval

---

## Frontend Routes & UX

### Public Routes (No Auth Required)
- `/` - Landing page
- `/login` - Login page
- `/register` - Registration page
- `/forgot-password` - Request password reset
- `/reset-password` - Reset password with token
- `/:publicCode` - Game summary (public view)
- `/summary/:publicCode` - Game summary (explicit)
- `/rules/:publicCode` - Game rules
- `/analytics/:publicCode` - Game analytics
- `/payments/:publicCode` - Payment ledger
- `/join-live/:joinCode` - Join live game landing

### Protected Routes (Auth Required)
- `/my-games` - User's game dashboard
- `/settings` - User settings and profile
- `/claim-game` - Claim a game
- `/create-game` - Create new game
- `/live-game/:joinCode` - Live game player view

### Admin Routes (Auth + Admin Code Required)
- `/ingest/:publicCode` - PokerNow import
- `/live/:publicCode` - Live game management
- `/live/:joinCode/admin` - Live game admin view
- `/ledger-analysis/:publicCode` - Financial analysis
- `/audit/:publicCode` - Audit log

### Navigation Behavior
- **Logo click**:
  - Authenticated → `/my-games`
  - Not authenticated → `/` (landing)
- **Protected route redirect**:
  - Saves intended destination
  - Redirects to `/login`
  - Returns to intended page after login
- **401 interceptor**:
  - Auto-removes invalid token
  - Redirects to `/login` (unless already on auth page)

---

## API Endpoints Summary

### Public Endpoints
```
POST   /api/auth/register              Create account
POST   /api/auth/login                 Authenticate
POST   /api/auth/forgot-password       Request password reset
POST   /api/auth/reset-password        Complete password reset
POST   /api/auth/password-strength     Check password strength
GET    /api/auth/password-requirements Get password requirements
```

### Protected Endpoints (Require JWT)
```
GET    /api/auth/me                    Get current user
PATCH  /api/auth/profile               Update profile
PATCH  /api/auth/password              Change password
DELETE /api/auth/account               Delete account
```

### Health Endpoints
```
GET    /api/health                     Basic health check
GET    /api/health/ready               Readiness probe (DB check)
GET    /api/health/live                Liveness probe
```

---

## Frontend State Management

### Auth Context
- Provides: `{ isAuthenticated, isLoading, user, login, logout, register }`
- Stores token in localStorage
- Maintains user state across page reloads
- Auto-refreshes user profile from `/api/auth/me`

### Admin Session Context
- Separate from user auth
- Stores: `{ hasAdminSession, adminCode, publicCode, setAdminSession, clearAdminSession }`
- Admin codes stored in localStorage (separate from JWT)
- Can have user auth + admin session simultaneously

### API Client
- Axios instance with interceptors
- Auto-attaches JWT token to requests
- Handles 401 errors (expired tokens)
- Auto-redirects on authentication failures

---

## Database Schema

### Users Table
```sql
CREATE TABLE users (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email             VARCHAR(255) UNIQUE NOT NULL,
  password_hash     VARCHAR(255) NOT NULL,
  token_version     BIGINT NOT NULL DEFAULT 1,
  display_name      VARCHAR(100) NOT NULL,
  email_verified    BOOLEAN NOT NULL DEFAULT false,
  created_at        TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
  last_login_at     TIMESTAMP WITH TIME ZONE
);
```

### Password Reset Tokens Table
```sql
CREATE TABLE password_reset_tokens (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  token_hash  VARCHAR(64) NOT NULL, -- SHA256 hash
  created_at  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
  expires_at  TIMESTAMP WITH TIME ZONE NOT NULL,
  used_at     TIMESTAMP WITH TIME ZONE,
  ip_address  VARCHAR(45)
);
```

### Poker Identity Claims Table
```sql
CREATE TABLE poker_identity_claims (
  id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id              UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  player_id            UUID NOT NULL REFERENCES players(id) ON DELETE CASCADE,
  claimed_at           TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
  verification_method  VARCHAR(50) NOT NULL,
  UNIQUE(user_id, player_id),
  UNIQUE(player_id) -- One player, one owner
);
```

---

## Known Gaps & Missing Features

### Email Verification
**Status**: Schema exists, implementation incomplete
**Missing**:
- Email sending for verification links
- Verification token system
- Verification endpoint
- UI for resending verification
- Enforcement of verification

### Two-Factor Authentication (2FA)
**Status**: Not implemented
**Would need**:
- TOTP/SMS system
- Backup codes
- 2FA setup flow
- 2FA verification on login

### OAuth/Social Login
**Status**: Not implemented
**Could add**:
- Google OAuth
- GitHub OAuth
- Discord OAuth

### Password History
**Status**: Not implemented
**Would prevent**:
- Reusing last N passwords
- Too frequent password changes

### Account Recovery
**Status**: Partial (password reset only)
**Missing**:
- Security questions
- Recovery codes
- Account lockout after failed attempts
- Account recovery for compromised accounts

### Email Change Flow
**Status**: Not implemented
**Would need**:
- New email verification
- Confirmation to old email
- Grace period before change takes effect

### Account Suspension/Ban
**Status**: Not implemented
**Would need**:
- Admin ability to suspend users
- Blocked user table
- Ban reasons and appeals
- Temporary vs permanent bans

### Session Management UI
**Status**: Not implemented
**Could add**:
- View active sessions
- Logout specific sessions
- Logout all other sessions
- Session details (device, location, last active)

### Rate Limit Feedback
**Status**: Implemented in backend, not surfaced in UI
**Could improve**:
- Show remaining attempts
- Show lockout duration
- Better error messages

### Player Identity Claim UI
**Status**: Backend exists, UI incomplete
**Missing**:
- Flow to claim players in UI
- Verification methods
- Admin approval workflow
- Dispute resolution

### Privacy Settings
**Status**: Not implemented
**Could add**:
- Profile visibility controls
- Game history privacy
- Stats sharing preferences

### Notification Preferences
**Status**: Not implemented (only security emails sent)
**Could add**:
- Email notification settings
- Game invites
- Payment reminders
- Weekly summaries
- Marketing emails (opt-in)

### API Key Management
**Status**: Not implemented
**Could add**:
- Personal API keys
- Scoped permissions
- Key rotation
- Rate limits per key

---

## Testing Coverage

### Backend Tests (pytest)
**Unit Tests**:
- Password strength service (35 tests)
- Email service (8 tests)
- Audit service (11 tests)
- JWT token service with versioning (4 tests)
- Password hasher (bcrypt)

**Integration Tests**:
- Password change security (10 tests)
- Password reset flow (10 tests)
- Authentication API (6 tests + original auth tests)
- Complete security flows (3 E2E tests)

### Frontend Tests (Jest/React Testing Library)
**Status**: Limited coverage
**Existing**: Header component tests
**Missing**: Most auth page tests

---

## Error Handling

### Common Error Scenarios
1. **Invalid credentials** → "Invalid credentials" (generic)
2. **Expired token** → 401 → Auto-logout → Redirect to login
3. **Used reset token** → "This reset link has already been used"
4. **Expired reset token** → "This reset link has expired. Please request a new one"
5. **Rate limit exceeded** → 429 with retry-after header
6. **Weak password** → Inline validation with feedback
7. **Duplicate email** → "Email already registered"
8. **Server error** → Generic error message + logged for debugging

---

## Security Considerations

### Password Storage
- Never stored in plain text
- Bcrypt with cost factor 12
- Hashes are 60 characters (bcrypt format)
- Max password length 72 (bcrypt limit)

### Token Storage
- JWTs stored in localStorage (XSS risk mitigated by CSP)
- Not in cookies (CSRF not applicable)
- Short expiry (7 days)
- Token versioning for instant invalidation

### Reset Token Security
- 256-bit cryptographic random tokens
- Stored as SHA256 hashes (not reversible)
- Single-use (marked used_at)
- Time-limited (24 hours)
- IP address logged for audit
- Timezone-aware expiry checks

### Email Security
- SendGrid for reliable delivery
- Security notifications sent on password change
- Templates include warnings about phishing
- Sender: noreply@homegame.gg

### Input Validation
- All endpoints validate input
- SQL injection prevented (SQLAlchemy ORM)
- XSS prevented (React escapes by default)
- CSRF not applicable (stateless JWT auth)

---

## Production Configuration

### Environment Variables
```bash
# Required
JWT_SECRET=<64-byte secret>
DATABASE_URL=<postgres connection string>
SENDGRID_API_KEY=<sendgrid key>

# Optional
FRONTEND_URL=https://homegame.gg
FROM_EMAIL=noreply@homegame.gg
BUG_REPORT_EMAIL=<admin email>
FLASK_ENV=production
```

### Rate Limits (Production)
- Global: 2000 requests/day, 500 requests/hour
- Login: 5 per minute
- Forgot password: 3 per hour
- Reset password: 5 per hour

### CORS
- Configured via ALLOWED_ORIGINS environment variable
- Production: https://homegame.gg
- Staging: https://home-game-staging.vercel.app
- Local: http://localhost:3000

---

## Migration Path for New Features

### To Add Email Verification:
1. Create email verification token system (similar to password reset)
2. Add `POST /api/auth/resend-verification` endpoint
3. Add `POST /api/auth/verify-email` endpoint
4. Update registration to send verification email
5. Add UI banner for unverified users
6. Optional: Block certain actions until verified

### To Add 2FA:
1. Add `totp_secret` column to users table
2. Add 2FA setup flow (`/settings/2fa`)
3. Add 2FA verification to login flow
4. Add backup codes table and generation
5. Add 2FA recovery flow

### To Add OAuth:
1. Install OAuth libraries (e.g., Authlib)
2. Add OAuth provider configuration
3. Create OAuth callback endpoints
4. Handle account linking (existing users)
5. Update frontend with OAuth buttons
6. Store OAuth provider_id in users table

---

## Performance Considerations

### Database Indexes
- Users: `email` (unique index)
- Password reset tokens: `token_hash`, `expires_at`
- Poker identity claims: `(user_id, player_id)`, `player_id`
- Audit logs: `user_id`, `created_at`

### Caching
- User profiles cached in frontend (AuthContext)
- Admin sessions cached in frontend (AdminSessionContext)
- Password strength endpoint is stateless (no caching needed)

### Token Validation
- Token decoded and validated on every protected request
- No database lookup on every request (JWT is self-contained)
- Database lookup only needed for user profile endpoints

---

## Monitoring & Observability

### What's Logged
- All authentication attempts
- All password changes/resets
- All security events (audit log)
- Failed authentication (via rate limiter)
- API errors (Flask logger)

### What Could Be Added
- Metrics (login success rate, registration rate)
- Alerting (suspicious activity, failed logins)
- User analytics (DAU, MAU, retention)
- Security monitoring (brute force detection)

---

## Recommendations for Gap Analysis

Ask Claude to review:

1. **Email Verification Implementation Plan**
   - Should it be required or optional?
   - When should it block user actions?
   - Email template design
   - Token expiry and resend logic

2. **2FA Implementation Plan**
   - TOTP vs SMS vs both?
   - Required vs optional?
   - Backup codes strategy
   - Recovery flow if 2FA device lost

3. **Session Management Features**
   - Should users see all active sessions?
   - Should there be a "logout all devices" option?
   - Session expiry notifications?

4. **Account Recovery Improvements**
   - Are password resets sufficient?
   - Should there be security questions?
   - Account lockout after N failed attempts?
   - Self-service account unlock?

5. **Privacy & Data Controls**
   - What privacy settings should users have?
   - Should users be able to export their data?
   - What about data deletion (GDPR)?
   - Profile visibility controls?

6. **Social/OAuth Integration**
   - Which providers make sense?
   - How to handle account linking?
   - What if OAuth email matches existing account?

7. **Security Enhancements**
   - IP-based login notifications?
   - Geolocation-based suspicious activity alerts?
   - Device fingerprinting?
   - Password expiry policies?

8. **User Experience**
   - "Remember this device" for 2FA?
   - Passwordless login options?
   - Magic link login?
   - Biometric authentication (WebAuthn)?

---

## Summary

The current user account system is **production-ready** with:
- ✅ Secure registration and login
- ✅ Complete password reset flow
- ✅ Password change with session invalidation
- ✅ Profile management
- ✅ Account deletion
- ✅ Comprehensive security (rate limiting, audit logging, strength checking)
- ✅ Integration with game ownership and player identity claims
- ✅ Live game participation

**Major gaps**:
- ❌ Email verification not implemented
- ❌ 2FA not available
- ❌ OAuth/social login not available
- ❌ Session management UI incomplete
- ❌ Player identity claim UI incomplete

**Minor gaps**:
- ⚠️ Email change flow missing
- ⚠️ Account recovery options limited
- ⚠️ Privacy controls not implemented
- ⚠️ Notification preferences not available
- ⚠️ API key management not available

The system is secure and functional for current use cases, with clear paths for enhancement.
