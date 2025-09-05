from sqlalchemy import text, func, distinct, and_
from sqlalchemy.orm import joinedload
from db.database import SessionLocal
from db.models import Player, SessionPlayerSummary, Session, Game
from services.audit_middleware import audit_context
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

def get_unverified_players(public_code: str) -> Dict[str, Any]:
    """
    Get all players from session summaries who don't have a verified name (display_name).
    These are players identified only by their names array from sessions.
    """
    with SessionLocal() as db:
        try:
            # Get all unique name combinations from session summaries for this game
            summaries = db.query(SessionPlayerSummary).join(
                Session, SessionPlayerSummary.session_id == Session.id
            ).join(
                Game, Session.game_id == Game.id
            ).join(
                Player, SessionPlayerSummary.player_id == Player.id
            ).filter(
                Game.public_code == public_code
            ).options(
                joinedload(SessionPlayerSummary.player)
            ).all()

            # Group by player and collect their info
            player_data = {}
            for summary in summaries:
                player_id = str(summary.player_id)
                player = summary.player
                
                if player_id not in player_data:
                    # Player is "unverified" if is_verified is False
                    is_unverified = not player.is_verified
                    
                    player_data[player_id] = {
                        'player_id': player_id,
                        'display_name': player.display_name or 'Unknown',
                        'external_id': player.external_id,
                        'is_unverified': is_unverified,
                        'session_count': 0,
                        'all_names': set()
                    }
                
                player_data[player_id]['session_count'] += 1
                player_data[player_id]['all_names'].update(summary.names)

            # Separate unverified and verified players
            unverified = []
            verified = []
            
            for player_info in player_data.values():
                player_info['all_names'] = list(player_info['all_names'])  # Convert set to list
                
                if player_info['is_unverified']:
                    unverified.append(player_info)
                else:
                    verified.append(player_info)

            return {
                'unverified_players': sorted(unverified, key=lambda x: x['session_count'], reverse=True),
                'verified_players': sorted(verified, key=lambda x: x['display_name']),
                'unverified_count': len(unverified),
                'verified_count': len(verified)
            }

        except Exception as e:
            logger.error(f"Error fetching player verification data: {e}")
            raise

def verify_player(player_id: str, verified_name: str, external_id: str = None) -> Dict[str, Any]:
    """
    Verify a player by setting their display_name, external_id, and is_verified flag.
    """
    with SessionLocal() as db:
        with audit_context(operation_type="PLAYER_VERIFY"):
            try:
                player = db.query(Player).filter(Player.id == player_id).first()
                
                if not player:
                    raise ValueError(f"Player not found with id: {player_id}")
                
                old_name = player.display_name
                old_external_id = player.external_id
                old_is_verified = player.is_verified
                
                player.display_name = verified_name.strip()
                player.is_verified = True  # Mark as verified by admin
                
                if external_id:
                    external_id_stripped = external_id.strip()
                    # Check if this external_id is already assigned to another player
                    if player.external_id != external_id_stripped:
                        existing_player = db.query(Player).filter(
                            Player.external_id == external_id_stripped,
                            Player.id != player.id
                        ).first()
                        
                        if existing_player:
                            raise ValueError(f"External ID '{external_id_stripped}' is already assigned to another player: {existing_player.display_name}")
                        
                        player.external_id = external_id_stripped
                
                db.commit()
                
                return {
                    'message': 'Player verified successfully',
                    'player_id': player_id,
                    'old_name': old_name,
                    'old_external_id': old_external_id,
                    'old_is_verified': old_is_verified,
                    'verified_name': verified_name.strip(),
                    'external_id': external_id.strip() if external_id else None,
                    'is_verified': True
                }

            except Exception as e:
                db.rollback()
                logger.error(f"Error verifying player: {e}")
                raise

