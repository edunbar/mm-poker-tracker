from sqlalchemy import text, and_
from sqlalchemy.orm import joinedload
from db.database import SessionLocal
from db.models import SessionPlayerSummary, Session, Player, Game
from services.audit_middleware import audit_context
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


def get_all_session_summaries(public_code: str) -> Dict[str, Any]:
    """
    Get all SessionPlayerSummary records for a given game's public code.
    Returns detailed information including player names, session details, etc.
    """
    with SessionLocal() as db:
        try:
            # Query with joins to get all related data, ordered by game_number descending (most recent first)
            summaries = db.query(SessionPlayerSummary).join(
                Session, SessionPlayerSummary.session_id == Session.id
            ).join(
                Game, Session.game_id == Game.id
            ).join(
                Player, SessionPlayerSummary.player_id == Player.id
            ).filter(
                Game.public_code == public_code
            ).options(
                joinedload(SessionPlayerSummary.session).joinedload(Session.game),
                joinedload(SessionPlayerSummary.player)
            ).order_by(Session.game_number.desc()).all()

            if not summaries:
                return {"summaries": [], "total_count": 0}

            # Build formatted results using the stored game_number
            formatted_summaries = []
            for summary in summaries:
                formatted_summaries.append({
                    "session_id": str(summary.session_id),
                    "player_id": str(summary.player_id),
                    "player_name": summary.player.display_name,
                    "session_external_id": summary.session.external_id,
                    "session_started_at": summary.session.started_at.isoformat() if summary.session.started_at else None,
                    "session_ended_at": summary.session.ended_at.isoformat() if summary.session.ended_at else None,
                    "buy_in_sum": summary.buy_in_sum,
                    "cash_out_sum": summary.cash_out_sum,
                    "in_game": summary.in_game,
                    "net": summary.net,
                    "names": summary.names,
                    "game_number": summary.session.game_number,
                    "has_csv": bool(summary.session.ledger_csv_content)
                })

            return {
                "summaries": formatted_summaries,
                "total_count": len(formatted_summaries)
            }

        except Exception as e:
            logger.error(f"Error fetching session summaries: {e}")
            raise

