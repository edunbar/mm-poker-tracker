"""
Domain-based LedgerService v2

Direct replacement for ledger_service.py using domain layer.
Maintains exact API compatibility while using clean domain architecture.
"""

from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional

from sqlalchemy.orm import Session as DBSession

from db.database import SessionLocal
from domain.ledger.services import LedgerManagementService
from domain.ledger.entities import LedgerEntry, SessionLedger
from domain.poker.exceptions import RepositoryError
from infrastructure.persistence.sqlalchemy.ledger_repository import SQLAlchemyLedgerRepository
from services.audit_middleware import audit_context

logger = logging.getLogger(__name__)


class LedgerService:
    """
    Domain-based LedgerService that replaces the old function-based approach.

    Uses domain entities and repositories for ledger management while maintaining
    exact API compatibility with existing Flask routes.
    """

    def __init__(self, db_session: DBSession):
        """
        Initialize with required database session.

        Args:
            db_session: SQLAlchemy session (REQUIRED). Session lifecycle is managed
                       by the caller (typically the web layer).

        Raises:
            ValueError: If db_session is None
        """
        if db_session is None:
            raise ValueError("db_session is required - services do not manage sessions")

        self._db_session = db_session
        self._repository = SQLAlchemyLedgerRepository(self._db_session)
        self._domain_service = LedgerManagementService(self._repository)

    def get_all_session_summaries(self, public_code: str) -> Dict[str, Any]:
        """
        Get all SessionPlayerSummary records for a given game's public code.
        Maintains exact compatibility with legacy service.

        Args:
            public_code: The game's public code

        Returns:
            Dictionary with summaries and total_count in legacy format
        """
        try:
            entries = self._domain_service.get_game_ledger(public_code)

            if not entries:
                return {"summaries": [], "total_count": 0}

            # Convert domain entities to legacy format
            formatted_summaries = [entry.to_dict() for entry in entries]

            return {
                "summaries": formatted_summaries,
                "total_count": len(formatted_summaries)
            }

        except RepositoryError as e:
            logger.error(f"Repository error fetching session summaries: {e}")
            raise Exception(f"Error fetching session summaries: {e}")
        except Exception as e:
            logger.error(f"Error fetching session summaries: {e}")
            raise

    def update_session_summary(self, session_id: str, player_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update specific fields of a SessionPlayerSummary record.
        Maintains exact compatibility with legacy service.

        Args:
            session_id: The session identifier
            player_id: The player identifier
            updates: Dictionary of field updates

        Returns:
            Dictionary with update results in legacy format
        """
        with audit_context(operation_type="LEDGER_UPDATE"):
            try:
                # Filter to allowed fields (same as legacy service)
                allowed_fields = ['buy_in_sum', 'cash_out_sum', 'in_game', 'net', 'names']
                filtered_updates = {}
                updated_fields = []

                for field, value in updates.items():
                    if field == 'game_number':
                        # Skip game_number as it's calculated, not stored
                        continue
                    elif field in allowed_fields:
                        if field == 'names' and not isinstance(value, list):
                            raise ValueError(f"Field 'names' must be a list, got {type(value)}")

                        # Get old value for audit
                        old_entry = self._domain_service.get_ledger_entry(session_id, player_id)
                        if old_entry is None:
                            raise ValueError(f"SessionPlayerSummary not found for session_id={session_id}, player_id={player_id}")

                        old_value = self._get_legacy_field_value(old_entry, field)
                        filtered_updates[field] = value
                        updated_fields.append({
                            'field': field,
                            'old_value': old_value,
                            'new_value': value
                        })

                if not filtered_updates:
                    return {"message": "No valid fields to update", "updated_fields": []}

                # Update using domain service
                self._domain_service.update_ledger_entry(session_id, player_id, filtered_updates)

                # Update payment balance for this player after ledger change
                self._update_payment_balance_after_update(session_id, player_id)

                return {
                    "message": "SessionPlayerSummary updated successfully",
                    "session_id": session_id,
                    "player_id": player_id,
                    "updated_fields": updated_fields
                }

            except ValueError as e:
                logger.error(f"Validation error updating session summary: {e}")
                raise
            except RepositoryError as e:
                logger.error(f"Repository error updating session summary: {e}")
                raise Exception(f"Error updating session summary: {e}")
            except Exception as e:
                logger.error(f"Error updating session summary: {e}")
                raise

    def delete_session_summary(self, session_id: str, player_id: str) -> Dict[str, Any]:
        """
        Delete a SessionPlayerSummary record and clean up orphaned session if no players remain.
        Maintains exact compatibility with legacy service.

        Args:
            session_id: The session identifier
            player_id: The player identifier

        Returns:
            Dictionary with deletion results in legacy format
        """
        with audit_context(operation_type="LEDGER_DELETE"):
            try:
                # Get entry before deletion for audit
                entry = self._domain_service.get_ledger_entry(session_id, player_id)
                if entry is None:
                    raise ValueError(f"SessionPlayerSummary not found for session_id={session_id}, player_id={player_id}")

                deleted_info = {
                    "session_id": entry.get_session_id(),
                    "player_id": entry.get_player_id(),
                    "buy_in_sum": entry.financial_summary.buy_in_sum,
                    "cash_out_sum": entry.financial_summary.cash_out_sum,
                    "in_game": entry.financial_summary.in_game,
                    "net": entry.financial_summary.net,
                    "names": entry.player_names.session_names
                }

                game_id = str(entry.game_id)
                affected_player_id = entry.get_player_id()

                # Delete the entry
                deleted = self._domain_service.delete_ledger_entry(session_id, player_id)
                if not deleted:
                    raise ValueError("Failed to delete entry")

                # Check if session is now orphaned
                orphaned_session = self._domain_service.check_session_orphaned(session_id)
                if orphaned_session:
                    # Delete the orphaned session
                    self._delete_orphaned_session(session_id)
                    logger.info(f"Deleted orphaned session {session_id}")

                # Update payment balances (integrate with existing payment service)
                self._update_payment_balances_after_deletion(game_id, affected_player_id)

                # Invalidate cache (integrate with existing cache invalidation)
                self._invalidate_game_cache(game_id)

                return {
                    "message": "SessionPlayerSummary deleted successfully",
                    "deleted_record": deleted_info,
                    "orphaned_session_deleted": orphaned_session
                }

            except ValueError as e:
                logger.error(f"Validation error deleting session summary: {e}")
                raise
            except RepositoryError as e:
                logger.error(f"Repository error deleting session summary: {e}")
                raise Exception(f"Error deleting session summary: {e}")
            except Exception as e:
                logger.error(f"Error deleting session summary: {e}")
                raise

    def delete_entire_session(self, session_id: str) -> Dict[str, Any]:
        """
        Delete an entire session including all player summaries.
        Maintains exact compatibility with legacy service.

        Args:
            session_id: The session identifier

        Returns:
            Dictionary with deletion results in legacy format
        """
        with audit_context(operation_type="SESSION_DELETE"):
            try:
                # Get session ledger before deletion for audit
                session_ledger = self._domain_service.get_session_ledger(session_id)
                if session_ledger is None:
                    raise ValueError(f"Session not found for session_id={session_id}")

                # Prepare deletion audit data
                deleted_players = []
                affected_player_ids = []

                for entry in session_ledger.entries:
                    deleted_players.append({
                        "player_id": entry.get_player_id(),
                        "player_name": entry.player_names.display_name,
                        "buy_in_sum": entry.financial_summary.buy_in_sum,
                        "cash_out_sum": entry.financial_summary.cash_out_sum,
                        "in_game": entry.financial_summary.in_game,
                        "net": entry.financial_summary.net,
                        "names": entry.player_names.session_names
                    })
                    affected_player_ids.append(entry.get_player_id())

                session_info = {
                    "session_id": str(session_ledger.session_reference.session_id),
                    "external_id": session_ledger.session_reference.external_id,
                    "game_number": session_ledger.session_reference.game_number,
                    "started_at": None,  # Would need to get from session model
                    "ended_at": None     # Would need to get from session model
                }

                game_id = str(session_ledger.game_id)

                # Delete all entries for the session
                deleted_count = self._domain_service.delete_entire_session(session_id)

                # Delete the session itself (integrate with session management)
                self._delete_session_model(session_id)

                # Update payment balances for all affected players
                for player_id in affected_player_ids:
                    self._update_payment_balances_after_deletion(game_id, player_id)

                # Invalidate cache
                self._invalidate_game_cache(game_id)

                return {
                    "message": "Entire session deleted successfully",
                    "deleted_session": session_info,
                    "deleted_players": deleted_players,
                    "total_players_deleted": len(deleted_players),
                    "deleted_count": len(deleted_players)  # For backward compatibility
                }

            except ValueError as e:
                logger.error(f"Validation error deleting entire session: {e}")
                raise
            except RepositoryError as e:
                logger.error(f"Repository error deleting entire session: {e}")
                raise Exception(f"Error deleting entire session: {e}")
            except Exception as e:
                logger.error(f"Error deleting entire session: {e}")
                raise

    def get_session_summary(self, session_id: str, player_id: str) -> Dict[str, Any]:
        """
        Get a single SessionPlayerSummary record with related data.
        Maintains exact compatibility with legacy service.

        Args:
            session_id: The session identifier
            player_id: The player identifier

        Returns:
            Dictionary with session summary in legacy format
        """
        try:
            entry = self._domain_service.get_ledger_entry(session_id, player_id)
            if entry is None:
                raise ValueError(f"SessionPlayerSummary not found for session_id={session_id}, player_id={player_id}")

            return entry.to_dict()

        except ValueError as e:
            logger.error(f"Error fetching session summary: {e}")
            raise
        except RepositoryError as e:
            logger.error(f"Repository error fetching session summary: {e}")
            raise Exception(f"Error fetching session summary: {e}")
        except Exception as e:
            logger.error(f"Error fetching session summary: {e}")
            raise

    def get_game_statistics(self, public_code: str) -> Dict[str, Any]:
        """
        Get aggregate statistics for a game.

        This method is unique to the v2 service and provides additional
        analytical capabilities.

        Args:
            public_code: The game's public code

        Returns:
            Dictionary with game statistics
        """
        try:
            return self._domain_service.calculate_game_statistics(public_code)
        except RepositoryError as e:
            logger.error(f"Repository error calculating game statistics: {e}")
            raise Exception(f"Error calculating game statistics: {e}")

    def _get_legacy_field_value(self, entry: LedgerEntry, field: str) -> Any:
        """Get field value in legacy format for audit purposes."""
        if field == 'buy_in_sum':
            return entry.financial_summary.buy_in_sum
        elif field == 'cash_out_sum':
            return entry.financial_summary.cash_out_sum
        elif field == 'in_game':
            return entry.financial_summary.in_game
        elif field == 'net':
            return entry.financial_summary.net
        elif field == 'names':
            return entry.player_names.session_names
        else:
            return None

    def _delete_orphaned_session(self, session_id: str) -> None:
        """Delete an orphaned session model. Note: Caller commits."""
        from db.models import Session as SessionModel
        session_model = self._db_session.query(SessionModel).filter(
            SessionModel.id == session_id
        ).first()
        if session_model:
            self._db_session.delete(session_model)
            # Note: Caller is responsible for commit

    def _delete_session_model(self, session_id: str) -> None:
        """Delete a session model. Note: Caller commits."""
        from db.models import Session as SessionModel
        session_model = self._db_session.query(SessionModel).filter(
            SessionModel.id == session_id
        ).first()
        if session_model:
            self._db_session.delete(session_model)
            # Note: Caller is responsible for commit

    def _update_payment_balances_after_deletion(self, game_id: str, player_id: str) -> None:
        """Update payment balances after entry deletion."""
        try:
            from services.payment_service import PaymentService
            from db.models import PaymentBalance, SessionPlayerSummary
            from db.models import Session as SessionModel

            payment_service = PaymentService(self._db_session)
            payment_service._update_payment_balances(self._db_session, game_id, [player_id])

            # Check if player still has activity in this game
            player_has_activity = self._db_session.query(SessionPlayerSummary).join(
                SessionModel, SessionPlayerSummary.session_id == SessionModel.id
            ).filter(
                SessionModel.game_id == game_id,
                SessionPlayerSummary.player_id == player_id
            ).count() > 0

            # If no activity, remove their payment balance record
            if not player_has_activity:
                self._db_session.query(PaymentBalance).filter(
                    PaymentBalance.game_id == game_id,
                    PaymentBalance.player_id == player_id
                ).delete()
                # Note: Caller is responsible for commit

        except Exception as e:
            logger.error(f"Error updating payment balances: {e}")
            # Don't fail the main operation for payment balance issues

    def _invalidate_game_cache(self, game_id: str) -> None:
        """Invalidate game cache after changes."""
        try:
            from db.models import Game
            game = self._db_session.query(Game).filter(Game.id == game_id).first()
            if game:
                from services.game_summary_service import invalidate_game_cache
                invalidate_game_cache(game.public_code)
        except Exception as e:
            logger.error(f"Error invalidating game cache: {e}")
            # Don't fail the main operation for cache issues

    def _update_payment_balance_after_update(self, session_id: str, player_id: str) -> None:
        """Update payment balance for a player after ledger entry changes."""
        try:
            from db.models import Session as SessionModel
            from services.payment_service import PaymentService

            # Get game_id from session
            session = self._db_session.query(SessionModel).filter(
                SessionModel.id == session_id
            ).first()

            if session:
                payment_service = PaymentService(self._db_session)
                payment_service._update_payment_balances(
                    self._db_session,
                    str(session.game_id),
                    [player_id]
                )
                logger.info(f"Updated payment balance for player {player_id}")

        except Exception as e:
            logger.warning(f"Failed to update payment balance after ledger update: {e}")
            # Don't fail the main operation if payment balance update fails


# =============================================================================
# Legacy Function-based API (for backward compatibility)
# =============================================================================

def get_all_session_summaries(public_code: str) -> Dict[str, Any]:
    """
    Legacy function interface for getting all session summaries.

    Maintains backward compatibility with existing code that imports and calls
    this function directly.
    """
    with SessionLocal() as db:
        service = LedgerService(db)
        return service.get_all_session_summaries(public_code)


def update_session_summary(session_id: str, player_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """Legacy function interface for updating session summary."""
    with SessionLocal() as db:
        try:
            service = LedgerService(db)
            result = service.update_session_summary(session_id, player_id, updates)
            db.commit()
            return result
        except Exception:
            db.rollback()
            raise


def delete_session_summary(session_id: str, player_id: str) -> Dict[str, Any]:
    """Legacy function interface for deleting session summary."""
    with SessionLocal() as db:
        try:
            service = LedgerService(db)
            result = service.delete_session_summary(session_id, player_id)
            db.commit()
            return result
        except Exception:
            db.rollback()
            raise


def delete_entire_session(session_id: str) -> Dict[str, Any]:
    """Legacy function interface for deleting entire session."""
    with SessionLocal() as db:
        try:
            service = LedgerService(db)
            result = service.delete_entire_session(session_id)
            db.commit()
            return result
        except Exception:
            db.rollback()
            raise


def get_session_summary(session_id: str, player_id: str) -> Dict[str, Any]:
    """Legacy function interface for getting session summary."""
    with SessionLocal() as db:
        service = LedgerService(db)
        return service.get_session_summary(session_id, player_id)