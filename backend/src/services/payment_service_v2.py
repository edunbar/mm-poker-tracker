"""
Domain-based PaymentService v2

Direct replacement for payment_service.py using domain layer.
Maintains exact API compatibility while using clean domain architecture.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from datetime import datetime, timezone
from typing import List, Dict, Optional
from dataclasses import dataclass

from sqlalchemy.orm import Session as DBSession
from sqlalchemy import text, func, select
from sqlalchemy.exc import IntegrityError

from db.database import SessionLocal
from db.models import (
    Game, Player, PaymentTransaction as PaymentTransactionModel,
    PaymentBalance as PaymentBalanceModel, SessionPlayerSummary, Session
)
from domain.payments.entities import PaymentTransaction, PlayerBalance, SettlementSuggestion
from domain.payments.services import SettlementOptimizer, PaymentValidator
from domain.payments.repositories import PaymentRepository, PaymentBalanceRepository
from domain.poker.value_objects import Money, PlayerId, GameId
from infrastructure.persistence.sqlalchemy.payment_repository import (
    SQLAlchemyPaymentRepository, SQLAlchemyPaymentBalanceRepository
)

# Configure structured logging for payment operations
logger = logging.getLogger(__name__)


class PaymentLogger:
    """Structured logger for payment operations"""

    @staticmethod
    def log_payment_recorded(transaction_id: str, game_id: str, payer_id: str,
                            recipient_id: str, amount_cents: int, payment_method: str,
                            status: str, duration_ms: float):
        """Log when a payment is successfully recorded"""
        logger.info(
            "Payment recorded",
            extra={
                "event": "payment_recorded",
                "transaction_id": transaction_id,
                "game_id": game_id,
                "payer_id": payer_id,
                "recipient_id": recipient_id,
                "amount_cents": amount_cents,
                "payment_method": payment_method,
                "status": status,
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
    def log_balance_updated(balance_id: str, player_id: str, game_id: str,
                           old_balance: Decimal, new_balance: Decimal):
        """Log when a payment balance is updated"""
        logger.info(
            "Payment balance updated",
            extra={
                "event": "balance_updated",
                "balance_id": balance_id,
                "player_id": player_id,
                "game_id": game_id,
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
    """Summary of a player's payment status - maintains compatibility with old service."""
    player_id: str
    player_name: str
    poker_net_winnings: Decimal
    total_paid: Decimal
    total_received: Decimal
    balance: Decimal
    realized_earnings: Decimal
    days_since_last_payment: Optional[int]


@dataclass
class SettlementSuggestionCompat:
    """Settlement suggestion - maintains compatibility with old service."""
    payer_id: str
    payer_name: str
    recipient_id: str
    recipient_name: str
    amount: Decimal


