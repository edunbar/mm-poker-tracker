"""
SQLAlchemy implementation of payment repositories.

This module provides concrete implementation of the repository interfaces,
mapping between domain entities and SQLAlchemy models for payment operations.
"""

from typing import List, Optional
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text, and_, select, func

from domain.payments.repositories import PaymentRepository, PaymentBalanceRepository
from domain.payments.entities import PaymentTransaction, PlayerBalance
from domain.payments.value_objects import PaymentMethod, PaymentNotes, PaymentReference
from domain.poker.value_objects import GameId, PlayerId, Money
from domain.poker.exceptions import RepositoryError
from db.models import (
    PaymentTransaction as PaymentTransactionModel,
    PaymentBalance as PaymentBalanceModel,
    Player, Game, SessionPlayerSummary, Session as SessionModel
)


class SQLAlchemyPaymentRepository(PaymentRepository):
    """
    SQLAlchemy implementation of PaymentRepository.

    This repository maps between domain entities (PaymentTransaction) and
    SQLAlchemy models (PaymentTransaction).
    """

    def __init__(self, db_session: Session) -> None:
        """
        Initialize the repository with a database session.

        Args:
            db_session: SQLAlchemy database session
        """
        self._db_session = db_session

    def save_transaction(self, transaction: PaymentTransaction) -> PaymentTransaction:
        """
        Save a payment transaction.

        Args:
            transaction: The PaymentTransaction to save

        Returns:
            The saved PaymentTransaction with updated transaction_id

        Raises:
            RepositoryError: If save operation fails
        """
        try:
            # Convert domain entity to SQLAlchemy model
            db_transaction = self._to_db_model(transaction)

            self._db_session.add(db_transaction)
            self._db_session.flush()
            self._db_session.refresh(db_transaction)

            # Return domain entity with updated ID
            return self._to_domain_entity(db_transaction)

        except SQLAlchemyError as e:
            raise RepositoryError("save_transaction", str(e))

    def get_transaction_by_id(self, transaction_id: str) -> Optional[PaymentTransaction]:
        """
        Get a payment transaction by ID.

        Args:
            transaction_id: The transaction identifier

        Returns:
            PaymentTransaction if found, None otherwise
        """
        try:
            db_transaction = self._db_session.query(PaymentTransactionModel).filter(
                PaymentTransactionModel.id == transaction_id
            ).first()

            if db_transaction is None:
                return None

            return self._to_domain_entity(db_transaction)

        except SQLAlchemyError as e:
            raise RepositoryError("get_transaction_by_id", str(e))

    def get_transactions_for_game(self, game_id: GameId) -> List[PaymentTransaction]:
        """
        Get all payment transactions for a game.

        Args:
            game_id: The game identifier

        Returns:
            List of PaymentTransaction objects ordered by payment_date desc
        """
        try:
            db_transactions = self._db_session.query(PaymentTransactionModel).filter(
                PaymentTransactionModel.game_id == game_id.value
            ).order_by(PaymentTransactionModel.payment_date.desc()).all()

            return [self._to_domain_entity(tx) for tx in db_transactions]

        except SQLAlchemyError as e:
            raise RepositoryError("get_transactions_for_game", str(e))

    def get_transactions_for_player(self, player_id: PlayerId, game_id: GameId) -> List[PaymentTransaction]:
        """
        Get all payment transactions involving a specific player in a game.

        Args:
            player_id: The player identifier
            game_id: The game identifier

        Returns:
            List of PaymentTransaction objects where player is payer or recipient
        """
        try:
            db_transactions = self._db_session.query(PaymentTransactionModel).filter(
                and_(
                    PaymentTransactionModel.game_id == game_id.value,
                    ((PaymentTransactionModel.payer_id == player_id.value) |
                     (PaymentTransactionModel.recipient_id == player_id.value))
                )
            ).order_by(PaymentTransactionModel.payment_date.desc()).all()

            return [self._to_domain_entity(tx) for tx in db_transactions]

        except SQLAlchemyError as e:
            raise RepositoryError("get_transactions_for_player", str(e))

    def delete_transaction(self, transaction_id: str) -> bool:
        """
        Delete a payment transaction.

        Args:
            transaction_id: The transaction identifier

        Returns:
            True if transaction was deleted, False if it didn't exist

        Raises:
            RepositoryError: If delete operation fails
        """
        try:
            db_transaction = self._db_session.query(PaymentTransactionModel).filter(
                PaymentTransactionModel.id == transaction_id
            ).first()

            if db_transaction is None:
                return False

            self._db_session.delete(db_transaction)
            self._db_session.flush()  # Note: Caller is responsible for commit
            return True

        except SQLAlchemyError as e:
            raise RepositoryError("delete_transaction", str(e))

    def _to_db_model(self, transaction: PaymentTransaction) -> PaymentTransactionModel:
        """
        Convert a domain PaymentTransaction to a SQLAlchemy model.

        Args:
            transaction: The domain entity

        Returns:
            SQLAlchemy PaymentTransaction model
        """
        # Convert cents to dollars for database storage
        amount_dollars = transaction.amount.amount / 100

        return PaymentTransactionModel(
            game_id=transaction.game_id.value,
            payer_id=transaction.payer_id.value,
            recipient_id=transaction.recipient_id.value,
            amount_cents=transaction.amount.amount,  # Store amount in cents
            payment_date=transaction.payment_date,
            payment_method=str(transaction.payment_method) if transaction.payment_method else None,
            notes=str(transaction.notes) if transaction.notes else None,
            reference_id=str(transaction.reference_id) if transaction.reference_id else None,
            created_by=transaction.created_by
        )

    def _to_domain_entity(self, db_transaction: PaymentTransactionModel) -> PaymentTransaction:
        """
        Convert a SQLAlchemy PaymentTransaction to a domain entity.

        Args:
            db_transaction: The SQLAlchemy model

        Returns:
            Domain PaymentTransaction entity
        """
        # Convert strings to value objects
        payment_method = PaymentMethod(db_transaction.payment_method) if db_transaction.payment_method else None
        notes = PaymentNotes(db_transaction.notes) if db_transaction.notes else None
        reference_id = PaymentReference(db_transaction.reference_id) if db_transaction.reference_id else None

        return PaymentTransaction(
            transaction_id=str(db_transaction.id),
            game_id=GameId(str(db_transaction.game_id)),
            payer_id=PlayerId(str(db_transaction.payer_id)),
            recipient_id=PlayerId(str(db_transaction.recipient_id)),
            amount=Money(db_transaction.amount_cents),  # Amount already in cents
            payment_date=db_transaction.payment_date,
            payment_method=payment_method,
            notes=notes,
            reference_id=reference_id,
            created_by=db_transaction.created_by
        )


