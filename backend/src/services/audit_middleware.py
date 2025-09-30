from sqlalchemy import event, text
from sqlalchemy.orm import Session as SQLSession
from sqlalchemy.inspection import inspect
from db.models import Base, AuditLog, Player, SessionPlayerSummary, Session, Game, GamePlayer, PaymentTransaction, PaymentBalance
from db.database import SessionLocal
from flask import request, g
from typing import Dict, Any, Optional
import logging
import uuid
import json
from datetime import datetime
from contextlib import contextmanager
from decimal import Decimal

logger = logging.getLogger(__name__)

# Global audit context for tracking request-level information
class AuditContext:
    def __init__(self):
        self.actor_kind: Optional[str] = None
        self.actor_id: Optional[str] = None
        self.operation_type: Optional[str] = None
        self.game_id: Optional[str] = None
        self.session_id: Optional[str] = None
        self.operation_id: Optional[str] = None
        self.enabled: bool = True

    def set_context(self, actor_kind: str = None, actor_id: str = None, 
                   operation_type: str = None, game_id: str = None, 
                   session_id: str = None, operation_id: str = None):
        if actor_kind: self.actor_kind = actor_kind
        if actor_id: self.actor_id = actor_id
        if operation_type: self.operation_type = operation_type
        if game_id: self.game_id = game_id
        if session_id: self.session_id = session_id
        if operation_id: self.operation_id = operation_id

    def clear(self):
        self.actor_kind = None
        self.actor_id = None
        self.operation_type = None
        self.game_id = None
        self.session_id = None
        self.operation_id = None

# Thread-local audit context
_audit_context = AuditContext()

@contextmanager
def audit_context(actor_kind: str = None, actor_id: str = None, 
                 operation_type: str = None, game_id: str = None, 
                 session_id: str = None, operation_id: str = None):
    """Context manager for setting audit information for a block of operations."""
    old_context = {
        'actor_kind': _audit_context.actor_kind,
        'actor_id': _audit_context.actor_id,
        'operation_type': _audit_context.operation_type,
        'game_id': _audit_context.game_id,
        'session_id': _audit_context.session_id,
        'operation_id': _audit_context.operation_id
    }
    
    try:
        _audit_context.set_context(actor_kind, actor_id, operation_type, game_id, session_id, operation_id)
        yield _audit_context
    finally:
        # Restore previous context
        _audit_context.set_context(**old_context)

def disable_audit():
    """Temporarily disable audit logging (useful for audit log writes themselves)."""
    _audit_context.enabled = False

def enable_audit():
    """Re-enable audit logging."""
    _audit_context.enabled = True

def _get_model_name(instance) -> str:
    """Get the model name for audit logging."""
    return instance.__class__.__name__.lower()

def _serialize_model(instance) -> Dict[str, Any]:
    """Serialize a model instance to a dictionary for audit logging."""
    try:
        data = {}
        for column in inspect(instance.__class__).columns:
            value = getattr(instance, column.name, None)
            if value is not None:
                # Handle different data types
                if hasattr(value, 'isoformat'):  # datetime
                    data[column.name] = value.isoformat()
                elif isinstance(value, uuid.UUID):
                    data[column.name] = str(value)
                elif isinstance(value, Decimal):  # Decimal types
                    data[column.name] = float(value)
                elif isinstance(value, list):  # Arrays
                    data[column.name] = value
                else:
                    data[column.name] = value
        return data
    except Exception as e:
        logger.warning(f"Failed to serialize model {instance.__class__.__name__}: {e}")
        return {"error": f"serialization_failed: {str(e)}"}

def _create_audit_log(action: str, table_name: str, target_id: str, before_data: Dict = None, after_data: Dict = None):
    """Create an audit log entry."""
    if not _audit_context.enabled:
        return
    
    try:
        # Use a separate database session to avoid conflicts
        with SessionLocal() as audit_db:
            disable_audit()  # Prevent recursive audit logging
            
            audit_entry = AuditLog(
                game_id=_audit_context.game_id,
                session_id=_audit_context.session_id,
                actor_kind=_audit_context.actor_kind or "system",
                actor_id=_audit_context.actor_id or "unknown",
                action=_audit_context.operation_type if _audit_context.operation_type else action,
                target_table=table_name,
                target_id=target_id,
                before=before_data,
                after=after_data
            )
            
            audit_db.add(audit_entry)
            audit_db.commit()
            
            enable_audit()
            
            logger.debug(f"Audit logged: {action} on {table_name} (ID: {target_id})")
            
    except Exception as e:
        enable_audit()
        logger.error(f"Failed to create audit log: {e}")