class PaymentService:
    """
    Domain-based PaymentService that replaces the old direct database access approach.

    Uses domain entities and services while maintaining exact API compatibility
    with existing Flask routes.
    """

    def __init__(self, db_session: DBSession):
        """
        Initialize payment service.

        Args:
            db_session: SQLAlchemy session (REQUIRED). Session lifecycle is managed
                       by the caller (typically the web layer).
        """
        if db_session is None:
            raise ValueError("db_session is required - services do not manage sessions")
        self._db_session = db_session

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
    ) -> PaymentTransactionModel:
        """
        Record a payment between two players using domain layer.

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
            PaymentTransaction model (for compatibility)

        Raises:
            ValueError: For validation errors
        """
        start_time = datetime.now()
        logger.info(f"Recording payment: {payer_id} -> {recipient_id}, ${amount}")

        try:
            db_session = self._db_session
            # Basic validation first (matching original service)
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
            game = db_session.query(Game).filter(Game.id == game_id).first()
            if not game:
                PaymentLogger.log_payment_error(
                    "not_found",
                    game_id,
                    {"error": "game_not_found"}
                )
                raise ValueError(f"Game {game_id} not found")

            # Verify players exist (this will raise appropriate errors for nonexistent players)
            payer = db_session.query(Player).filter(Player.id == payer_id).first()
            recipient = db_session.query(Player).filter(Player.id == recipient_id).first()

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

            # Validate that players have some connection to this game
            # Players should have either session summaries OR payment history in this game
            from db.models import SessionPlayerSummary, Session, PaymentTransaction as PaymentTransactionModel

            def player_has_game_connection(player_id: str, game_id: str) -> bool:
                # Check if player has session summaries in this game
                has_sessions = db_session.query(SessionPlayerSummary).join(
                    Session, SessionPlayerSummary.session_id == Session.id
                ).filter(
                    Session.game_id == game_id,
                    SessionPlayerSummary.player_id == player_id
                ).first() is not None

                # Check if player has payment history in this game
                has_payments = db_session.query(PaymentTransactionModel).filter(
                    PaymentTransactionModel.game_id == game_id
                ).filter(
                    (PaymentTransactionModel.payer_id == player_id) |
                    (PaymentTransactionModel.recipient_id == player_id)
                ).first() is not None

                return has_sessions or has_payments

            if not player_has_game_connection(payer_id, game_id):
                raise ValueError(f"Payer {payer_id} has no connection to game {game_id}")
            if not player_has_game_connection(recipient_id, game_id):
                raise ValueError(f"Recipient {recipient_id} has no connection to game {game_id}")

            # Import PaymentTransactionModel for use throughout method
            from db.models import PaymentTransaction as PaymentTransactionModel

            # Check for duplicate reference_id to ensure idempotency
            if reference_id:
                existing_payment = db_session.query(PaymentTransactionModel).filter(
                    PaymentTransactionModel.game_id == game_id,
                    PaymentTransactionModel.reference_id == reference_id
                ).first()

                if existing_payment:
                    raise ValueError(f"Payment with reference_id '{reference_id}' already exists")

            # Convert to domain objects
            domain_game_id = GameId(game_id)  # Accept UUID for compatibility
            domain_payer_id = PlayerId(payer_id)
            domain_recipient_id = PlayerId(recipient_id)
            # Convert to cents with proper rounding (Money expects cents)
            from decimal import Decimal, ROUND_HALF_UP
            amount_cents = int(Decimal(str(amount)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP) * 100)
            domain_amount = Money(amount_cents)

            # Create domain transaction using factory method
            domain_transaction = PaymentTransaction.create_new(
                game_id=domain_game_id,
                payer_id=domain_payer_id,
                recipient_id=domain_recipient_id,
                amount=domain_amount,
                payment_date=payment_date,
                payment_method=payment_method,
                notes=notes,
                reference_id=reference_id,
                created_by=created_by
            )

            # Create repositories with this session
            payment_repo = SQLAlchemyPaymentRepository(db_session)
            balance_repo = SQLAlchemyPaymentBalanceRepository(db_session)

            # Save transaction using repository
            try:
                saved_transaction = payment_repo.save_transaction(domain_transaction)
            except IntegrityError as e:
                # Check if this is a duplicate reference_id constraint violation
                if reference_id and "uq_payment_transactions_game_reference" in str(e):
                    raise ValueError(f"Payment with reference_id '{reference_id}' already exists")
                raise  # Re-raise original error if not our constraint
            except Exception as e:
                # Check if this might be a duplicate reference_id race condition (fallback)
                if reference_id and ("duplicate" in str(e).lower() or "unique" in str(e).lower()):
                    # Double-check if a payment with this reference_id was created concurrently
                    existing_payment = db_session.query(PaymentTransactionModel).filter(
                        PaymentTransactionModel.game_id == game_id,
                        PaymentTransactionModel.reference_id == reference_id
                    ).first()
                    if existing_payment:
                        raise ValueError(f"Payment with reference_id '{reference_id}' already exists")
                raise  # Re-raise original error if not a duplicate

            # Update balances using repository
            affected_player_ids = [domain_payer_id, domain_recipient_id]
            balance_repo.update_balances_for_players(domain_game_id, affected_player_ids)

            # Convert back to model for compatibility
            db_transaction = db_session.query(PaymentTransactionModel).filter(
                PaymentTransactionModel.id == saved_transaction.transaction_id
            ).first()

            # Log successful payment
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            PaymentLogger.log_payment_recorded(
                transaction_id=str(db_transaction.id),
                game_id=game_id,
                payer_id=payer_id,
                recipient_id=recipient_id,
                amount_cents=db_transaction.amount_cents,
                payment_method=payment_method or "",
                status=db_transaction.status,
                duration_ms=duration_ms
            )

            # Note: Caller is responsible for commit/rollback
            logger.info(f"Payment recorded successfully: {db_transaction.id}")
            return db_transaction

        except ValueError as e:
            logger.error(f"Validation error recording payment: {e}")
            raise

        except Exception as e:
            PaymentLogger.log_payment_error(
                "unexpected_error",
                game_id,
                {"error": str(e), "error_type": type(e).__name__}
            )
            logger.error(f"Unexpected error recording payment: {e}")
            raise ValueError(f"Internal error: {str(e)}")

    def get_payment_summary(self, game_id: str) -> List[PlayerPaymentSummary]:
        """
        Get payment summary for all players in a game.

        Args:
            game_id: UUID of the game

        Returns:
            List of PlayerPaymentSummary objects (maintains compatibility)
        """
        logger.debug(f"Getting payment summary for game {game_id}")

        try:
            db_session = self._db_session
            # Convert game_id to GameId and get balances using repository
            domain_game_id = GameId(game_id)  # Accept UUID for compatibility
            balance_repo = SQLAlchemyPaymentBalanceRepository(db_session)
            player_balances = balance_repo.get_all_balances_for_game(domain_game_id)

            # Convert to compatible format
            summaries = []
            for balance in player_balances:
                # Use days_balance_negative (how long balance has been negative)
                # instead of days_since_last_payment
                days_balance_neg = balance.days_balance_negative(datetime.now(timezone.utc))

                summaries.append(PlayerPaymentSummary(
                    player_id=str(balance.player_id),
                    player_name=self._get_player_name(balance.player_id, db_session),
                    poker_net_winnings=balance.poker_net_winnings.amount / 100,  # Convert cents to dollars
                    total_paid=balance.total_paid.amount / 100,
                    total_received=balance.total_received.amount / 100,
                    balance=balance.balance.amount / 100,
                    realized_earnings=balance.realized_earnings.amount / 100,
                    days_since_last_payment=days_balance_neg  # Now represents days balance negative
                ))

            # Sort by balance descending (highest owed first)
            summaries.sort(key=lambda x: x.balance, reverse=True)

            return summaries

        except Exception as e:
            logger.error(f"Error getting payment summary: {e}")
            raise ValueError(f"Internal error: {str(e)}")

    def get_settlement_suggestions(self, game_id: str) -> List[SettlementSuggestionCompat]:
        """
        Calculate optimal payment suggestions using domain service.

        Args:
            game_id: UUID of the game

        Returns:
            List of SettlementSuggestion objects (maintains compatibility)
        """
        logger.debug(f"Getting settlement suggestions for game {game_id}")

        try:
            db_session = self._db_session
            # Convert game_id and get balances using repository
            domain_game_id = GameId(game_id)  # Accept UUID for compatibility
            balance_repo = SQLAlchemyPaymentBalanceRepository(db_session)
            player_balances = balance_repo.get_all_balances_for_game(domain_game_id)

            # Use domain service to calculate optimal settlements
            domain_suggestions = SettlementOptimizer.calculate_optimal_settlements(player_balances)

            # Convert to compatible format
            suggestions = []
            for suggestion in domain_suggestions:
                payer_name = self._get_player_name(suggestion.payer_id, db_session)
                recipient_name = self._get_player_name(suggestion.recipient_id, db_session)

                suggestions.append(SettlementSuggestionCompat(
                    payer_id=str(suggestion.payer_id),
                    payer_name=payer_name,
                    recipient_id=str(suggestion.recipient_id),
                    recipient_name=recipient_name,
                    amount=suggestion.amount.amount / 100  # Convert cents to dollars
                ))

            logger.info(f"Generated {len(suggestions)} settlement suggestions")
            return suggestions

        except Exception as e:
            logger.error(f"Error getting settlement suggestions: {e}")
            raise ValueError(f"Internal error: {str(e)}")

    def get_payment_history(
        self,
        game_id: str,
        limit: int = 1000,
        offset: int = 0
    ) -> List[Dict]:
        """
        Get payment transaction history for a game.

        Args:
            game_id: UUID of the game
            limit: Maximum number of records to return
            offset: Number of records to skip

        Returns:
            List of payment history dictionaries (maintains compatibility)
        """
        logger.debug(f"Getting payment history for game {game_id}")

        try:
            db_session = self._db_session
            # Convert game_id and get transactions using repository
            domain_game_id = GameId(game_id)  # Accept UUID for compatibility
            payment_repo = SQLAlchemyPaymentRepository(db_session)
            transactions = payment_repo.get_transactions_for_game(domain_game_id)

            # Apply limit and offset manually (repositories don't support pagination yet)
            paginated_transactions = transactions[offset:offset + limit]

            history = []
            for transaction in paginated_transactions:
                payer_name = self._get_player_name(transaction.payer_id, db_session)
                recipient_name = self._get_player_name(transaction.recipient_id, db_session)

                history.append({
                    'id': transaction.transaction_id,
                    'payer_name': payer_name,
                    'recipient_name': recipient_name,
                    'amount': transaction.get_amount_dollars(),
                    'payment_date': transaction.payment_date.isoformat(),
                    'payment_method': str(transaction.payment_method) if transaction.payment_method else None,
                    'notes': str(transaction.notes) if transaction.notes else None,
                    'reference_id': str(transaction.reference_id) if transaction.reference_id else None,
                    'created_by': transaction.created_by,
                    'created_at': None  # Not available in domain entity, could be added if needed
                })

            logger.info(f"Retrieved {len(history)} payment records")
            return history

        except Exception as e:
            logger.error(f"Error getting payment history: {e}")
            raise ValueError(f"Internal error: {str(e)}")

    def delete_payment(self, payment_id: str) -> bool:
        """
        Delete a payment transaction.

        Args:
            payment_id: UUID of the payment to delete

        Returns:
            True if deleted, False if not found

        Raises:
            ValueError: For validation errors
        """
        logger.info(f"Deleting payment {payment_id}")

        try:
            db_session = self._db_session
            # Create repositories with this session
            payment_repo = SQLAlchemyPaymentRepository(db_session)
            balance_repo = SQLAlchemyPaymentBalanceRepository(db_session)

            # Get transaction first to extract game and player info
            transaction = payment_repo.get_transaction_by_id(payment_id)

            if not transaction:
                logger.warning(f"Payment not found: {payment_id}")
                return False

            # Store details for balance update
            game_id = transaction.game_id
            payer_id = transaction.payer_id
            recipient_id = transaction.recipient_id

            # Delete the transaction using repository
            deleted = payment_repo.delete_transaction(payment_id)

            if deleted:
                # Update balances after deletion
                affected_player_ids = [payer_id, recipient_id]
                balance_repo.update_balances_for_players(game_id, affected_player_ids)

                # Note: Caller is responsible for commit/rollback
                logger.info(f"Payment {payment_id} deleted successfully")
                return True
            else:
                return False

        except Exception as e:
            logger.error(f"Error deleting payment: {e}")
            raise ValueError(f"Internal error: {str(e)}")

    def _update_payment_balances(self, db_session: DBSession, game_id: str, player_ids: list[str]) -> None:
        """
        Update payment balances for specific players.

        This method provides compatibility with V1 service while using V2 domain logic.
        It recalculates poker winnings and payment balances for the given players.

        Args:
            db_session: Database session to use
            game_id: Game UUID as string
            player_ids: List of player UUIDs as strings
        """
        try:
            from domain.poker.value_objects import GameId, PlayerId
            from infrastructure.persistence.sqlalchemy.payment_repository import SQLAlchemyPaymentBalanceRepository

            logger.info(f"Updating payment balances for {len(player_ids)} player(s) in game {game_id}")

            # Convert to domain types (GameId accepts both UUID and 5-char public code)
            domain_game_id = GameId(game_id)
            domain_player_ids = [PlayerId(pid) for pid in player_ids]

            # Use repository to update balances
            balance_repo = SQLAlchemyPaymentBalanceRepository(db_session)
            balance_repo.update_balances_for_players(domain_game_id, domain_player_ids)

            logger.info(f"Successfully updated payment balances for {len(player_ids)} player(s)")

        except Exception as e:
            logger.error(f"Error updating payment balances: {e}")
            raise

    # Private helper methods

    def _get_player_name(self, player_id: PlayerId, db_session: DBSession) -> str:
        """Get display name for a player."""
        player = db_session.query(Player).filter(Player.id == str(player_id)).first()
        return player.display_name if player else f"Player {player_id}"