class SQLAlchemyPaymentBalanceRepository(PaymentBalanceRepository):
    """
    SQLAlchemy implementation of PaymentBalanceRepository.

    This repository handles payment balance calculations and storage.
    """

    def __init__(self, db_session: Session) -> None:
        """
        Initialize the repository with a database session.

        Args:
            db_session: SQLAlchemy database session
        """
        self._db_session = db_session

    def get_balance(self, player_id: PlayerId, game_id: GameId) -> Optional[PlayerBalance]:
        """
        Get a player's payment balance for a specific game.

        Args:
            player_id: The player identifier
            game_id: The game identifier

        Returns:
            PlayerBalance if found, None otherwise
        """
        try:
            db_balance = self._db_session.query(PaymentBalanceModel).filter(
                and_(
                    PaymentBalanceModel.player_id == player_id.value,
                    PaymentBalanceModel.game_id == game_id.value
                )
            ).first()

            if db_balance is None:
                return None

            return self._to_domain_entity(db_balance)

        except SQLAlchemyError as e:
            raise RepositoryError("get_balance", str(e))

    def get_all_balances_for_game(self, game_id: GameId) -> List[PlayerBalance]:
        """
        Get all player balances for a specific game.

        This includes ALL players who have session summaries for this game,
        even if they haven't been involved in any payments yet.

        Args:
            game_id: The game identifier

        Returns:
            List of PlayerBalance objects
        """
        try:
            # Get all players who have session summaries for this game
            player_ids_in_game = self._db_session.query(SessionPlayerSummary.player_id).join(
                SessionModel, SessionPlayerSummary.session_id == SessionModel.id
            ).filter(
                SessionModel.game_id == game_id.value
            ).distinct().all()

            balances = []
            for (player_id,) in player_ids_in_game:
                player_id_obj = PlayerId(str(player_id))

                # Always calculate fresh balances to avoid stale data in concurrent scenarios
                poker_net = self._calculate_poker_net_winnings(game_id, player_id_obj)
                total_paid, total_received, last_payment_date = self._calculate_payment_totals(
                    game_id, player_id_obj
                )

                balance = PlayerBalance(
                    player_id=player_id_obj,
                    game_id=game_id,
                    poker_net_winnings=poker_net,
                    total_paid=total_paid,
                    total_received=total_received,
                    last_payment_date=last_payment_date
                )
                balances.append(balance)

            return balances

        except SQLAlchemyError as e:
            raise RepositoryError("get_all_balances_for_game", str(e))

    def save_balance(self, balance: PlayerBalance) -> PlayerBalance:
        """
        Save or update a player balance.

        Args:
            balance: The PlayerBalance to save

        Returns:
            The saved PlayerBalance

        Raises:
            RepositoryError: If save operation fails
        """
        try:
            # Use UPSERT with explicit row locking for concurrent safety
            from sqlalchemy.dialects.postgresql import insert

            # Convert balance to dict for upsert
            balance_data = {
                'game_id': balance.game_id.value,
                'player_id': balance.player_id.value,
                'total_paid': balance.total_paid.amount,
                'total_received': balance.total_received.amount,
                'poker_net_winnings': balance.poker_net_winnings.amount,
                'payment_balance': balance.balance.amount,
                'last_updated': datetime.now(timezone.utc)
            }

            # PostgreSQL UPSERT with advisory lock to prevent deadlocks
            # The ON CONFLICT clause handles concurrent inserts atomically
            stmt = insert(PaymentBalanceModel).values(**balance_data)
            upsert_stmt = stmt.on_conflict_do_update(
                constraint='uq_payment_balances_game_player',
                set_={
                    'total_paid': stmt.excluded.total_paid,
                    'total_received': stmt.excluded.total_received,
                    'poker_net_winnings': stmt.excluded.poker_net_winnings,
                    'payment_balance': stmt.excluded.payment_balance,
                    'last_updated': stmt.excluded.last_updated
                }
            ).returning(PaymentBalanceModel.id)

            self._db_session.execute(upsert_stmt)
            self._db_session.flush()  # Note: Caller is responsible for commit
            return balance

        except SQLAlchemyError as e:
            raise RepositoryError("save_balance", str(e))

    def update_balances_for_players(self, game_id: GameId, player_ids: List[PlayerId]) -> None:
        """
        Recalculate and update payment balances for specific players in a game.

        This method recalculates balances based on current poker winnings and payments.

        Args:
            game_id: The game identifier
            player_ids: List of player identifiers to update

        Raises:
            RepositoryError: If update operation fails
        """
        try:
            # Sort player IDs to ensure consistent lock ordering
            # This reduces (but doesn't eliminate) deadlock risk
            sorted_player_ids = sorted(player_ids, key=lambda p: p.value)

            for player_id in sorted_player_ids:
                # Calculate poker net winnings
                poker_net = self._calculate_poker_net_winnings(game_id, player_id)

                # Calculate payment totals
                total_paid, total_received, last_payment_date = self._calculate_payment_totals(
                    game_id, player_id
                )

                # Create or update balance
                balance = PlayerBalance(
                    player_id=player_id,
                    game_id=game_id,
                    poker_net_winnings=poker_net,
                    total_paid=total_paid,
                    total_received=total_received,
                    last_payment_date=last_payment_date
                )

                self.save_balance(balance)

        except SQLAlchemyError as e:
            raise RepositoryError("update_balances_for_players", str(e))

    def delete_balance(self, player_id: PlayerId, game_id: GameId) -> bool:
        """
        Delete a player's payment balance record.

        Args:
            player_id: The player identifier
            game_id: The game identifier

        Returns:
            True if balance was deleted, False if it didn't exist

        Raises:
            RepositoryError: If delete operation fails
        """
        try:
            db_balance = self._db_session.query(PaymentBalanceModel).filter(
                and_(
                    PaymentBalanceModel.player_id == player_id.value,
                    PaymentBalanceModel.game_id == game_id.value
                )
            ).first()

            if db_balance is None:
                return False

            self._db_session.delete(db_balance)
            self._db_session.flush()  # Note: Caller is responsible for commit
            return True

        except SQLAlchemyError as e:
            raise RepositoryError("delete_balance", str(e))

    def get_balances_with_player_names(self, public_code: str) -> List[dict]:
        """
        Get payment balances with player names for a game.

        This method returns balance data suitable for API responses,
        including calculated fields and player names.

        Args:
            public_code: The game's public code

        Returns:
            List of dictionaries with balance data and player names
        """
        try:
            # Use the existing SQL query from the original service
            sql = text('''
                SELECT
                    pb.player_id,
                    p.display_name as player_name,
                    pb.poker_net_winnings,
                    pb.total_paid,
                    pb.total_received,
                    pb.balance,
                    pb.realized_earnings,
                    CASE
                        WHEN pb.last_payment_date IS NULL THEN NULL
                        ELSE EXTRACT(DAY FROM (NOW() - pb.last_payment_date))::INTEGER
                    END as days_since_last_payment
                FROM payment_balances pb
                JOIN players p ON pb.player_id = p.id
                JOIN games g ON pb.game_id = g.id
                WHERE g.public_code = :public_code
                ORDER BY pb.balance DESC
            ''')

            result = self._db_session.execute(sql, {"public_code": public_code})
            rows = result.mappings().all()

            return [dict(row) for row in rows]

        except SQLAlchemyError as e:
            raise RepositoryError("get_balances_with_player_names", str(e))

    def _calculate_poker_net_winnings(self, game_id: GameId, player_id: PlayerId) -> Money:
        """Calculate poker net winnings for a player in a game."""
        try:
            result = self._db_session.query(func.coalesce(func.sum(SessionPlayerSummary.net), 0)).join(
                SessionModel, SessionPlayerSummary.session_id == SessionModel.id
            ).filter(
                and_(
                    SessionModel.game_id == game_id.value,
                    SessionPlayerSummary.player_id == player_id.value
                )
            ).scalar()

            return Money(result or 0)

        except SQLAlchemyError as e:
            raise RepositoryError("_calculate_poker_net_winnings", str(e))

    def _calculate_payment_totals(self, game_id: GameId, player_id: PlayerId) -> tuple:
        """Calculate payment totals for a player in a game."""
        try:
            # Calculate total paid (as payer) - amount_cents is already in cents
            paid_result = self._db_session.query(
                func.coalesce(func.sum(PaymentTransactionModel.amount_cents), 0)
            ).filter(
                and_(
                    PaymentTransactionModel.game_id == game_id.value,
                    PaymentTransactionModel.payer_id == player_id.value
                )
            ).scalar()

            total_paid = Money(paid_result or 0)

            # Calculate total received (as recipient) - amount_cents is already in cents
            received_result = self._db_session.query(
                func.coalesce(func.sum(PaymentTransactionModel.amount_cents), 0)
            ).filter(
                and_(
                    PaymentTransactionModel.game_id == game_id.value,
                    PaymentTransactionModel.recipient_id == player_id.value
                )
            ).scalar()

            total_received = Money(received_result or 0)

            # Get last payment date
            last_payment_date = self._db_session.query(
                func.max(PaymentTransactionModel.payment_date)
            ).filter(
                and_(
                    PaymentTransactionModel.game_id == game_id.value,
                    ((PaymentTransactionModel.payer_id == player_id.value) |
                     (PaymentTransactionModel.recipient_id == player_id.value))
                )
            ).scalar()

            return total_paid, total_received, last_payment_date

        except SQLAlchemyError as e:
            raise RepositoryError("_calculate_payment_totals", str(e))

    def _to_db_model(self, balance: PlayerBalance) -> PaymentBalanceModel:
        """
        Convert a domain PlayerBalance to a SQLAlchemy model.

        Args:
            balance: The domain entity

        Returns:
            SQLAlchemy PaymentBalance model
        """
        return PaymentBalanceModel(
            player_id=balance.player_id.value,
            game_id=balance.game_id.value,
            poker_net_winnings=balance.poker_net_winnings.amount,  # Keep in cents
            total_paid=balance.total_paid.amount,                 # Keep in cents
            total_received=balance.total_received.amount,         # Keep in cents
            payment_balance=balance.balance.amount                # Keep in cents, use correct field name
        )

    def _update_db_model(self, db_balance: PaymentBalanceModel, balance: PlayerBalance) -> None:
        """
        Update a SQLAlchemy model with data from a domain entity.

        Args:
            db_balance: The SQLAlchemy model to update
            balance: The domain entity with new data
        """
        db_balance.poker_net_winnings = balance.poker_net_winnings.amount
        db_balance.total_paid = balance.total_paid.amount
        db_balance.total_received = balance.total_received.amount
        db_balance.payment_balance = balance.balance.amount

    def _to_domain_entity(self, db_balance: PaymentBalanceModel) -> PlayerBalance:
        """
        Convert a SQLAlchemy PaymentBalance to a domain entity.

        Args:
            db_balance: The SQLAlchemy model

        Returns:
            Domain PlayerBalance entity
        """
        return PlayerBalance(
            player_id=PlayerId(str(db_balance.player_id)),
            game_id=GameId(str(db_balance.game_id)),
            poker_net_winnings=Money(db_balance.poker_net_winnings),  # Already in cents
            total_paid=Money(db_balance.total_paid),                  # Already in cents
            total_received=Money(db_balance.total_received),          # Already in cents
            last_payment_date=None  # Model doesn't have this field, will be calculated when needed
        )