def update_verified_player(player_id: str, verified_name: str, external_id: str = None) -> Dict[str, Any]:
    """
    Update an already verified player's name and external_id. Maintains verified status.
    """
    with SessionLocal() as db:
        try:
            player = db.query(Player).filter(Player.id == player_id).first()
            
            if not player:
                raise ValueError(f"Player not found with id: {player_id}")
            
            old_name = player.display_name
            old_external_id = player.external_id
            
            player.display_name = verified_name.strip()
            if external_id:
                external_id_stripped = external_id.strip()
                # Check if this external_id is already assigned to another player
                if player.external_id != external_id_stripped:
                    existing_player = db.query(Player).filter(
                        Player.external_id == external_id_stripped,
                        Player.id != player.id
                    ).first()
                    
                    if existing_player:
                        raise ValueError(f"External ID '{external_id_stripped}' is already assigned to another player: {existing_player.display_name}")
                    
                    player.external_id = external_id_stripped
            
            db.commit()
            
            return {
                'message': 'Player updated successfully',
                'player_id': player_id,
                'old_name': old_name,
                'old_external_id': old_external_id,
                'verified_name': verified_name.strip(),
                'external_id': external_id.strip() if external_id else None
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Error updating player: {e}")
            raise

def get_player_details(player_id: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific player.
    """
    with SessionLocal() as db:
        try:
            player = db.query(Player).filter(Player.id == player_id).first()
            
            if not player:
                raise ValueError(f"Player not found with id: {player_id}")
            
            # Get all session summaries for this player
            summaries = db.query(SessionPlayerSummary).filter(
                SessionPlayerSummary.player_id == player_id
            ).options(joinedload(SessionPlayerSummary.session)).all()
            
            # Collect all names used
            all_names = set()
            for summary in summaries:
                all_names.update(summary.names)
            
            return {
                'player_id': str(player.id),
                'display_name': player.display_name,
                'external_id': player.external_id,
                'session_count': len(summaries),
                'all_names': list(all_names),
                'created_at': player.created_at.isoformat() if player.created_at else None
            }

        except Exception as e:
            logger.error(f"Error fetching player details: {e}")
            raise

def get_player_verification_debug(public_code: str) -> Dict[str, Any]:
    """
    Get comprehensive debugging information about player verification issues.
    Identifies duplicate names, external ID conflicts, and other issues.
    """
    with SessionLocal() as db:
        try:
            # Get all players for this game
            players_query = db.query(Player).join(
                SessionPlayerSummary, Player.id == SessionPlayerSummary.player_id
            ).join(
                Session, SessionPlayerSummary.session_id == Session.id
            ).join(
                Game, Session.game_id == Game.id
            ).filter(
                Game.public_code == public_code
            ).options(
                joinedload(Player.summaries)
            ).distinct()

            players = players_query.all()

            # Build comprehensive player data
            player_data = {}
            for player in players:
                player_id = str(player.id)
                session_count = len(player.summaries)
                all_names = set()
                
                for summary in player.summaries:
                    all_names.update(summary.names)

                player_data[player_id] = {
                    'player_id': player_id,
                    'display_name': player.display_name,
                    'external_id': player.external_id,
                    'session_count': session_count,
                    'all_names': list(all_names),
                    'created_at': player.created_at.isoformat() if player.created_at else None,
                    'is_verified': player.is_verified
                }

            # Find duplicate display names
            name_to_players = {}
            for player_info in player_data.values():
                name = player_info['display_name'].lower()
                if name not in name_to_players:
                    name_to_players[name] = []
                name_to_players[name].append(player_info)

            duplicate_display_names = []
            for name, players_list in name_to_players.items():
                if len(players_list) > 1:
                    duplicate_display_names.append({
                        'display_name': players_list[0]['display_name'],  # Use original case
                        'players': players_list
                    })

            # Find external ID conflicts
            external_id_to_players = {}
            for player_info in player_data.values():
                if player_info['external_id']:
                    ext_id = player_info['external_id']
                    if ext_id not in external_id_to_players:
                        external_id_to_players[ext_id] = []
                    external_id_to_players[ext_id].append(player_info)

            external_id_conflicts = []
            for ext_id, players_list in external_id_to_players.items():
                if len(players_list) > 1:
                    external_id_conflicts.append({
                        'external_id': ext_id,
                        'players': players_list
                    })

            # Separate verified and unverified players
            unverified_players = [p for p in player_data.values() if not p['is_verified']]
            verified_players = [p for p in player_data.values() if p['is_verified']]

            # Sort by session count (most active first) for unverified
            unverified_players.sort(key=lambda x: x['session_count'], reverse=True)
            verified_players.sort(key=lambda x: x['display_name'])

            return {
                'total_players': len(player_data),
                'verified_count': len(verified_players),
                'unverified_count': len(unverified_players),
                'unverified_players': unverified_players,
                'verified_players': verified_players,
                'duplicate_display_names': duplicate_display_names,
                'external_id_conflicts': external_id_conflicts,
                'debug_info': {
                    'duplicate_names_count': len(duplicate_display_names),
                    'external_id_conflicts_count': len(external_id_conflicts)
                }
            }

        except Exception as e:
            logger.error(f"Error generating player verification debug data: {e}")
            raise