def update_session_summary(session_id: str, player_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update specific fields of a SessionPlayerSummary record.
    """
    with SessionLocal() as db:
        with audit_context(operation_type="LEDGER_UPDATE"):
            try:
                # Find the record
                summary = db.query(SessionPlayerSummary).filter(
                    and_(
                        SessionPlayerSummary.session_id == session_id,
                        SessionPlayerSummary.player_id == player_id
                    )
                ).first()

                if not summary:
                    raise ValueError(f"SessionPlayerSummary not found for session_id={session_id}, player_id={player_id}")

                # Update allowed fields
                allowed_fields = ['buy_in_sum', 'cash_out_sum', 'in_game', 'net', 'names']
                updated_fields = []

                for field, value in updates.items():
                    if field == 'game_number':
                        # Skip game_number as it's calculated, not stored
                        continue
                    elif field in allowed_fields:
                        if field == 'names' and not isinstance(value, list):
                            raise ValueError(f"Field 'names' must be a list, got {type(value)}")
                        
                        old_value = getattr(summary, field)
                        setattr(summary, field, value)
                        updated_fields.append({
                            'field': field,
                            'old_value': old_value,
                            'new_value': value
                        })

                if not updated_fields:
                    return {"message": "No valid fields to update", "updated_fields": []}

                db.commit()

                return {
                    "message": "SessionPlayerSummary updated successfully",
                    "session_id": session_id,
                    "player_id": player_id,
                    "updated_fields": updated_fields
                }

            except Exception as e:
                db.rollback()
                logger.error(f"Error updating session summary: {e}")
                raise

def delete_session_summary(session_id: str, player_id: str) -> Dict[str, Any]:
    """
    Delete a SessionPlayerSummary record and clean up orphaned session if no players remain.
    """
    with SessionLocal() as db:
        with audit_context(operation_type="LEDGER_DELETE"):
            try:
                # Find the record
                summary = db.query(SessionPlayerSummary).filter(
                    and_(
                        SessionPlayerSummary.session_id == session_id,
                        SessionPlayerSummary.player_id == player_id
                    )
                ).first()

                if not summary:
                    raise ValueError(f"SessionPlayerSummary not found for session_id={session_id}, player_id={player_id}")

                # Store info before deletion
                deleted_info = {
                    "session_id": str(summary.session_id),
                    "player_id": str(summary.player_id),
                    "buy_in_sum": summary.buy_in_sum,
                    "cash_out_sum": summary.cash_out_sum,
                    "in_game": summary.in_game,
                    "net": summary.net,
                    "names": summary.names
                }

                # Get game_id for payment balance update
                session = db.query(Session).filter(Session.id == session_id).first()
                game_id = str(session.game_id) if session else None
                affected_player_id = str(player_id)

                db.delete(summary)

                # Check if this was the last player in the session
                remaining_players = db.query(SessionPlayerSummary).filter(
                    SessionPlayerSummary.session_id == session_id
                ).count()

                orphaned_session = False
                if remaining_players == 0:
                    # Delete the orphaned session
                    if session:
                        db.delete(session)
                        orphaned_session = True
                        logger.info(f"Deleted orphaned session {session_id}")

                db.flush()

                # Update payment balances after deletion
                if game_id:
                    from services.payment_service import PaymentService
                    from db.models import PaymentBalance
                    payment_service = PaymentService()
                    payment_service._update_payment_balances(db, game_id, [affected_player_id])

                    # Check if player still has any activity in this game
                    player_has_activity = db.query(SessionPlayerSummary).join(
                        Session, SessionPlayerSummary.session_id == Session.id
                    ).filter(
                        Session.game_id == game_id,
                        SessionPlayerSummary.player_id == affected_player_id
                    ).count() > 0

                    # If no activity, remove their payment balance record
                    if not player_has_activity:
                        db.query(PaymentBalance).filter(
                            PaymentBalance.game_id == game_id,
                            PaymentBalance.player_id == affected_player_id
                        ).delete()

                db.commit()

                # Invalidate cache
                game = db.query(Game).filter(Game.id == game_id).first()
                if game:
                    from services.game_summary_service import invalidate_game_cache
                    invalidate_game_cache(game.public_code)

                return {
                    "message": "SessionPlayerSummary deleted successfully",
                    "deleted_record": deleted_info,
                    "orphaned_session_deleted": orphaned_session
                }

            except Exception as e:
                db.rollback()
                logger.error(f"Error deleting session summary: {e}")
                raise

def delete_entire_session(session_id: str) -> Dict[str, Any]:
    """
    Delete an entire session including all player summaries.
    """
    with SessionLocal() as db:
        with audit_context(operation_type="SESSION_DELETE"):
            try:
                # Find the session
                session = db.query(Session).filter(Session.id == session_id).first()
                if not session:
                    raise ValueError(f"Session not found for session_id={session_id}")

                # Get all player summaries before deletion for audit
                summaries = db.query(SessionPlayerSummary).filter(
                    SessionPlayerSummary.session_id == session_id
                ).all()

                deleted_players = []
                affected_player_ids = []
                for summary in summaries:
                    deleted_players.append({
                        "player_id": str(summary.player_id),
                        "player_name": summary.player.display_name if summary.player else "Unknown",
                        "buy_in_sum": summary.buy_in_sum,
                        "cash_out_sum": summary.cash_out_sum,
                        "in_game": summary.in_game,
                        "net": summary.net,
                        "names": summary.names
                    })
                    affected_player_ids.append(str(summary.player_id))

                # Store session info before deletion
                session_info = {
                    "session_id": str(session.id),
                    "external_id": session.external_id,
                    "game_number": session.game_number,
                    "started_at": session.started_at.isoformat() if session.started_at else None,
                    "ended_at": session.ended_at.isoformat() if session.ended_at else None
                }

                game_id = str(session.game_id)

                # Delete the session (CASCADE will delete summaries)
                db.delete(session)
                db.flush()

                # Update payment balances for all affected players
                if affected_player_ids:
                    from services.payment_service import PaymentService
                    from db.models import PaymentBalance
                    payment_service = PaymentService()
                    payment_service._update_payment_balances(db, game_id, affected_player_ids)

                    # Remove payment balance records for players with no remaining activity
                    for player_id in affected_player_ids:
                        player_has_activity = db.query(SessionPlayerSummary).join(
                            Session, SessionPlayerSummary.session_id == Session.id
                        ).filter(
                            Session.game_id == game_id,
                            SessionPlayerSummary.player_id == player_id
                        ).count() > 0

                        if not player_has_activity:
                            db.query(PaymentBalance).filter(
                                PaymentBalance.game_id == game_id,
                                PaymentBalance.player_id == player_id
                            ).delete()

                db.commit()

                # Invalidate cache
                game = db.query(Game).filter(Game.id == game_id).first()
                if game:
                    from services.game_summary_service import invalidate_game_cache
                    invalidate_game_cache(game.public_code)

                return {
                    "message": "Entire session deleted successfully",
                    "deleted_session": session_info,
                    "deleted_players": deleted_players,
                    "total_players_deleted": len(deleted_players),
                    "deleted_count": len(deleted_players)  # For backward compatibility
                }

            except Exception as e:
                db.rollback()
                logger.error(f"Error deleting entire session: {e}")
                raise

def get_session_summary(session_id: str, player_id: str) -> Dict[str, Any]:
    """
    Get a single SessionPlayerSummary record with related data.
    """
    with SessionLocal() as db:
        try:
            summary = db.query(SessionPlayerSummary).join(
                Session, SessionPlayerSummary.session_id == Session.id
            ).join(
                Player, SessionPlayerSummary.player_id == Player.id
            ).filter(
                and_(
                    SessionPlayerSummary.session_id == session_id,
                    SessionPlayerSummary.player_id == player_id
                )
            ).options(
                joinedload(SessionPlayerSummary.session),
                joinedload(SessionPlayerSummary.player)
            ).first()

            if not summary:
                raise ValueError(f"SessionPlayerSummary not found for session_id={session_id}, player_id={player_id}")

            return {
                "session_id": str(summary.session_id),
                "player_id": str(summary.player_id),
                "player_name": summary.player.display_name,
                "session_external_id": summary.session.external_id,
                "session_started_at": summary.session.started_at.isoformat() if summary.session.started_at else None,
                "session_ended_at": summary.session.ended_at.isoformat() if summary.session.ended_at else None,
                "buy_in_sum": summary.buy_in_sum,
                "cash_out_sum": summary.cash_out_sum,
                "in_game": summary.in_game,
                "net": summary.net,
                "names": summary.names
            }

        except Exception as e:
            logger.error(f"Error fetching session summary: {e}")
            raise