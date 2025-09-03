from sqlalchemy import text, func, or_, and_
from sqlalchemy.orm import joinedload
from db.database import SessionLocal
from db.models import Player, SessionPlayerSummary, Session, Game, GamePlayer, AuditLog
from typing import List, Dict, Any, Optional
import logging
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

def find_potential_duplicates(public_code: str, verified_name: str, exclude_player_id: str = None) -> Dict[str, Any]:
    """
    Find potential duplicate players for a given verified name.
    Uses fuzzy matching on display names and session names.
    """
    with SessionLocal() as db:
        try:
            # Normalize the verified name for comparison
            verified_name_lower = verified_name.lower().strip()
            
            # Get all players in this game with their session info
            query = db.query(Player).join(
                GamePlayer, Player.id == GamePlayer.player_id
            ).join(
                Game, GamePlayer.game_id == Game.id
            ).filter(
                Game.public_code == public_code
            )
            
            # Exclude the player being verified
            if exclude_player_id:
                query = query.filter(Player.id != exclude_player_id)
            
            players = query.options(
                joinedload(Player.summaries).joinedload(SessionPlayerSummary.session)
            ).all()
            
            potential_matches = []
            
            for player in players:
                match_score = 0
                match_reasons = []
                
                # Check display name similarity
                if player.display_name:
                    display_name_lower = player.display_name.lower().strip()
                    
                    # Exact match (high score)
                    if display_name_lower == verified_name_lower:
                        match_score += 100
                        match_reasons.append("Exact display name match")
                    # Contains match
                    elif verified_name_lower in display_name_lower or display_name_lower in verified_name_lower:
                        match_score += 60
                        match_reasons.append("Display name contains match")
                    # Similar length and some common characters
                    elif _calculate_similarity(display_name_lower, verified_name_lower) > 0.6:
                        match_score += 40
                        match_reasons.append("Similar display name")
                
                # Check session names for matches
                session_names = set()
                session_count = 0
                
                for summary in player.summaries:
                    session_count += 1
                    for name in summary.names:
                        session_names.add(name.lower().strip())
                
                # Check if verified name appears in any session names
                for session_name in session_names:
                    if session_name == verified_name_lower:
                        match_score += 80
                        match_reasons.append("Exact session name match")
                        break
                    elif verified_name_lower in session_name or session_name in verified_name_lower:
                        match_score += 50
                        match_reasons.append("Session name contains match")
                        break
                    elif _calculate_similarity(session_name, verified_name_lower) > 0.7:
                        match_score += 30
                        match_reasons.append("Similar session name")
                        break
                
                # Only include matches with score above threshold
                if match_score >= 30:
                    potential_matches.append({
                        'player_id': str(player.id),
                        'display_name': player.display_name,
                        'external_id': player.external_id,
                        'session_count': session_count,
                        'session_names': list(session_names),
                        'is_verified': bool(player.external_id),
                        'match_score': match_score,
                        'match_reasons': match_reasons
                    })
            
            # Sort by match score (highest first)
            potential_matches.sort(key=lambda x: x['match_score'], reverse=True)
            
            return {
                'verified_name': verified_name,
                'potential_matches': potential_matches,
                'match_count': len(potential_matches)
            }

        except Exception as e:
            logger.error(f"Error finding potential duplicates: {e}")
            raise

def _calculate_similarity(str1: str, str2: str) -> float:
    """
    Simple string similarity calculation using character overlap.
    Returns a value between 0 and 1.
    """
    if not str1 or not str2:
        return 0.0
    
    # Use set intersection for simple similarity
    set1 = set(str1.lower())
    set2 = set(str2.lower())
    
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    
    if union == 0:
        return 0.0
    
    return intersection / union

