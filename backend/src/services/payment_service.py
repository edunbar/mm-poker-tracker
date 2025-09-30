"""
Payment Service

Handles all payment-related business logic including:
- Recording payments between players
- Calculating balances and settlements
- Optimal debt minimization
- Balance synchronization
"""

import logging
import json
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timezone
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

from sqlalchemy.orm import Session as DBSession
from sqlalchemy import text, func

from db.database import SessionLocal
from db.models import (
    Game, Player, PaymentTransaction, PaymentBalance,
    SessionPlayerSummary, Session
)

# Configure structured logging for payment operations
logger = logging.getLogger(__name__)


class PaymentLogger:
    """Structured logger for payment operations"""

    @staticmethod
    def log_payment_recorded(transaction: 'PaymentTransaction', duration_ms: float):
        """Log when a payment is successfully recorded"""
        logger.info(
            "Payment recorded",
            extra={
                "event": "payment_recorded",
                "transaction_id": str(transaction.id),
                "game_id": str(transaction.game_id),
                "payer_id": str(transaction.payer_id),
                "recipient_id": str(transaction.recipient_id),
                "amount_cents": transaction.amount_cents,
                "payment_method": transaction.payment_method,
                "status": transaction.status,
                "duration_ms": duration_ms,
            }
        )

    @staticmethod
    def log_payment_error(error_type: str, game_id: str, details: dict):
        """Log payment operation errors"""
        logger.error(
            f"Payment error: {error_type}",
            extra={
                "event": "payment_error",
                "error_type": error_type,
                "game_id": game_id,
                **details
            }
        )

    @staticmethod
    def log_balance_updated(balance: 'PaymentBalance', old_balance: Decimal, new_balance: Decimal):
        """Log when a payment balance is updated"""
        logger.info(
            "Payment balance updated",
            extra={
                "event": "balance_updated",
                "balance_id": str(balance.id),
                "player_id": str(balance.player_id),
                "game_id": str(balance.game_id),
                "old_balance": str(old_balance),
                "new_balance": str(new_balance),
                "delta": str(new_balance - old_balance),
            }
        )

    @staticmethod
    def log_settlement_calculated(game_id: str, num_suggestions: int, total_amount: Decimal):
        """Log when settlement suggestions are calculated"""
        logger.info(
            "Settlement suggestions calculated",
            extra={
                "event": "settlement_calculated",
                "game_id": game_id,
                "num_suggestions": num_suggestions,
                "total_amount": str(total_amount),
            }
        )


@dataclass
class PlayerPaymentSummary:
    """Summary of a player's payment status"""
    player_id: str
    player_name: str
    poker_net_winnings: Decimal  # From poker games
    total_paid: Decimal  # Amount paid to others
    total_received: Decimal  # Amount received from others
    balance: Decimal  # Payment balance: total_received - net_winnings (can be negative)
    realized_earnings: Decimal  # Actual cash flow: total_received - total_paid
    days_since_last_payment: Optional[int]  # Days since their last payment (as payer)


@dataclass 
class SettlementSuggestion:
    """A suggested payment to optimize settlements"""
    payer_id: str
    payer_name: str
    recipient_id: str
    recipient_name: str
    amount: Decimal