# Event listeners for automatic audit logging
@event.listens_for(Player, 'before_update')
def audit_player_before_update(mapper, connection, target):
    if not _audit_context.enabled:
        return
    
    # Use raw SQL to fetch the current state from database before the update
    result = connection.execute(text("""
        SELECT id, display_name, external_id
        FROM players 
        WHERE id = :player_id
    """), {
        'player_id': str(target.id)
    }).fetchone()
    
    if result:
        target._audit_before = {
            'id': str(result.id),
            'display_name': result.display_name,
            'external_id': result.external_id
        }

@event.listens_for(Player, 'after_update')
def audit_player_after_update(mapper, connection, target):
    if not _audit_context.enabled:
        return
    
    before_data = getattr(target, '_audit_before', None)
    after_data = _serialize_model(target)
    
    _create_audit_log(
        action="UPDATE",
        table_name="players",
        target_id=str(target.id),
        before_data=before_data,
        after_data=after_data
    )

@event.listens_for(Player, 'after_insert')
def audit_player_after_insert(mapper, connection, target):
    if not _audit_context.enabled:
        return
    
    _create_audit_log(
        action="INSERT",
        table_name="players",
        target_id=str(target.id),
        before_data=None,
        after_data=_serialize_model(target)
    )

@event.listens_for(Player, 'before_delete')
def audit_player_before_delete(mapper, connection, target):
    if not _audit_context.enabled:
        return
    
    _create_audit_log(
        action="DELETE",
        table_name="players",
        target_id=str(target.id),
        before_data=_serialize_model(target),
        after_data=None
    )

# SessionPlayerSummary audit listeners
@event.listens_for(SessionPlayerSummary, 'before_update')
def audit_sps_before_update(mapper, connection, target):
    if not _audit_context.enabled:
        return
    
    # Use raw SQL to fetch the current state from database before the update
    result = connection.execute(text("""
        SELECT session_id, player_id, buy_in_sum, cash_out_sum, in_game, net, names
        FROM session_player_summaries 
        WHERE session_id = :session_id AND player_id = :player_id
    """), {
        'session_id': str(target.session_id),
        'player_id': str(target.player_id)
    }).fetchone()
    
    if result:
        # Get game number from session table
        game_number_result = connection.execute(text("""
            SELECT game_number FROM sessions WHERE id = :session_id
        """), {'session_id': str(result.session_id)}).fetchone()
        
        game_number = game_number_result.game_number if game_number_result else None
        
        target._audit_before = {
            'session_id': str(result.session_id),
            'player_id': str(result.player_id),
            'buy_in_sum': result.buy_in_sum,
            'cash_out_sum': result.cash_out_sum,
            'in_game': result.in_game,
            'net': result.net,
            'names': result.names,
            'game_number': game_number
        }

@event.listens_for(SessionPlayerSummary, 'after_update')
def audit_sps_after_update(mapper, connection, target):
    if not _audit_context.enabled:
        return
    
    before_data = getattr(target, '_audit_before', None)
    after_data = _serialize_model(target)
    
    # Add game number to after_data as well
    if after_data:
        game_number_result = connection.execute(text("""
            SELECT game_number FROM sessions WHERE id = :session_id
        """), {'session_id': str(target.session_id)}).fetchone()
        
        game_number = game_number_result.game_number if game_number_result else None
        after_data['game_number'] = game_number
    
    _create_audit_log(
        action="UPDATE",
        table_name="session_player_summaries",
        target_id=f"{target.session_id}:{target.player_id}",
        before_data=before_data,
        after_data=after_data
    )

@event.listens_for(SessionPlayerSummary, 'after_insert')
def audit_sps_after_insert(mapper, connection, target):
    if not _audit_context.enabled:
        return
    
    _create_audit_log(
        action="INSERT",
        table_name="session_player_summaries",
        target_id=f"{target.session_id}:{target.player_id}",
        before_data=None,
        after_data=_serialize_model(target)
    )