def merge_players(target_player_id: str, source_player_ids: List[str], verified_name: str, external_id: str = None, admin_code: str = None, game_id: str = None) -> Dict[str, Any]:
    """
    Merge multiple players into a single target player.
    All session summaries from source players are moved to target player.
    Source players are deleted after merge.
    """
    with SessionLocal() as db:
        try:
            # Get target player
            target_player = db.query(Player).filter(Player.id == target_player_id).first()
            if not target_player:
                raise ValueError(f"Target player not found: {target_player_id}")
            
            # Get source players
            source_players = db.query(Player).filter(Player.id.in_(source_player_ids)).all()
            found_ids = [str(p.id) for p in source_players]
            missing_ids = [pid for pid in source_player_ids if pid not in found_ids]
            if missing_ids:
                raise ValueError(f"Source players not found: {missing_ids}")
            
            merged_sessions = 0
            merged_names = set()
            
            # Create a unique operation ID for this merge
            operation_id = str(uuid.uuid4())
            
            # Capture full state before merge for audit
            audit_before = {
                'operation_id': operation_id,
                'operation_type': 'PLAYER_MERGE',
                'target_player': {
                    'id': str(target_player.id),
                    'display_name': target_player.display_name,
                    'external_id': target_player.external_id,
                    'sessions': []
                },
                'source_players': [],
                'requested_verified_name': verified_name,
                'requested_external_id': external_id
            }
            
            # Capture target player's current sessions
            target_summaries = db.query(SessionPlayerSummary).filter(
                SessionPlayerSummary.player_id == target_player.id
            ).options(joinedload(SessionPlayerSummary.session)).all()
            
            for summary in target_summaries:
                audit_before['target_player']['sessions'].append({
                    'session_id': str(summary.session_id),
                    'session_external_id': summary.session.external_id,
                    'buy_in_sum': summary.buy_in_sum,
                    'cash_out_sum': summary.cash_out_sum,
                    'in_game': summary.in_game,
                    'net': summary.net,
                    'names': summary.names
                })
            
            # Capture each source player's full state
            for source_player in source_players:
                source_summaries = db.query(SessionPlayerSummary).filter(
                    SessionPlayerSummary.player_id == source_player.id
                ).options(joinedload(SessionPlayerSummary.session)).all()
                
                source_data = {
                    'id': str(source_player.id),
                    'display_name': source_player.display_name,
                    'external_id': source_player.external_id,
                    'sessions': []
                }
                
                for summary in source_summaries:
                    source_data['sessions'].append({
                        'session_id': str(summary.session_id),
                        'session_external_id': summary.session.external_id,
                        'buy_in_sum': summary.buy_in_sum,
                        'cash_out_sum': summary.cash_out_sum,
                        'in_game': summary.in_game,
                        'net': summary.net,
                        'names': summary.names
                    })
                
                audit_before['source_players'].append(source_data)
            
            # First, check if we need to inherit external_id from source players
            target_should_inherit_external_id = None
            logger.info(f"MERGE: Target player {target_player.id} ({target_player.display_name}) external_id: {target_player.external_id}")
            logger.info(f"MERGE: Source players: {[(p.id, p.display_name, p.external_id) for p in source_players]}")
            logger.info(f"MERGE: Requested external_id: {external_id}")
            
            if external_id:
                external_id_stripped = external_id.strip()
                # Find which source player (if any) has the desired external_id
                for source_player in source_players:
                    if source_player.external_id == external_id_stripped:
                        target_should_inherit_external_id = external_id_stripped
                        logger.info(f"MERGE: Will inherit external_id {external_id_stripped} from source player {source_player.id}")
                        break
            elif not target_player.external_id:
                # Target has no external_id, inherit from first source that has one
                for source_player in source_players:
                    if source_player.external_id:
                        target_should_inherit_external_id = source_player.external_id
                        logger.info(f"MERGE: Will inherit external_id {source_player.external_id} from source player {source_player.id}")
                        break
            
            # Move all session summaries from source players to target player
            for source_player in source_players:
                summaries = db.query(SessionPlayerSummary).filter(
                    SessionPlayerSummary.player_id == source_player.id
                ).all()
                
                for summary in summaries:
                    # Check if target player already has a summary for this session
                    existing_summary = db.query(SessionPlayerSummary).filter(
                        SessionPlayerSummary.session_id == summary.session_id,
                        SessionPlayerSummary.player_id == target_player.id
                    ).first()
                    
                    if existing_summary:
                        # Merge the data (sum the values, combine names)
                        existing_summary.buy_in_sum += summary.buy_in_sum
                        existing_summary.cash_out_sum += summary.cash_out_sum
                        existing_summary.in_game += summary.in_game
                        existing_summary.net += summary.net
                        
                        # Combine names
                        combined_names = list(set(existing_summary.names + summary.names))
                        existing_summary.names = combined_names
                        merged_names.update(combined_names)
                        
                        # Delete the duplicate summary manually (don't rely on cascade)
                        db.delete(summary)
                        logger.info(f"MERGE: Merged duplicate session {summary.session_id} for source player {source_player.id}")
                    else:
                        # Move summary to target player BEFORE deleting source player
                        logger.info(f"MERGE: Moving session {summary.session_id} from source player {source_player.id} to target player {target_player.id}")
                        summary.player_id = target_player.id
                        merged_names.update(summary.names)
                    
                    merged_sessions += 1
                
                # Flush the session transfers before deleting the source player
                logger.info(f"MERGE: Flushing session transfers for source player {source_player.id}")
                db.flush()
                
                # Update GamePlayer links
                game_links = db.query(GamePlayer).filter(GamePlayer.player_id == source_player.id).all()
                for link in game_links:
                    # Check if target player already linked to this game
                    existing_link = db.query(GamePlayer).filter(
                        GamePlayer.game_id == link.game_id,
                        GamePlayer.player_id == target_player.id
                    ).first()
                    
                    if existing_link:
                        # Use earlier join date
                        if link.joined_at < existing_link.joined_at:
                            existing_link.joined_at = link.joined_at
                        db.delete(link)
                    else:
                        # Move link to target player
                        link.player_id = target_player.id
                
                # Delete source player
                logger.info(f"MERGE: Deleting source player {source_player.id} ({source_player.display_name}) with external_id: {source_player.external_id}")
                db.delete(source_player)
            
            # Flush the deletions to free up external_ids immediately
            logger.info("MERGE: Flushing source player deletions")
            db.flush()
            
            # Update target player with verified info
            old_name = target_player.display_name
            old_external_id = target_player.external_id
            
            target_player.display_name = verified_name.strip()
            
            # Now assign external_id after source players are deleted
            if target_should_inherit_external_id:
                # Double-check that the external_id is now free (sources should be deleted)
                existing_player = db.query(Player).filter(
                    Player.external_id == target_should_inherit_external_id,
                    Player.id != target_player.id
                ).first()
                
                if existing_player:
                    logger.error(f"MERGE ERROR: External ID {target_should_inherit_external_id} still exists on player {existing_player.id} ({existing_player.display_name}) after source deletion")
                    raise ValueError(f"External ID '{target_should_inherit_external_id}' is still assigned to another player: {existing_player.display_name}")
                
                logger.info(f"Assigning external_id {target_should_inherit_external_id} to target player {target_player.id}")
                target_player.external_id = target_should_inherit_external_id
            elif external_id and not target_should_inherit_external_id:
                # New external_id that doesn't come from source players
                external_id_stripped = external_id.strip()
                if target_player.external_id != external_id_stripped:
                    # Check if external_id exists elsewhere in database (excluding already deleted sources)
                    existing_player = db.query(Player).filter(
                        Player.external_id == external_id_stripped,
                        Player.id != target_player.id
                    ).first()
                    
                    if existing_player:
                        raise ValueError(f"External ID '{external_id_stripped}' is already assigned to another player: {existing_player.display_name}")
                    
                    target_player.external_id = external_id_stripped
            
            # Capture final state after merge for audit
            final_summaries = db.query(SessionPlayerSummary).filter(
                SessionPlayerSummary.player_id == target_player.id
            ).options(joinedload(SessionPlayerSummary.session)).all()
            
            audit_after = {
                'operation_id': operation_id,
                'target_player': {
                    'id': str(target_player.id),
                    'display_name': target_player.display_name,
                    'external_id': target_player.external_id,
                    'sessions': []
                },
                'merged_player_count': len(source_players),
                'merged_sessions_total': len(final_summaries)
            }
            
            for summary in final_summaries:
                audit_after['target_player']['sessions'].append({
                    'session_id': str(summary.session_id),
                    'session_external_id': summary.session.external_id,
                    'buy_in_sum': summary.buy_in_sum,
                    'cash_out_sum': summary.cash_out_sum,
                    'in_game': summary.in_game,
                    'net': summary.net,
                    'names': summary.names
                })
            
            # Create audit log entry
            audit_entry = AuditLog(
                game_id=game_id,
                session_id=None,  # This is a player-level operation
                actor_kind="admin_code",
                actor_id=admin_code[:8] + "…" if admin_code else "unknown",
                action="PLAYER_MERGE",
                target_table="players",
                target_id=operation_id,  # Use operation_id as the target
                before=audit_before,
                after=audit_after
            )
            db.add(audit_entry)
            
            db.commit()
            
            return {
                'message': 'Players merged successfully',
                'operation_id': operation_id,
                'target_player_id': target_player_id,
                'merged_player_count': len(source_players),
                'merged_sessions': merged_sessions,
                'old_name': old_name,
                'old_external_id': old_external_id,
                'verified_name': verified_name.strip(),
                'external_id': external_id.strip() if external_id else None,
                'all_names_used': list(merged_names)
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Error merging players: {e}")
            raise