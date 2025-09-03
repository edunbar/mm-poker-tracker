from sqlalchemy import text, desc, and_
from sqlalchemy.orm import joinedload
from db.database import SessionLocal
from db.models import AuditLog, Player, SessionPlayerSummary, Session, Game, GamePlayer
from typing import List, Dict, Any, Optional
import logging
import uuid

logger = logging.getLogger(__name__)

def _get_operation_description(log: AuditLog) -> str:
    """Generate a human-readable description of the audit operation."""
    try:
        if log.action == 'PLAYER_MERGE':
            if log.after and 'merged_player_count' in log.after:
                count = log.after['merged_player_count']
                target_name = log.after.get('target_player', {}).get('display_name', 'Unknown')
                return f"Merged {count} players into '{target_name}'"
            return "Player merge operation"
        
        elif log.action == 'PLAYER_MERGE_UNDO':
            return "Undid player merge operation"
        
        elif log.action == 'IMPORT_LEDGER_SESSION':
            if log.after and 'players_count' in log.after:
                count = log.after['players_count']
                return f"Imported session with {count} players"
            return "Session import"
        
        elif log.action.endswith('_UPDATE'):
            table = log.target_table.replace('_', ' ').title()
            if log.action.startswith('PLAYER_VERIFY'):
                return f"Verified player"
            return f"Updated {table}"
        
        elif log.action.endswith('_INSERT'):
            table = log.target_table.replace('_', ' ').title()
            return f"Created {table}"
        
        elif log.action.endswith('_DELETE'):
            table = log.target_table.replace('_', ' ').title()
            return f"Deleted {table}"
        
        else:
            # Generic description
            action_name = log.action.replace('_', ' ').title()
            table_name = log.target_table.replace('_', ' ').title()
            return f"{action_name} on {table_name}"
            
    except Exception as e:
        logger.warning(f"Failed to generate description for audit log {log.id}: {e}")
        return log.action