@event.listens_for(SessionPlayerSummary, 'before_delete')
def audit_sps_before_delete(mapper, connection, target):
    if not _audit_context.enabled:
        return
    
    before_data = _serialize_model(target)
    
    # Add game number to before_data for delete operations
    if before_data:
        game_number_result = connection.execute(text("""
            SELECT game_number FROM sessions WHERE id = :session_id
        """), {'session_id': str(target.session_id)}).fetchone()
        
        game_number = game_number_result.game_number if game_number_result else None
        before_data['game_number'] = game_number
    
    _create_audit_log(
        action="DELETE",
        table_name="session_player_summaries",
        target_id=f"{target.session_id}:{target.player_id}",
        before_data=before_data,
        after_data=None
    )

# Session audit listeners
@event.listens_for(Session, 'before_update')
def audit_session_before_update(mapper, connection, target):
    if not _audit_context.enabled:
        return
    
    session = SQLSession.object_session(target)
    if session:
        current = session.get(Session, target.id)
        if current:
            target._audit_before = _serialize_model(current)

@event.listens_for(Session, 'after_update')
def audit_session_after_update(mapper, connection, target):
    if not _audit_context.enabled:
        return
    
    before_data = getattr(target, '_audit_before', None)
    after_data = _serialize_model(target)
    
    _create_audit_log(
        action="UPDATE",
        table_name="sessions",
        target_id=str(target.id),
        before_data=before_data,
        after_data=after_data
    )

@event.listens_for(Session, 'after_insert')
def audit_session_after_insert(mapper, connection, target):
    if not _audit_context.enabled:
        return
    
    _create_audit_log(
        action="INSERT",
        table_name="sessions",
        target_id=str(target.id),
        before_data=None,
        after_data=_serialize_model(target)
    )

@event.listens_for(Session, 'before_delete')
def audit_session_before_delete(mapper, connection, target):
    if not _audit_context.enabled:
        return
    
    _create_audit_log(
        action="DELETE",
        table_name="sessions",
        target_id=str(target.id),
        before_data=_serialize_model(target),
        after_data=None
    )

# Game audit listeners
@event.listens_for(Game, 'before_update')
def audit_game_before_update(mapper, connection, target):
    if not _audit_context.enabled:
        return
    
    session = SQLSession.object_session(target)
    if session:
        current = session.get(Game, target.id)
        if current:
            target._audit_before = _serialize_model(current)

@event.listens_for(Game, 'after_update')
def audit_game_after_update(mapper, connection, target):
    if not _audit_context.enabled:
        return
    
    before_data = getattr(target, '_audit_before', None)
    after_data = _serialize_model(target)
    
    _create_audit_log(
        action="UPDATE",
        table_name="games",
        target_id=str(target.id),
        before_data=before_data,
        after_data=after_data
    )

@event.listens_for(Game, 'after_insert')
def audit_game_after_insert(mapper, connection, target):
    if not _audit_context.enabled:
        return
    
    _create_audit_log(
        action="INSERT",
        table_name="games",
        target_id=str(target.id),
        before_data=None,
        after_data=_serialize_model(target)
    )

@event.listens_for(Game, 'before_delete')
def audit_game_before_delete(mapper, connection, target):
    if not _audit_context.enabled:
        return
    
    _create_audit_log(
        action="DELETE",
        table_name="games",
        target_id=str(target.id),
        before_data=_serialize_model(target),
        after_data=None
    )

# PaymentTransaction audit listeners
@event.listens_for(PaymentTransaction, 'before_update')
def audit_payment_before_update(mapper, connection, target):
    if not _audit_context.enabled:
        return
    
    # Use raw SQL to fetch the current state from database before the update
    result = connection.execute(text("""
        SELECT id, game_id, payer_id, recipient_id, amount_cents, payment_method, 
               payment_date, status, notes, reference_id, created_by, created_at
        FROM payment_transactions 
        WHERE id = :payment_id
    """), {
        'payment_id': str(target.id)
    }).fetchone()
    
    if result:
        target._audit_before = {
            'id': str(result.id),
            'game_id': str(result.game_id),
            'payer_id': str(result.payer_id),
            'recipient_id': str(result.recipient_id),
            'amount_cents': result.amount_cents,
            'payment_method': result.payment_method,
            'payment_date': result.payment_date.isoformat() if result.payment_date else None,
            'status': result.status,
            'notes': result.notes,
            'reference_id': result.reference_id,
            'created_by': result.created_by,
            'created_at': result.created_at.isoformat() if result.created_at else None
        }