class PaymentService:
    """Service for managing payments and settlements"""
    
    def record_payment(
        self, 
        game_id: str,
        payer_id: str, 
        recipient_id: str, 
        amount: Decimal,
        payment_date: datetime,
        payment_method: Optional[str] = None,
        notes: Optional[str] = None,
        reference_id: Optional[str] = None,
        created_by: str = "admin"
    ) -> PaymentTransaction:
        """
        Record a payment between two players and update balances.
        
        Args:
            game_id: UUID of the game
            payer_id: UUID of player making payment
            recipient_id: UUID of player receiving payment
            amount: Payment amount as Decimal
            payment_date: When payment was made
            payment_method: Optional method (Venmo, Zelle, etc)
            notes: Optional notes
            reference_id: Optional external transaction ID
            created_by: Who created this record (admin code hash)
            
        Returns:
            PaymentTransaction: The created transaction record
            
        Raises:
            ValueError: If validation fails
        """
        start_time = datetime.now()

        with SessionLocal() as db:
            try:
                # Validate inputs
                if payer_id == recipient_id:
                    PaymentLogger.log_payment_error(
                        "validation_error",
                        game_id,
                        {"error": "payer_equals_recipient", "player_id": payer_id}
                    )
                    raise ValueError("Payer and recipient cannot be the same")

                if amount <= 0:
                    PaymentLogger.log_payment_error(
                        "validation_error",
                        game_id,
                        {"error": "invalid_amount", "amount": str(amount)}
                    )
                    raise ValueError("Payment amount must be positive")

                # Verify game exists
                game = db.query(Game).filter(Game.id == game_id).first()
                if not game:
                    PaymentLogger.log_payment_error(
                        "not_found",
                        game_id,
                        {"error": "game_not_found"}
                    )
                    raise ValueError(f"Game {game_id} not found")

                # Verify players exist
                payer = db.query(Player).filter(Player.id == payer_id).first()
                recipient = db.query(Player).filter(Player.id == recipient_id).first()

                if not payer:
                    PaymentLogger.log_payment_error(
                        "not_found",
                        game_id,
                        {"error": "payer_not_found", "payer_id": payer_id}
                    )
                    raise ValueError(f"Payer {payer_id} not found")
                if not recipient:
                    PaymentLogger.log_payment_error(
                        "not_found",
                        game_id,
                        {"error": "recipient_not_found", "recipient_id": recipient_id}
                    )
                    raise ValueError(f"Recipient {recipient_id} not found")

                # Convert to cents for storage
                amount_cents = int(amount * 100)

                # Create payment transaction
                payment = PaymentTransaction(
                    game_id=game_id,
                    payer_id=payer_id,
                    recipient_id=recipient_id,
                    amount_cents=amount_cents,
                    payment_method=payment_method,
                    payment_date=payment_date,
                    status='completed',
                    notes=notes,
                    reference_id=reference_id,
                    created_by=created_by
                )

                db.add(payment)
                db.flush()  # Get the ID

                # Update payment balances
                self._update_payment_balances(db, game_id, [payer_id, recipient_id])

                db.commit()

                # Log successful payment
                duration_ms = (datetime.now() - start_time).total_seconds() * 1000
                PaymentLogger.log_payment_recorded(payment, duration_ms)
                logger.info(f"Recorded payment: {payer.display_name} -> {recipient.display_name}: ${amount}")

                return payment

            except Exception as e:
                db.rollback()
                if not isinstance(e, ValueError):
                    PaymentLogger.log_payment_error(
                        "unexpected_error",
                        game_id,
                        {"error": str(e), "error_type": type(e).__name__}
                    )
                raise

    def get_payment_summary(self, game_id: str) -> List[PlayerPaymentSummary]:
        """
        Get payment summary for all players in a game.

        Returns list of PlayerPaymentSummary objects with current balances.
        """
        with SessionLocal() as db:
            # Ensure balances are up to date
            self._sync_all_balances(db, game_id)
            db.commit()  # Commit the balance sync changes

            # Get all balances for this game with last payment dates
            balances_query = """
                SELECT
                    pb.*,
                    p.display_name,
                    (
                        SELECT MAX(pt.payment_date)
                        FROM payment_transactions pt
                        WHERE pt.game_id = pb.game_id
                        AND pt.payer_id = pb.player_id
                        AND pt.status = 'completed'
                    ) as last_payment_date
                FROM payment_balances pb
                JOIN players p ON pb.player_id = p.id
                WHERE pb.game_id = :game_id
            """

            balances = db.execute(text(balances_query), {"game_id": game_id}).mappings().all()

            summaries = []
            for balance in balances:
                poker_net = Decimal(balance.poker_net_winnings) / 100
                total_paid = Decimal(balance.total_paid) / 100
                total_received = Decimal(balance.total_received) / 100

                # Balance = poker_net + paid - received (negative = owes, positive = owed, zero = settled)
                player_balance = poker_net + total_paid - total_received

                # Realized Earnings = actual cash flow (received - paid)
                realized_earnings = total_received - total_paid

                # Calculate days since last payment
                days_since_last_payment = None
                if balance.last_payment_date:
                    last_payment_date = balance.last_payment_date
                    if isinstance(last_payment_date, str):
                        # Handle string date format
                        last_payment_date = datetime.fromisoformat(last_payment_date.replace('Z', '+00:00'))

                    # Ensure last_payment_date is timezone-aware
                    if last_payment_date.tzinfo is None:
                        last_payment_date = last_payment_date.replace(tzinfo=timezone.utc)

                    # Calculate days difference
                    days_diff = (datetime.now(timezone.utc) - last_payment_date).days
                    days_since_last_payment = days_diff

                summaries.append(PlayerPaymentSummary(
                    player_id=str(balance.player_id),
                    player_name=balance.display_name,
                    poker_net_winnings=poker_net,
                    total_paid=total_paid,
                    total_received=total_received,
                    balance=player_balance,
                    realized_earnings=realized_earnings,
                    days_since_last_payment=days_since_last_payment
                ))
            
            # Sort by balance descending (highest owed first)
            summaries.sort(key=lambda x: x.balance, reverse=True)
            
            return summaries

    def get_settlement_suggestions(self, game_id: str) -> List[SettlementSuggestion]:
        """
        Calculate optimal payment suggestions to minimize transactions.
        
        Uses debt minimization algorithm similar to Splitwise.
        """
        summaries = self.get_payment_summary(game_id)
        
        # Calculate who owes what based on net balance: (poker_winnings + paid_out) - received
        # Positive net_balance = player is owed money
        # Negative net_balance = player owes money
        net_balances = []
        for p in summaries:
            net_balance = (p.poker_net_winnings + p.total_paid) - p.total_received
            net_balances.append((p, net_balance))
        
        creditors = [(p, balance) for p, balance in net_balances if balance > 0]  # Owed money
        debtors = [(p, balance) for p, balance in net_balances if balance < 0]   # Owe money
        
        # Sort creditors by amount owed (desc), debtors by debt (asc)
        creditors.sort(key=lambda x: x[1], reverse=True)
        debtors.sort(key=lambda x: x[1])
        
        suggestions = []
        
        # Debt minimization algorithm
        while creditors and debtors:
            creditor_player, creditor_balance = creditors[0]
            debtor_player, debtor_balance = debtors[0]
            
            # Amount to transfer is minimum of what's owed and what's due
            amount = min(creditor_balance, abs(debtor_balance))
            
            if amount > Decimal('0.01'):  # Only suggest payments over 1 cent
                suggestions.append(SettlementSuggestion(
                    payer_id=debtor_player.player_id,
                    payer_name=debtor_player.player_name,
                    recipient_id=creditor_player.player_id, 
                    recipient_name=creditor_player.player_name,
                    amount=amount
                ))
            
            # Update balances
            creditor_balance -= amount
            debtor_balance += amount
            
            # Update the tuples in the lists
            creditors[0] = (creditor_player, creditor_balance)
            debtors[0] = (debtor_player, debtor_balance)
            
            # Remove players who are now settled
            if creditor_balance <= Decimal('0.01'):
                creditors.pop(0)
            if debtor_balance >= Decimal('-0.01'):
                debtors.pop(0)
        
        return suggestions

    def get_payment_history(
        self, 
        game_id: str, 
        limit: int = 1000,
        offset: int = 0
    ) -> List[Dict]:
        """Get payment transaction history for a game"""
        with SessionLocal() as db:
            payments = (
                db.query(
                    PaymentTransaction,
                    Player.display_name.label('payer_name'),
                    db.query(Player.display_name)
                    .filter(Player.id == PaymentTransaction.recipient_id)
                    .correlate(PaymentTransaction)
                    .as_scalar()
                    .label('recipient_name')
                )
                .join(Player, PaymentTransaction.payer_id == Player.id)
                .filter(PaymentTransaction.game_id == game_id)
                .order_by(PaymentTransaction.payment_date.desc())
                .limit(limit)
                .offset(offset)
                .all()
            )
            
            history = []
            for payment, payer_name, recipient_name in payments:
                history.append({
                    'id': str(payment.id),
                    'payer_name': payer_name,
                    'recipient_name': recipient_name,
                    'amount': float(payment.amount_cents) / 100,
                    'payment_method': payment.payment_method,
                    'payment_date': payment.payment_date.isoformat(),
                    'status': payment.status,
                    'notes': payment.notes,
                    'reference_id': payment.reference_id,
                    'created_at': payment.created_at.isoformat()
                })
            
            return history

    def _sync_all_balances(self, db: DBSession, game_id: str) -> None:
        """Sync payment balances for all players in a game"""
        # Get all players who have participated in this game
        # Include players with either session summaries OR payment transactions
        session_players = (
            db.query(SessionPlayerSummary.player_id)
            .join(Session, SessionPlayerSummary.session_id == Session.id)
            .filter(Session.game_id == game_id)
            .distinct()
        )
        
        payment_players = (
            db.query(PaymentTransaction.payer_id.label('player_id'))
            .filter(PaymentTransaction.game_id == game_id)
            .union(
                db.query(PaymentTransaction.recipient_id.label('player_id'))
                .filter(PaymentTransaction.game_id == game_id)
            )
            .distinct()
        )
        
        # Combine both sets of players
        all_player_ids = session_players.union(payment_players).all()
        player_ids = [str(pid[0]) for pid in all_player_ids]
        
        self._update_payment_balances(db, game_id, player_ids)

    def _update_payment_balances(self, db: DBSession, game_id: str, player_ids: List[str]) -> None:
        """Update payment balances for specific players"""
        for player_id in player_ids:
            # Calculate poker net winnings from sessions
            poker_winnings_result = (
                db.query(func.coalesce(func.sum(SessionPlayerSummary.net), 0))
                .join(Session, SessionPlayerSummary.session_id == Session.id)
                .filter(
                    Session.game_id == game_id,
                    SessionPlayerSummary.player_id == player_id
                )
                .scalar()
            )
            poker_winnings = poker_winnings_result or 0
            
            # Calculate total paid by this player
            total_paid = (
                db.query(func.coalesce(func.sum(PaymentTransaction.amount_cents), 0))
                .filter(
                    PaymentTransaction.game_id == game_id,
                    PaymentTransaction.payer_id == player_id,
                    PaymentTransaction.status == 'completed'
                )
                .scalar()
            ) or 0
            
            # Calculate total received by this player
            total_received = (
                db.query(func.coalesce(func.sum(PaymentTransaction.amount_cents), 0))
                .filter(
                    PaymentTransaction.game_id == game_id,
                    PaymentTransaction.recipient_id == player_id,
                    PaymentTransaction.status == 'completed'
                )
                .scalar()
            ) or 0
            
            # Calculate net balance: poker_winnings + total_paid - total_received
            payment_balance = poker_winnings + total_paid - total_received
            
            # Upsert payment balance record
            balance = (
                db.query(PaymentBalance)
                .filter(
                    PaymentBalance.game_id == game_id,
                    PaymentBalance.player_id == player_id
                )
                .first()
            )
            
            if balance:
                balance.total_paid = total_paid
                balance.total_received = total_received
                balance.poker_net_winnings = poker_winnings
                balance.payment_balance = payment_balance
                balance.last_updated = datetime.now(timezone.utc)
            else:
                balance = PaymentBalance(
                    game_id=game_id,
                    player_id=player_id,
                    total_paid=total_paid,
                    total_received=total_received,
                    poker_net_winnings=poker_winnings,
                    payment_balance=payment_balance
                )
                db.add(balance)

            db.flush()