def get_all_audit_logs(public_code: str, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
    """
    Get all audit logs for a specific game.
    """
    with SessionLocal() as db:
        try:
            game = db.query(Game).filter(Game.public_code == public_code).first()
            if not game:
                raise ValueError(f"Game not found: {public_code}")
            
            return get_audit_logs(
                game_id=str(game.id),
                limit=limit,
                offset=offset
            )

        except Exception as e:
            logger.error(f"Error fetching all audit logs: {e}")
            raise

def get_audit_logs(game_id: str = None, action_filter: str = None, table_filter: str = None, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
    """
    Get audit logs with optional filtering.
    """
    with SessionLocal() as db:
        try:
            query = db.query(AuditLog)
            
            if game_id:
                query = query.filter(AuditLog.game_id == game_id)
            
            if action_filter:
                query = query.filter(AuditLog.action == action_filter)
            
            if table_filter:
                query = query.filter(AuditLog.target_table == table_filter)
            
            # Order by most recent first
            query = query.order_by(desc(AuditLog.at))
            
            total_count = query.count()
            
            # Apply pagination
            logs = query.offset(offset).limit(limit).all()
            
            audit_entries = []
            for log in logs:
                entry = {
                    'id': str(log.id),
                    'game_id': str(log.game_id) if log.game_id else None,
                    'session_id': str(log.session_id) if log.session_id else None,
                    'actor_kind': log.actor_kind,
                    'actor_id': log.actor_id,
                    'action': log.action,
                    'target_table': log.target_table,
                    'target_id': log.target_id,
                    'timestamp': log.at.isoformat() if log.at else None,
                    'before': log.before,
                    'after': log.after,
                    'can_undo': log.action == 'PLAYER_MERGE' and log.before and log.after,
                    'description': _get_operation_description(log)
                }
                audit_entries.append(entry)
            
            return {
                'audit_logs': audit_entries,
                'total_count': total_count,
                'page_size': limit,
                'offset': offset
            }

        except Exception as e:
            logger.error(f"Error fetching audit logs: {e}")
            raise

def get_merge_audit_logs(public_code: str, limit: int = 20) -> Dict[str, Any]:
    """
    Get merge-specific audit logs for a game.
    """
    with SessionLocal() as db:
        try:
            game = db.query(Game).filter(Game.public_code == public_code).first()
            if not game:
                raise ValueError(f"Game not found: {public_code}")
            
            return get_audit_logs(
                game_id=str(game.id),
                action_filter='PLAYER_MERGE',
                limit=limit
            )

        except Exception as e:
            logger.error(f"Error fetching merge audit logs: {e}")
            raise

def undo_player_merge(operation_id: str, admin_code: str) -> Dict[str, Any]:
    """
    Undo a player merge operation by restoring the original player states.
    """
    with SessionLocal() as db:
        try:
            # Find the audit log for this operation
            audit_log = db.query(AuditLog).filter(
                AuditLog.target_id == operation_id,
                AuditLog.action == 'PLAYER_MERGE'
            ).first()
            
            if not audit_log:
                raise ValueError(f"Merge operation not found: {operation_id}")
            
            if not audit_log.before or not audit_log.after:
                raise ValueError("Insufficient audit data to undo this operation")
            
            before_state = audit_log.before
            after_state = audit_log.after
            
            # Validate that we can undo this operation
            target_player_id = before_state['target_player']['id']
            target_player = db.query(Player).filter(Player.id == target_player_id).first()
            
            if not target_player:
                raise ValueError(f"Target player no longer exists: {target_player_id}")
            
            logger.info(f"UNDO: Starting undo of merge operation {operation_id}")
            
            # Step 1: Recreate all source players
            restored_players = []
            for source_data in before_state['source_players']:
                logger.info(f"UNDO: Recreating source player {source_data['id']} ({source_data['display_name']})")
                
                restored_player = Player(
                    id=source_data['id'],
                    display_name=source_data['display_name'],
                    external_id=source_data['external_id']
                )
                db.add(restored_player)
                restored_players.append(restored_player)
            
            # Flush to create the players
            db.flush()
            
            # Step 2: Restore all session summaries to their original players
            current_summaries = db.query(SessionPlayerSummary).filter(
                SessionPlayerSummary.player_id == target_player_id
            ).all()
            
            # Create a mapping of sessions to their original owners
            session_to_original_player = {}
            
            # Map target player's original sessions
            for session_data in before_state['target_player']['sessions']:
                session_to_original_player[session_data['session_id']] = {
                    'player_id': target_player_id,
                    'data': session_data
                }
            
            # Map source players' original sessions
            for source_data in before_state['source_players']:
                for session_data in source_data['sessions']:
                    session_to_original_player[session_data['session_id']] = {
                        'player_id': source_data['id'],
                        'data': session_data
                    }
            
            # Delete all current session summaries for target player
            for summary in current_summaries:
                db.delete(summary)
            
            db.flush()
            
            # Recreate all session summaries with original data
            restored_sessions = 0
            for session_id, owner_info in session_to_original_player.items():
                session_data = owner_info['data']
                
                logger.info(f"UNDO: Restoring session {session_id} to player {owner_info['player_id']}")
                
                restored_summary = SessionPlayerSummary(
                    session_id=session_id,
                    player_id=owner_info['player_id'],
                    buy_in_sum=session_data['buy_in_sum'],
                    cash_out_sum=session_data['cash_out_sum'],
                    in_game=session_data['in_game'],
                    net=session_data['net'],
                    names=session_data['names']
                )
                db.add(restored_summary)
                restored_sessions += 1
            
            # Step 3: Restore target player's original state
            logger.info(f"UNDO: Restoring target player {target_player_id} to original state")
            target_player.display_name = before_state['target_player']['display_name']
            target_player.external_id = before_state['target_player']['external_id']
            
            # Step 4: Recreate GamePlayer links for restored players
            if audit_log.game_id:
                for restored_player in restored_players:
                    # Check if link already exists
                    existing_link = db.query(GamePlayer).filter(
                        GamePlayer.game_id == audit_log.game_id,
                        GamePlayer.player_id == restored_player.id
                    ).first()
                    
                    if not existing_link:
                        game_link = GamePlayer(
                            game_id=audit_log.game_id,
                            player_id=restored_player.id
                        )
                        db.add(game_link)
            
            # Step 5: Create undo audit log
            undo_operation_id = str(uuid.uuid4())
            undo_audit = AuditLog(
                game_id=audit_log.game_id,
                session_id=None,
                actor_kind="admin_code",
                actor_id=admin_code[:8] + "…" if admin_code else "unknown",
                action="PLAYER_MERGE_UNDO",
                target_table="players",
                target_id=undo_operation_id,
                before=after_state,  # What it was after merge
                after=before_state   # What we restored it to
            )
            db.add(undo_audit)
            
            db.commit()
            
            logger.info(f"UNDO: Successfully undid merge operation {operation_id}")
            
            return {
                'message': 'Merge operation successfully undone',
                'original_operation_id': operation_id,
                'undo_operation_id': undo_operation_id,
                'restored_players': len(restored_players),
                'restored_sessions': restored_sessions,
                'target_player_restored': True
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Error undoing merge operation {operation_id}: {e}")
            raise

def get_operation_details(operation_id: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific operation for preview before undo.
    operation_id can be either an audit log ID or a target_id for merge operations.
    """
    with SessionLocal() as db:
        try:
            # First try to find by audit log ID
            audit_log = db.query(AuditLog).filter(
                AuditLog.id == operation_id
            ).first()
            
            # If not found, try by target_id (for merge operations)
            if not audit_log:
                audit_log = db.query(AuditLog).filter(
                    AuditLog.target_id == operation_id
                ).first()
            
            if not audit_log:
                raise ValueError(f"Operation not found: {operation_id}")
            
            return {
                'operation_id': operation_id,
                'action': audit_log.action,
                'timestamp': audit_log.at.isoformat() if audit_log.at else None,
                'actor': audit_log.actor_id,
                'before_state': audit_log.before,
                'after_state': audit_log.after,
                'can_undo': audit_log.action == 'PLAYER_MERGE' and audit_log.before and audit_log.after
            }

        except Exception as e:
            logger.error(f"Error getting operation details: {e}")
            raise