@event.listens_for(PaymentTransaction, 'after_update')
def audit_payment_after_update(mapper, connection, target):
    if not _audit_context.enabled:
        return
    
    before_data = getattr(target, '_audit_before', None)
    after_data = _serialize_model(target)
    
    _create_audit_log(
        action="UPDATE",
        table_name="payment_transactions",
        target_id=str(target.id),
        before_data=before_data,
        after_data=after_data
    )

@event.listens_for(PaymentTransaction, 'after_insert')
def audit_payment_after_insert(mapper, connection, target):
    if not _audit_context.enabled:
        return
    
    after_data = _serialize_model(target)
    
    # Add player names for better readability
    try:
        payer_result = connection.execute(text("""
            SELECT display_name FROM players WHERE id = :payer_id
        """), {'payer_id': str(target.payer_id)}).fetchone()
        
        recipient_result = connection.execute(text("""
            SELECT display_name FROM players WHERE id = :recipient_id
        """), {'recipient_id': str(target.recipient_id)}).fetchone()
        
        if payer_result and recipient_result:
            after_data['payer_name'] = payer_result.display_name
            after_data['recipient_name'] = recipient_result.display_name
            after_data['amount_dollars'] = float(target.amount_cents) / 100
            
    except Exception as e:
        logger.warning(f"Failed to add player names to payment audit: {e}")
    
    _create_audit_log(
        action="INSERT",
        table_name="payment_transactions",
        target_id=str(target.id),
        before_data=None,
        after_data=after_data
    )

@event.listens_for(PaymentTransaction, 'before_delete')
def audit_payment_before_delete(mapper, connection, target):
    if not _audit_context.enabled:
        return
    
    before_data = _serialize_model(target)
    
    # Add player names for better readability
    try:
        payer_result = connection.execute(text("""
            SELECT display_name FROM players WHERE id = :payer_id
        """), {'payer_id': str(target.payer_id)}).fetchone()
        
        recipient_result = connection.execute(text("""
            SELECT display_name FROM players WHERE id = :recipient_id
        """), {'recipient_id': str(target.recipient_id)}).fetchone()
        
        if payer_result and recipient_result:
            before_data['payer_name'] = payer_result.display_name
            before_data['recipient_name'] = recipient_result.display_name
            before_data['amount_dollars'] = float(target.amount_cents) / 100
            
    except Exception as e:
        logger.warning(f"Failed to add player names to payment audit: {e}")
    
    _create_audit_log(
        action="DELETE",
        table_name="payment_transactions",
        target_id=str(target.id),
        before_data=before_data,
        after_data=None
    )

# PaymentBalance audit listeners
@event.listens_for(PaymentBalance, 'before_update')
def audit_payment_balance_before_update(mapper, connection, target):
    if not _audit_context.enabled:
        return
    
    # Use raw SQL to fetch the current state from database before the update
    result = connection.execute(text("""
        SELECT id, game_id, player_id, total_paid, total_received, 
               poker_net_winnings, payment_balance, last_updated
        FROM payment_balances 
        WHERE id = :balance_id
    """), {
        'balance_id': str(target.id)
    }).fetchone()
    
    if result:
        target._audit_before = {
            'id': str(result.id),
            'game_id': str(result.game_id),
            'player_id': str(result.player_id),
            'total_paid': result.total_paid,
            'total_received': result.total_received,
            'poker_net_winnings': result.poker_net_winnings,
            'payment_balance': result.payment_balance,
            'last_updated': result.last_updated.isoformat() if result.last_updated else None
        }

