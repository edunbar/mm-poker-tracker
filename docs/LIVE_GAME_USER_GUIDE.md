# Live Game User Guide

## Overview

The **Live Game** feature enables real-time tracking of poker game buy-ins and cash-outs during your poker session. Instead of manually recording transactions after the game, players can request buy-ins and cash-outs through the app, which are then approved by the admin in real-time.

### Key Benefits

- **Real-Time Balance Tracking**: See your current chip count and net result live during the game
- **Instant Updates**: All players see transaction approvals immediately via Server-Sent Events (SSE)
- **Zero Manual Entry**: Eliminate post-game ledger reconciliation errors
- **Admin Control**: All transactions require admin approval before processing
- **Automatic Settlement**: Final ledger is automatically generated when the game closes

### How It Works

1. **Admin creates a live game** with a unique 4-character join code
2. **Players join** using the join code via their mobile devices
3. **Players request buy-ins/cash-outs** during the game
4. **Admin approves or rejects** each transaction
5. **All participants see updates** instantly via real-time events
6. **Admin closes the game** at the end of the session
7. **Final ledger is saved** to the game's permanent record

---

## Getting Started

### Prerequisites

- An existing game created on homegame.gg with a public code
- At least one admin with the admin code
- Players with accounts on homegame.gg (or willing to create one)

### Quick Start (Admin)

1. Navigate to your game's dashboard: `https://homegame.gg/game/{publicCode}`
2. Click the **"Start Live Game"** button
3. Configure game settings:
   - Min Buy-In (e.g., $20)
   - Max Buy-In (optional, e.g., $200)
   - Small/Big Blinds (optional, for reference)
4. Click **"Create Live Game"**
5. Share the **4-character join code** with your players (e.g., "A7X2")

### Quick Start (Player)

