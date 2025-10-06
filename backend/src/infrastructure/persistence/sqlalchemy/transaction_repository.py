"""
SQLAlchemy implementation of TransactionRepository.
"""

from typing import List, Optional, Dict
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func
import logging

from domain.live_game.repositories import TransactionRepository
from domain.live_game.entities import LiveGameTransaction
from domain.live_game.value_objects import LiveGameId, ParticipantId, TransactionId
from domain.identity.value_objects import UserId
from domain.poker.exceptions import RepositoryError
from db.models import LiveGameTransaction as LiveGameTransactionModel

logger = logging.getLogger(__name__)


class SQLAlchemyTransactionRepository(TransactionRepository):
    """SQLAlchemy implementation of transaction repository."""

    def __init__(self, db_session: Session):
        self._db_session = db_session

    def get_by_id(self, transaction_id: TransactionId) -> Optional[LiveGameTransaction]:
        """Retrieve a transaction by ID."""
        try:
            model = self._db_session.query(LiveGameTransactionModel).filter(
                LiveGameTransactionModel.id == str(transaction_id)
            ).first()

            return self._to_entity(model) if model else None

        except SQLAlchemyError as e:
            raise RepositoryError("get_by_id", str(e))

    def get_by_live_game(self, live_game_id: LiveGameId) -> List[LiveGameTransaction]:
        """Get all transactions for a live game."""
        try:
            models = self._db_session.query(LiveGameTransactionModel).filter(
                LiveGameTransactionModel.live_game_id == str(live_game_id)
            ).order_by(LiveGameTransactionModel.created_at).all()

            return [self._to_entity(model) for model in models]

        except SQLAlchemyError as e:
            raise RepositoryError("get_by_live_game", str(e))

    def get_pending_by_live_game(self, live_game_id: LiveGameId) -> List[LiveGameTransaction]:
        """Get pending transactions for a live game."""
        try:
            models = self._db_session.query(LiveGameTransactionModel).filter(
                LiveGameTransactionModel.live_game_id == str(live_game_id),
                LiveGameTransactionModel.status == 'pending'
            ).order_by(LiveGameTransactionModel.created_at).all()

            return [self._to_entity(model) for model in models]

        except SQLAlchemyError as e:
            raise RepositoryError("get_pending_by_live_game", str(e))

    def get_by_participant(self, participant_id: ParticipantId) -> List[LiveGameTransaction]:
        """Get all transactions for a participant."""
        try:
            models = self._db_session.query(LiveGameTransactionModel).filter(
                LiveGameTransactionModel.participant_id == str(participant_id)
            ).order_by(LiveGameTransactionModel.created_at).all()

            return [self._to_entity(model) for model in models]

        except SQLAlchemyError as e:
            raise RepositoryError("get_by_participant", str(e))

    def get_approved_by_participant(self, participant_id: ParticipantId) -> List[LiveGameTransaction]:
        """Get approved transactions for a participant."""
        try:
            models = self._db_session.query(LiveGameTransactionModel).filter(
                LiveGameTransactionModel.participant_id == str(participant_id),
                LiveGameTransactionModel.status == 'approved'
            ).order_by(LiveGameTransactionModel.created_at).all()

            return [self._to_entity(model) for model in models]

        except SQLAlchemyError as e:
            raise RepositoryError("get_approved_by_participant", str(e))

    def create(self, transaction: LiveGameTransaction) -> LiveGameTransaction:
        """Create a new transaction."""
        try:
            model = LiveGameTransactionModel(
                live_game_id=str(transaction.live_game_id),
                participant_id=str(transaction.participant_id),
                user_id=str(transaction.user_id),
                transaction_type=transaction.transaction_type,
                amount=transaction.amount,
                status=transaction.status,
                created_at=transaction.created_at,
                approved_by_user_id=str(transaction.approved_by_user_id) if transaction.approved_by_user_id else None,
                approved_at=transaction.approved_at,
                notes=transaction.notes,
                original_amount=transaction.original_amount,
                edited_at=transaction.edited_at,
                edited_by_user_id=str(transaction.edited_by_user_id) if transaction.edited_by_user_id else None
            )

            self._db_session.add(model)
            self._db_session.flush()

            return self._to_entity(model)

        except SQLAlchemyError as e:
            self._db_session.rollback()
            raise RepositoryError("create", str(e))

    def update(self, transaction: LiveGameTransaction) -> LiveGameTransaction:
        """Update an existing transaction."""
        try:
            model = self._db_session.query(LiveGameTransactionModel).filter(
                LiveGameTransactionModel.id == str(transaction.id)
            ).first()

            if not model:
                raise RepositoryError("update", f"Transaction not found: {transaction.id}")

            # Update fields
            model.transaction_type = transaction.transaction_type
            model.amount = transaction.amount
            model.status = transaction.status
            model.approved_by_user_id = str(transaction.approved_by_user_id) if transaction.approved_by_user_id else None
            model.approved_at = transaction.approved_at
            model.notes = transaction.notes
            model.original_amount = transaction.original_amount
            model.edited_at = transaction.edited_at
            model.edited_by_user_id = str(transaction.edited_by_user_id) if transaction.edited_by_user_id else None

            self._db_session.flush()

            return self._to_entity(model)

        except SQLAlchemyError as e:
            self._db_session.rollback()
            raise RepositoryError("update", str(e))

    def calculate_participant_stats(self, participant_id: ParticipantId) -> Dict[str, Decimal]:
        """
        Calculate financial statistics for a participant.

        Only includes APPROVED transactions in calculations.

        IMPORTANT: Cash-out means LEAVING the table!
        - If player has cashed out → chips_on_table = $0 (they left!)
        - If player still playing → chips_on_table = total_buy_ins (estimate)
        """
        try:
            # Query approved transactions for this participant with counts
            result = self._db_session.query(
                LiveGameTransactionModel.transaction_type,
                func.sum(LiveGameTransactionModel.amount).label('total'),
                func.count(LiveGameTransactionModel.id).label('count')
            ).filter(
                LiveGameTransactionModel.participant_id == str(participant_id),
                LiveGameTransactionModel.status == 'approved'
            ).group_by(LiveGameTransactionModel.transaction_type).all()

            # Calculate totals
            total_buy_ins = Decimal('0.00')
            total_cash_outs = Decimal('0.00')
            buy_in_count = 0
            cash_out_count = 0

            for transaction_type, total, count in result:
                if transaction_type == 'buy_in':
                    total_buy_ins = Decimal(str(total)) if total else Decimal('0.00')
                    buy_in_count = count
                elif transaction_type == 'cash_out':
                    total_cash_outs = Decimal(str(total)) if total else Decimal('0.00')
                    cash_out_count = count

            # Calculate derived values
            net_result = total_cash_outs - total_buy_ins

            # CRITICAL FIX: Cash-out means LEAVING the table!
            # If player has cashed out, they have $0 on table (they left!)
            has_cashed_out = cash_out_count > 0

            if has_cashed_out:
                chips_on_table = Decimal('0.00')  # Player left the table
            else:
                # Player still at table, chips = total buy-ins
                # (we don't track hand-by-hand, so this is best estimate)
                chips_on_table = total_buy_ins

            return {
                'total_buy_ins': total_buy_ins,
                'total_cash_outs': total_cash_outs,
                'net_result': net_result,
                'chips_on_table': chips_on_table,
                'buy_in_count': buy_in_count,
                'cash_out_count': cash_out_count,
                'has_cashed_out': has_cashed_out
            }

        except SQLAlchemyError as e:
            raise RepositoryError("calculate_participant_stats", str(e))

    def _to_entity(self, model: LiveGameTransactionModel) -> LiveGameTransaction:
        """Convert SQLAlchemy model to domain entity."""
        return LiveGameTransaction(
            id=TransactionId(str(model.id)),
            live_game_id=LiveGameId(str(model.live_game_id)),
            participant_id=ParticipantId(str(model.participant_id)),
            user_id=UserId(str(model.user_id)),
            transaction_type=model.transaction_type,
            amount=Decimal(str(model.amount)),
            status=model.status,
            created_at=model.created_at,
            approved_by_user_id=UserId(str(model.approved_by_user_id)) if model.approved_by_user_id else None,
            approved_at=model.approved_at,
            notes=model.notes,
            original_amount=Decimal(str(model.original_amount)) if model.original_amount else None,
            edited_at=model.edited_at,
            edited_by_user_id=UserId(str(model.edited_by_user_id)) if model.edited_by_user_id else None
        )