@event.listens_for(PaymentBalance, 'after_update')
def audit_payment_balance_after_update(mapper, connection, target):
    if not _audit_context.enabled:
        return
    
    before_data = getattr(target, '_audit_before', None)
    after_data = _serialize_model(target)
    
    # Add player name for better readability
    try:
        player_result = connection.execute(text("""
            SELECT display_name FROM players WHERE id = :player_id
        """), {'player_id': str(target.player_id)}).fetchone()
        
        if player_result:
            after_data['player_name'] = player_result.display_name
            # Convert cents to dollars for readability
            after_data['total_paid_dollars'] = float(target.total_paid) / 100
            after_data['total_received_dollars'] = float(target.total_received) / 100
            after_data['poker_net_winnings_dollars'] = float(target.poker_net_winnings) / 100
            after_data['payment_balance_dollars'] = float(target.payment_balance) / 100
            
            # Add the same info to before_data if it exists
            if before_data:
                before_data['player_name'] = player_result.display_name
                before_data['total_paid_dollars'] = float(before_data['total_paid']) / 100
                before_data['total_received_dollars'] = float(before_data['total_received']) / 100
                before_data['poker_net_winnings_dollars'] = float(before_data['poker_net_winnings']) / 100
                before_data['payment_balance_dollars'] = float(before_data['payment_balance']) / 100
            
    except Exception as e:
        logger.warning(f"Failed to add player name to payment balance audit: {e}")
    
    _create_audit_log(
        action="UPDATE",
        table_name="payment_balances",
        target_id=str(target.id),
        before_data=before_data,
        after_data=after_data
    )

@event.listens_for(PaymentBalance, 'after_insert')
def audit_payment_balance_after_insert(mapper, connection, target):
    if not _audit_context.enabled:
        return
    
    after_data = _serialize_model(target)
    
    # Add player name and dollar amounts for better readability
    try:
        player_result = connection.execute(text("""
            SELECT display_name FROM players WHERE id = :player_id
        """), {'player_id': str(target.player_id)}).fetchone()
        
        if player_result:
            after_data['player_name'] = player_result.display_name
            after_data['total_paid_dollars'] = float(target.total_paid) / 100
            after_data['total_received_dollars'] = float(target.total_received) / 100
            after_data['poker_net_winnings_dollars'] = float(target.poker_net_winnings) / 100
            after_data['payment_balance_dollars'] = float(target.payment_balance) / 100
            
    except Exception as e:
        logger.warning(f"Failed to add player name to payment balance audit: {e}")
    
    _create_audit_log(
        action="INSERT",
        table_name="payment_balances",
        target_id=str(target.id),
        before_data=None,
        after_data=after_data
    )

@event.listens_for(PaymentBalance, 'before_delete')
def audit_payment_balance_before_delete(mapper, connection, target):
    if not _audit_context.enabled:
        return
    
    before_data = _serialize_model(target)
    
    # Add player name and dollar amounts for better readability
    try:
        player_result = connection.execute(text("""
            SELECT display_name FROM players WHERE id = :player_id
        """), {'player_id': str(target.player_id)}).fetchone()
        
        if player_result:
            before_data['player_name'] = player_result.display_name
            before_data['total_paid_dollars'] = float(target.total_paid) / 100
            before_data['total_received_dollars'] = float(target.total_received) / 100
            before_data['poker_net_winnings_dollars'] = float(target.poker_net_winnings) / 100
            before_data['payment_balance_dollars'] = float(target.payment_balance) / 100
            
    except Exception as e:
        logger.warning(f"Failed to add player name to payment balance audit: {e}")
    
    _create_audit_log(
        action="DELETE",
        table_name="payment_balances",
        target_id=str(target.id),
        before_data=before_data,
        after_data=None
    )

# GamePlayer audit listeners
@event.listens_for(GamePlayer, 'before_update')
def audit_game_player_before_update(mapper, connection, target):
    if not _audit_context.enabled:
        return
    
    # Use raw SQL to fetch the current state from database before the update
    result = connection.execute(text("""
        SELECT game_id, player_id, joined_at
        FROM game_players 
        WHERE game_id = :game_id AND player_id = :player_id
    """), {
        'game_id': str(target.game_id),
        'player_id': str(target.player_id)
    }).fetchone()
    
    if result:
        target._audit_before = {
            'game_id': str(result.game_id),
            'player_id': str(result.player_id),
            'joined_at': result.joined_at.isoformat() if result.joined_at else None
        }