1. Visit the join link shared by the admin: `https://homegame.gg/join-live/{joinCode}`
2. Log in (or create an account if you don't have one)
3. You'll automatically join as a participant
4. Use the **"Buy In"** button to request chips
5. Use the **"Cash Out"** button when leaving the table

---

## Admin Guide

### Creating a Live Game

**Step 1**: Navigate to game dashboard
```
https://homegame.gg/game/{publicCode}
```

**Step 2**: Click **"Start Live Game"** button in the header

**Step 3**: Configure game settings in the modal:

| Setting | Required | Description | Example |
|---------|----------|-------------|---------|
| Min Buy-In | Yes | Minimum amount players can buy in for | $20.00 |
| Max Buy-In | No | Maximum amount players can buy in for | $200.00 |
| Small Blind | No | Reference only (not enforced) | $0.25 |
| Big Blind | No | Reference only (not enforced) | $0.50 |

**Step 4**: Click **"Create Game"**

**Step 5**: Copy the join code from the success modal (e.g., "A7X2")

**Step 6**: Share the join link with players:
```
https://homegame.gg/join-live/A7X2
```

### Accessing the Admin Panel

Once a live game is created, navigate to:
```
https://homegame.gg/live-admin/{joinCode}
```

Or click the **"Admin Panel"** button from the game dashboard.

### Approving Transactions

The admin panel shows all pending transactions in the **"Pending Approvals"** section.

**Buy-In Approval**:
1. Player requests $50 buy-in
2. Admin sees:
   ```
   Player 1 requests $50.00 buy-in
   [Approve] [Reject]
   ```
3. Click **"Approve"** to add chips to their balance
4. All participants see the update instantly

**Cash-Out Approval**:
1. Player requests to cash out $75
2. Admin sees:
   ```
   Player 1 requests $75.00 cash-out
   [Approve] [Reject]
   ```
3. Click **"Approve"** to remove chips from their balance
4. All participants see the update instantly

**Rejecting Transactions**:
- Click **"Reject"** if the transaction is invalid (e.g., wrong amount, mistake)
- The transaction is removed and the player can submit a new request

### Monitoring Game Balance

The **Game Status** card shows critical financial metrics:

| Metric | Description |
|--------|-------------|
| Active Players | Players with chips on the table (chipsOnTable > 0) |
| Total Pot | Sum of all chips currently on the table |
| Pending Requests | Number of unapproved transactions |

**Financial Integrity Check**:
- Total Pot should equal: Σ(total_buy_ins) - Σ(total_cash_outs)
- If discrepancy exists, contact support before closing the game

### Closing the Game

**IMPORTANT**: Once a game is closed, it **cannot be reopened**. All transactions must be approved before closing.

**Step 1**: Click **"Close Game"** button in admin panel

**Step 2**: Review the closure summary:
```
Total Buy-Ins: $500.00
Total Cash-Outs: $350.00
Chips Remaining: $150.00 (3 players)
```

**Step 3**: Confirm that:
- All pending transactions are resolved (or intentionally rejected)
- Total pot matches expected amount
- No players are missing from the participant list

**Step 4**: Click **"Confirm Close Game"**

**Step 5**: The game status changes to **"Closed"** and:
- SSE connections are terminated
- Players can no longer request transactions
- Final ledger is saved to the game's session history
- Participants can view their final net result

### Sharing the Join Link

**Copy Join Link Button**:
- Click **"Copy Join Link"** in the admin panel
- Share via text message, email, or QR code
- Players can join at any time (even mid-game)

**Best Practices**:
- Share the link before the game starts
- Have players join and test their connection
- Ensure all players have accounts created beforehand
- Keep the join code visible during the game (e.g., on a TV screen)

---

## Player Guide

### Joining a Live Game

**Method 1: Direct Link**
1. Admin shares link: `https://homegame.gg/join-live/A7X2`
2. Click the link on your mobile device
3. Log in (or create an account)
4. You're automatically joined as a participant

**Method 2: Manual Join Code Entry**
1. Navigate to: `https://homegame.gg/join-live`
2. Enter the 4-character join code (e.g., "A7X2")
3. Click **"Join Game"**

### Requesting a Buy-In

**Step 1**: Click the **"💵 Buy In"** button

**Step 2**: Enter the amount (must be between min/max buy-in limits)

**Step 3**: Click **"Request Buy-In"**

**Step 4**: Wait for admin approval
- You'll see: `⏳ Pending Approval: $50.00`
- The admin will approve or reject your request
- You'll receive an instant notification when processed

**Step 5**: Once approved:
- Your **"Chips on Table"** updates immediately
- Your **"Total Buy-Ins"** increases
- Your **"Net Result"** recalculates

### Requesting a Cash-Out

**Step 1**: Click the **"🚪 Cash Out"** button

**Step 2**: Enter the amount (cannot exceed your chips on table)

**Step 3**: Click **"Request Cash-Out"**

**Step 4**: Wait for admin approval

**Step 5**: Once approved:
- Your **"Chips on Table"** decreases
- Your **"Total Cash-Outs"** increases
- Your **"Net Result"** recalculates

**Note**: You can only cash out if you have chips on the table (chipsOnTable > 0).

### Understanding Your Stats

Your player stats card shows:

| Stat | Description | Formula |
|------|-------------|---------|
| Chips on Table | Current chips you have in front of you | Latest approved balance |
| Total Buy-Ins | Total amount you've bought in for | Sum of all approved buy-ins |
| Total Cash-Outs | Total amount you've cashed out | Sum of all approved cash-outs |
| Net Result | Your current profit/loss | (Total Cash-Outs + Chips on Table) - Total Buy-Ins |

**Example**:
```
Chips on Table: $120.00
Total Buy-Ins: $150.00
Total Cash-Outs: $50.00
Net Result: $20.00 (profit)

Calculation: ($50 + $120) - $150 = $20
```

### Viewing Other Players

The **Players** section shows all participants:

| Player | Chips on Table | Net Result | Status |
|--------|----------------|------------|--------|
| You | $120.00 | +$20.00 | 🟢 Active |
| Player 2 | $80.00 | -$10.00 | 🟢 Active |
| Player 3 | $0.00 | -$50.00 | ⚫ Cashed Out |

**Privacy Note**: Other players can see your chip count and net result, but not your individual buy-in/cash-out amounts.

### Leaving the Game

**Option 1: Cash Out Fully**
1. Request a cash-out for all your chips
2. Wait for admin approval
3. Your chips on table = $0.00
4. You remain in the participant list (but marked as inactive)

**Option 2: Leave Without Cashing Out**
- If you must leave before the game ends, coordinate with the admin
- The admin can record your final chip count manually
- When the game closes, your final balance is recorded

---

## Real-Time Updates

### How Server-Sent Events (SSE) Work

The Live Game feature uses **Server-Sent Events (SSE)** for instant updates without polling. This means:

- **Zero delay**: Updates appear instantly (typically <50ms)
- **Battery efficient**: No constant HTTP requests draining your phone battery
- **Reliable**: Auto-reconnects if your connection drops

### Events You'll See

| Event | Triggered When | What You See |
|-------|----------------|--------------|
| `transaction_created` | Player requests buy-in/cash-out | New pending transaction appears |
| `transaction_approved` | Admin approves transaction | Transaction disappears, balance updates |
| `transaction_rejected` | Admin rejects transaction | Transaction disappears, no balance change |
| `participant_joined` | New player joins the game | New player appears in participant list |
| `game_closed` | Admin closes the game | "Game Closed" banner, no more actions allowed |

### Connection Status

The app automatically manages your SSE connection:

**Connected**:
- You'll see real-time updates
- Green indicator in the corner (optional UI enhancement)

**Reconnecting**:
- Brief network interruption occurred
- App automatically retries (up to 10 times)
- Uses exponential backoff: 1s → 2s → 4s → 8s → 16s → 30s

**Disconnected**:
- Connection lost after max retries
- You'll see a banner: **"Connection lost. Refresh to reconnect."**
- Refresh the page to re-establish connection

### Best Practices for Stable Connections

1. **Use a stable internet connection**: WiFi preferred over cellular
2. **Keep the page open**: Don't switch apps or lock your screen for long periods
3. **Refresh if disconnected**: If you see a disconnect banner, refresh immediately
4. **Test before the game**: Join 5-10 minutes early to verify connection works
5. **Disable battery saver**: Some phones close background connections aggressively

---

## Troubleshooting

### Cannot Join Game: "Game Not Found"

**Possible Causes**:
- Join code is incorrect (check for typos like "0" vs "O")
- Game has been closed by the admin
- Game does not exist (admin hasn't created it yet)

**Solutions**:
1. Verify the join code with the admin
2. Check if the game is still active (ask admin)
3. Try the join link again instead of manual entry

### Buy-In Button is Disabled

**Possible Causes**:
- You already have a pending transaction awaiting approval
- The game has been closed
- You've been disconnected from SSE

**Solutions**:
1. Wait for admin to approve/reject your pending transaction
2. Check if the game is still active (status should be "🟢 Active")
3. Refresh the page to reconnect

### Cash-Out Button is Disabled

**Possible Causes**:
- You have no chips on the table (chipsOnTable = 0)
- You already have a pending cash-out request
- The game has been closed

**Solutions**:
1. Buy in first before you can cash out
2. Wait for admin to approve your pending cash-out
3. Verify your chip count is greater than $0.00

### "Connection Lost" Banner

**Possible Causes**:
- Network interruption (WiFi/cellular dropped)
- Server restart (rare, typically during deployment)
- Browser closed SSE connection (battery saver, tab inactive)

**Solutions**:
1. **Refresh the page immediately** to reconnect
2. Check your internet connection
3. If problem persists, contact admin to verify server is running

### Updates Not Appearing Instantly

**Possible Causes**:
- SSE connection is broken (but no error shown yet)
- Browser tab is inactive (some browsers throttle background connections)
- Network latency is high

**Solutions**:
1. Refresh the page
2. Bring the tab to the foreground
3. Check your network speed (SSE requires stable connection)
4. Ask another player if they're seeing updates (to rule out server issue)

### Admin Approved My Transaction, But Balance Didn't Update

**Possible Causes**:
- SSE connection dropped during the approval
- React Query cache didn't invalidate
- Browser rendering bug

**Solutions**:
1. **Refresh the page** to fetch the latest balance
2. Check with admin to confirm they clicked "Approve"
3. If balance still incorrect, contact support (possible database issue)

### "Maximum Connections Exceeded" Error

**Possible Causes**:
- You have 5+ browser tabs/devices connected with the same user account
- Your previous connection didn't close properly

**Solutions**:
1. Close all other tabs/devices connected to the live game
2. Wait 60 seconds for stale connections to time out
3. Refresh and reconnect

### Game Closes Unexpectedly

**Possible Causes**:
- Admin closed the game
- Game reached a time limit (if configured)
- Server error caused auto-closure (rare)

**Solutions**:
1. Contact the admin to verify if closure was intentional
2. Check your final balance in the "Game Closed" view
3. If unintentional, admin must create a new live game

---

## FAQ

### Can I join a live game without an account?

No, all participants must have a homegame.gg account. Creating an account takes <1 minute and is free.

### Can I join mid-game?

Yes! You can join at any time while the game status is "active". Just use the join code or link provided by the admin.

### What happens if I accidentally request the wrong amount?

Ask the admin to reject your transaction, then submit a new request with the correct amount. The admin can also manually adjust amounts if needed.

### Can I change my display name?

Yes, your display name is set in your account settings. Changes will reflect in all games you participate in.

### What if the admin loses connection?

If the admin's connection drops, they can reconnect by navigating back to `/live-admin/{joinCode}`. All pending transactions and participant data persist on the server.

### Can multiple people be admins?

Currently, only the user who created the live game has admin access. This is to prevent conflicting approvals. If the admin must leave, they should designate someone and share their credentials.

### What if two players have the same name?

The app uses your account display name. If two players coincidentally have the same name, add a distinguisher (e.g., "Mike L" vs "Mike S"). This prevents confusion during transaction approval.

### Can I cash out more than my chip count?

No, cash-outs are capped at your current `chipsOnTable` amount. If you believe your chip count is incorrect, ask the admin to manually adjust before cashing out.

### What happens to pending transactions when the game closes?

All pending transactions are automatically rejected when the game closes. Make sure all transactions are approved/rejected before closing.

### Can I re-open a closed game?

No, closed games cannot be re-opened. If you need to continue playing, the admin must create a new live game.

### How long does the join code remain valid?

The join code remains valid until the game is closed. Once closed, the join code becomes inactive and cannot be used.

### Can I view my transaction history?

Yes, after the game closes, you can view the final session in the game's dashboard, which includes all buy-ins, cash-outs, and your final net result.

### What if I have chips remaining when the game closes?

Your remaining chips are recorded in the final ledger. The admin should ensure all players cash out before closing, but if chips remain, they're counted toward your net result:

```
Net Result = (Total Cash-Outs + Chips Remaining) - Total Buy-Ins
```

### Is my financial data secure?

Yes, all transactions are stored securely in a PostgreSQL database with:
- Encrypted connections (SSL/TLS in production)
- User authentication required for all actions
- Audit logging of all financial operations
- Zero-sum validation to ensure ledger integrity

### Can I export my transaction history?

Yes, after the game closes, you can export the session data from the game dashboard (CSV or Google Sheets integration, if enabled by the admin).

### What browsers are supported?

The Live Game feature works on all modern browsers that support Server-Sent Events (SSE):
- ✅ Chrome (desktop & mobile)
- ✅ Safari (desktop & mobile)
- ✅ Firefox (desktop & mobile)
- ✅ Edge (desktop & mobile)
- ❌ Internet Explorer (not supported)

### Can I use this feature offline?

No, the Live Game feature requires an active internet connection for real-time updates. If your connection drops, the app will attempt to reconnect automatically.

### How much data does SSE use?

Very minimal. SSE is extremely efficient:
- Initial connection: ~2KB
- Keepalive pings: ~50 bytes every 30 seconds
- Transaction event: ~500 bytes

For a typical 4-hour game with 30 transactions, total data usage is <100KB (less than loading a single webpage).

---

## Support

### Need Help?

- **Documentation**: Check this guide and the API documentation (LIVE_GAME_API.md)
- **Bug Reports**: Report issues at https://github.com/edunbar/mmpt-clean/issues
- **Feature Requests**: Contact the admin or submit a GitHub issue

### Production Deployment Notes

For admins deploying their own instance:

- **Single Instance**: Current SSE implementation uses in-memory connection storage (works for 1 server)
- **Multi-Instance**: For production with load balancing, migrate to Redis Pub/Sub (see `docs/SSE_REDIS_UPGRADE.md`)
- **Health Checks**: Monitor `/api/health` endpoint for server status
- **Metrics**: SSE connection metrics available at `/api/live-games/metrics` (admin only)

---

**Version**: 1.0.0 (January 2025)
**Last Updated**: 2025-01-XX
**Feature Status**: Production Ready ✅
