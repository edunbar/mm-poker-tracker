"""
Balance History Service V2

Provides player balance history showing poker sessions and payment transactions
with running balance calculations. Follows domain-driven design patterns.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session as DBSession

from db.models import Game, Player

logger = logging.getLogger(__name__)


@dataclass
class BalanceHistoryTransaction:
    """Individual transaction in balance history (session or payment)."""
    date: datetime
    type: str  # 'session' | 'payment_sent' | 'payment_received'
    description: str
    amount: Decimal
    running_balance: Decimal
    session_id: Optional[str]
    payment_id: Optional[str]
    payment_method: Optional[str]
    to_player_name: Optional[str]
    from_player_name: Optional[str]


@dataclass
class BalanceHistorySummary:
    """Summary statistics for player's balance history."""
    poker_net: Decimal
    payments_sent: Decimal
    payments_received: Decimal
    session_count: int
    payment_count: int


@dataclass
class PlayerBalanceHistory:
    """Complete balance history for a player in a game."""
    player_id: str
    player_name: str
    current_balance: Decimal
    summary: BalanceHistorySummary
    transactions: List[BalanceHistoryTransaction]
    total_count: int
    current_page: int
    per_page: int
    total_pages: int
    has_next: bool
    has_prev: bool


class BalanceHistoryServiceV2:
    """
    Service for retrieving player balance history with running balances.

    Combines poker session results and payment transactions into a unified
    timeline showing how a player's balance evolved over time.
    """

    def __init__(self, db_session: DBSession):
        """
        Initialize balance history service.

        Args:
            db_session: SQLAlchemy session (REQUIRED). Session lifecycle is managed
                       by the caller (typically the web layer).
        """
        if db_session is None:
            raise ValueError("db_session is required - services do not manage sessions")
        self.db = db_session

    def get_player_balance_history(
        self,
        game_id: str,
        player_id: str,
        page: int = 1,
        per_page: int = 5
    ) -> PlayerBalanceHistory:
        """
        Get paginated balance history for a player in a game.

        Args:
            game_id: UUID of the game
            player_id: UUID of the player
            page: Page number (1 = most recent, default: 1)
            per_page: Transactions per page (default: 5, max: 100)

        Returns:
            PlayerBalanceHistory with transactions and pagination info

        Raises:
            ValueError: If game or player not found, or invalid parameters
        """
        logger.info(
            f"Getting balance history for player {player_id} in game {game_id}, "
            f"page={page}, per_page={per_page}"
        )

        # Validate inputs
        if page < 1:
            raise ValueError("Page number must be >= 1")

        if per_page < 1 or per_page > 100:
            raise ValueError("per_page must be between 1 and 100")

        # Verify game exists
        game = self.db.query(Game).filter(Game.id == game_id).first()
        if not game:
            raise ValueError(f"Game {game_id} not found")

        # Verify player exists
        player = self.db.query(Player).filter(Player.id == player_id).first()
        if not player:
            raise ValueError(f"Player {player_id} not found")

        # Get summary stats (always all-time)
        summary = self._get_summary_stats(game_id, player_id)

        # Get paginated transactions
        transactions, total_count = self._get_transactions(game_id, player_id, page, per_page)

        # Calculate pagination info
        total_pages = math.ceil(total_count / per_page) if total_count > 0 else 1

        # Validate page is within range
        if page > total_pages:
            raise ValueError(f"Page {page} does not exist (only {total_pages} pages available)")

        # Calculate amount owed (unsettled balance)
        # Positive = others owe this player, Negative = this player owes others
        amount_owed = summary.poker_net - summary.payments_received + summary.payments_sent

        return PlayerBalanceHistory(
            player_id=player_id,
            player_name=player.display_name,
            current_balance=amount_owed,
            summary=summary,
            transactions=transactions,
            total_count=total_count,
            current_page=page,
            per_page=per_page,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1
        )

    def _get_summary_stats(
        self,
        game_id: str,
        player_id: str
    ) -> BalanceHistorySummary:
        """Get summary statistics for player in game (all-time)."""
        # Query for poker net winnings
        poker_net_query = text("""
            SELECT COALESCE(SUM(sps.net), 0)::bigint as total_net,
                   COUNT(*)::int as session_count
            FROM session_player_summaries sps
            JOIN sessions s ON sps.session_id = s.id
            WHERE sps.player_id = :player_id
              AND s.game_id = :game_id
        """)

        poker_result = self.db.execute(
            poker_net_query,
            {
                "player_id": player_id,
                "game_id": game_id
            }
        ).fetchone()

        poker_net_cents = poker_result[0] if poker_result else 0
        session_count = poker_result[1] if poker_result else 0

        # Query for payments sent
        payments_sent_query = text("""
            SELECT COALESCE(SUM(pt.amount_cents), 0)::bigint as total_sent,
                   COUNT(*)::int as payment_count
            FROM payment_transactions pt
            WHERE pt.payer_id = :player_id
              AND pt.game_id = :game_id
              AND pt.status = 'completed'
        """)

        sent_result = self.db.execute(
            payments_sent_query,
            {
                "player_id": player_id,
                "game_id": game_id
            }
        ).fetchone()

        payments_sent_cents = sent_result[0] if sent_result else 0
        sent_count = sent_result[1] if sent_result else 0

        # Query for payments received
        payments_received_query = text("""
            SELECT COALESCE(SUM(pt.amount_cents), 0)::bigint as total_received,
                   COUNT(*)::int as payment_count
            FROM payment_transactions pt
            WHERE pt.recipient_id = :player_id
              AND pt.game_id = :game_id
              AND pt.status = 'completed'
        """)

        received_result = self.db.execute(
            payments_received_query,
            {
                "player_id": player_id,
                "game_id": game_id
            }
        ).fetchone()

        payments_received_cents = received_result[0] if received_result else 0
        received_count = received_result[1] if received_result else 0

        return BalanceHistorySummary(
            poker_net=Decimal(poker_net_cents) / 100,
            payments_sent=Decimal(payments_sent_cents) / 100,
            payments_received=Decimal(payments_received_cents) / 100,
            session_count=session_count,
            payment_count=sent_count + received_count
        )

    def _get_transactions(
        self,
        game_id: str,
        player_id: str,
        page: int,
        per_page: int
    ) -> tuple[List[BalanceHistoryTransaction], int]:
        """
        Get paginated transactions with running balances.

        Returns:
            (transactions_for_page, total_count)
        """

        # 1. Fetch ALL transactions in chronological order (oldest first)
        all_transactions_query = text("""
            WITH all_transactions AS (
                -- Sessions
                SELECT
                    sps.net / 100.0 AS amount,
                    s.ended_at AS date,
                    'session' AS type,
                    COALESCE(s.session_name, 'Session #' || s.game_number::text) AS description,
                    s.id::text AS session_id,
                    NULL AS payment_id,
                    NULL AS payment_method,
                    NULL AS to_player_name,
                    NULL AS from_player_name
                FROM session_player_summaries sps
                JOIN sessions s ON sps.session_id = s.id
                WHERE sps.player_id = :player_id
                  AND s.game_id = :game_id

                UNION ALL

                -- Payments sent
                SELECT
                    pt.amount_cents / 100.0 AS amount,
                    pt.payment_date AS date,
                    'payment_sent' AS type,
                    'Paid to ' || p_to.display_name AS description,
                    NULL AS session_id,
                    pt.id::text AS payment_id,
                    pt.payment_method,
                    p_to.display_name AS to_player_name,
                    NULL AS from_player_name
                FROM payment_transactions pt
                JOIN players p_to ON pt.recipient_id = p_to.id
                WHERE pt.payer_id = :player_id
                  AND pt.game_id = :game_id
                  AND pt.status = 'completed'

                UNION ALL

                -- Payments received
                SELECT
                    -(pt.amount_cents / 100.0) AS amount,
                    pt.payment_date AS date,
                    'payment_received' AS type,
                    'Received from ' || p_from.display_name AS description,
                    NULL AS session_id,
                    pt.id::text AS payment_id,
                    pt.payment_method,
                    NULL AS to_player_name,
                    p_from.display_name AS from_player_name
                FROM payment_transactions pt
                JOIN players p_from ON pt.payer_id = p_from.id
                WHERE pt.recipient_id = :player_id
                  AND pt.game_id = :game_id
                  AND pt.status = 'completed'
            )
            SELECT * FROM all_transactions
            ORDER BY date ASC, type ASC
        """)

        results = self.db.execute(
            all_transactions_query,
            {"player_id": player_id, "game_id": game_id}
        ).fetchall()

        # 2. Convert to list of dicts
        all_transactions = [
            {
                'amount': Decimal(str(row[0])),
                'date': row[1],
                'type': row[2],
                'description': row[3],
                'session_id': row[4],
                'payment_id': row[5],
                'payment_method': row[6],
                'to_player_name': row[7],
                'from_player_name': row[8]
            }
            for row in results
        ]

        total_count = len(all_transactions)

        # 3. Calculate pagination boundaries
        # Page 1 = most recent, so work backwards from end
        start_idx = total_count - (page * per_page)
        end_idx = total_count - ((page - 1) * per_page)
        start_idx = max(0, start_idx)

        # 4. Slice to get this page's transactions
        page_transactions = all_transactions[start_idx:end_idx]

        # 5. Calculate opening balance for this page
        # Opening balance = sum of ALL transactions before this page
        opening_balance = sum(tx['amount'] for tx in all_transactions[:start_idx])

        # 6. Add running balance to each transaction
        running_balance = opening_balance
        transaction_objects = []
        for tx in page_transactions:
            running_balance += tx['amount']
            transaction_objects.append(BalanceHistoryTransaction(
                date=tx['date'],
                type=tx['type'],
                description=tx['description'],
                amount=tx['amount'],
                running_balance=running_balance,
                session_id=tx['session_id'],
                payment_id=tx['payment_id'],
                payment_method=tx['payment_method'],
                to_player_name=tx['to_player_name'],
                from_player_name=tx['from_player_name']
            ))

        # 7. Reverse the list so newest transactions show at top of page
        transaction_objects.reverse()

        return transaction_objects, total_count