@event.listens_for(GamePlayer, 'after_update')
def audit_game_player_after_update(mapper, connection, target):
    if not _audit_context.enabled:
        return
    
    before_data = getattr(target, '_audit_before', None)
    after_data = _serialize_model(target)
    
    # Add player and game names for better readability
    try:
        player_result = connection.execute(text("""
            SELECT display_name FROM players WHERE id = :player_id
        """), {'player_id': str(target.player_id)}).fetchone()
        
        game_result = connection.execute(text("""
            SELECT public_code, title FROM games WHERE id = :game_id
        """), {'game_id': str(target.game_id)}).fetchone()
        
        if player_result and game_result:
            after_data['player_name'] = player_result.display_name
            after_data['game_public_code'] = game_result.public_code
            after_data['game_title'] = game_result.title
            
            # Add same info to before_data if it exists
            if before_data:
                before_data['player_name'] = player_result.display_name
                before_data['game_public_code'] = game_result.public_code
                before_data['game_title'] = game_result.title
            
    except Exception as e:
        logger.warning(f"Failed to add names to game player audit: {e}")
    
    _create_audit_log(
        action="UPDATE",
        table_name="game_players",
        target_id=f"{target.game_id}:{target.player_id}",
        before_data=before_data,
        after_data=after_data
    )

@event.listens_for(GamePlayer, 'after_insert')
def audit_game_player_after_insert(mapper, connection, target):
    if not _audit_context.enabled:
        return
    
    after_data = _serialize_model(target)
    
    # Add player and game names for better readability
    try:
        player_result = connection.execute(text("""
            SELECT display_name FROM players WHERE id = :player_id
        """), {'player_id': str(target.player_id)}).fetchone()
        
        game_result = connection.execute(text("""
            SELECT public_code, title FROM games WHERE id = :game_id
        """), {'game_id': str(target.game_id)}).fetchone()
        
        if player_result and game_result:
            after_data['player_name'] = player_result.display_name
            after_data['game_public_code'] = game_result.public_code
            after_data['game_title'] = game_result.title
            
    except Exception as e:
        logger.warning(f"Failed to add names to game player audit: {e}")
    
    _create_audit_log(
        action="INSERT",
        table_name="game_players",
        target_id=f"{target.game_id}:{target.player_id}",
        before_data=None,
        after_data=after_data
    )

@event.listens_for(GamePlayer, 'before_delete')
def audit_game_player_before_delete(mapper, connection, target):
    if not _audit_context.enabled:
        return
    
    before_data = _serialize_model(target)
    
    # Add player and game names for better readability
    try:
        player_result = connection.execute(text("""
            SELECT display_name FROM players WHERE id = :player_id
        """), {'player_id': str(target.player_id)}).fetchone()
        
        game_result = connection.execute(text("""
            SELECT public_code, title FROM games WHERE id = :game_id
        """), {'game_id': str(target.game_id)}).fetchone()
        
        if player_result and game_result:
            before_data['player_name'] = player_result.display_name
            before_data['game_public_code'] = game_result.public_code
            before_data['game_title'] = game_result.title
            
    except Exception as e:
        logger.warning(f"Failed to add names to game player audit: {e}")
    
    _create_audit_log(
        action="DELETE",
        table_name="game_players",
        target_id=f"{target.game_id}:{target.player_id}",
        before_data=before_data,
        after_data=None
    )

def setup_request_audit_context():
    """Flask request hook to set up audit context from request headers."""
    try:
        if hasattr(request, 'headers'):
            admin_code = request.headers.get('X-Admin-Code')
            if admin_code:
                _audit_context.set_context(
                    actor_kind="admin_code",
                    actor_id=admin_code[:8] + "…",
                    operation_type=request.endpoint or request.method
                )
            else:
                _audit_context.set_context(
                    actor_kind="api",
                    actor_id=request.remote_addr or "unknown",
                    operation_type=request.endpoint or request.method
                )
    except Exception as e:
        logger.warning(f"Failed to set up request audit context: {e}")

def teardown_request_audit_context(exception=None):
    """Flask request hook to clean up audit context."""
    _audit_context.clear()

logger.info("Audit middleware initialized with SQLAlchemy event listeners for Player, SessionPlayerSummary, Session, Game, PaymentTransaction, PaymentBalance, and GamePlayer")