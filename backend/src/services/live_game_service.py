# services/live_game_service.py
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from decimal import Decimal

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from db.database import SessionLocal
from db.models import (
    Game, Player, GamePlayer,
    Session as SessionModel,
    SessionPlayerSummary,
)

log = logging.getLogger(__name__)


def convert_dollars_to_chips(dollars: float) -> int:
    """Convert dollar amounts to chip integers (cents)."""
    if dollars is None:
        return 0
    return int(round(dollars * 100))


def validate_live_game_data(players_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Validate and normalize live game player data.
    
    Expected input format:
    [
        {
            "name": "Alice",
            "buy_in": 100.00,  # dollars
            "cash_out": 150.00,  # dollars  
            "in_game": 0.00  # optional, defaults to 0
        },
        ...
    ]
    
    Returns normalized data with chips in cents.
    """
    validated_players = []
    
    for i, player in enumerate(players_data):
        if not isinstance(player, dict):
            raise ValueError(f"Player {i+1}: Expected player data to be an object")
        
        name = player.get("name", "").strip()
        if not name:
            raise ValueError(f"Player {i+1}: Name is required")
        
        try:
            buy_in = float(player.get("buy_in", 0))
            cash_out = float(player.get("cash_out", 0)) 
            in_game = float(player.get("in_game", 0))
        except (ValueError, TypeError):
            raise ValueError(f"Player {name}: Buy-in, cash-out, and in-game must be valid numbers")
        
        if buy_in < 0 or cash_out < 0 or in_game < 0:
            raise ValueError(f"Player {name}: All amounts must be non-negative")
        
        # Convert to chips (cents)
        buy_in_chips = convert_dollars_to_chips(buy_in)
        cash_out_chips = convert_dollars_to_chips(cash_out)
        in_game_chips = convert_dollars_to_chips(in_game)
        net_chips = cash_out_chips + in_game_chips - buy_in_chips
        
        validated_players.append({
            "name": name,
            "buyInSum": buy_in_chips,
            "buyOutSum": cash_out_chips,
            "inGame": in_game_chips,
            "net": net_chips,
            "original_buy_in": buy_in,
            "original_cash_out": cash_out,
            "original_in_game": in_game
        })
    
    return validated_players


def create_live_game_session_data(
    session_name: str,
    players_data: List[Dict[str, Any]],
    session_date: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Create session data structure that mimics PokerNow format but for live games.
    
    This allows us to reuse existing dual_write_service.py logic.
    """
    if session_date is None:
        session_date = datetime.now(timezone.utc)
    
    # Create live game session data structure
    session_data = {
        "sessionId": f"live_{session_name}_{int(session_date.timestamp())}",
        "sessionType": "live",
        "sessionName": session_name,
        "startedAt": session_date.isoformat(),
        "endedAt": session_date.isoformat(),  # For live games, start/end are the same
        "playersInfos": []
    }
    
    # Convert player data to PokerNow-like format
    for i, player in enumerate(players_data):
        player_info = {
            "id": f"live_player_{i}_{session_name}_{player['name']}",  # Synthetic ID for live players
            "name": player["name"],
            "buyInSum": player["buyInSum"],
            "buyOutSum": player["buyOutSum"], 
            "inGame": player["inGame"],
            "net": player["net"],
            "external_id": None,  # No external ID for live games
            "validated_name": player["name"]  # Use actual name as validated name
        }
        session_data["playersInfos"].append(player_info)
    
    return session_data


def get_or_create_live_player(
    db: Session, 
    player_name: str, 
    game_id: str
) -> Player:
    """
    Get or create a player for live games.
    Live players don't have external_id, so we match on display_name.
    """
    # First try to find existing player by name within this game only (case-insensitive)
    existing_player = db.execute(
        select(Player)
        .join(GamePlayer, Player.id == GamePlayer.player_id)
        .where(
            GamePlayer.game_id == game_id,
            func.lower(Player.display_name) == player_name.lower()
        )
    ).scalar_one_or_none()
    
    if existing_player:
        log.debug(f"Found existing player: {existing_player.display_name}")
        
        # Ensure player is linked to the game
        game_player_exists = db.execute(
            select(GamePlayer).where(
                GamePlayer.game_id == game_id,
                GamePlayer.player_id == existing_player.id
            )
        ).scalar_one_or_none()
        
        if not game_player_exists:
            log.debug(f"Linking existing player {existing_player.display_name} to game")
            game_player = GamePlayer(game_id=game_id, player_id=existing_player.id)
            db.add(game_player)
        
        return existing_player
    
    # Create new player for live game
    log.debug(f"Creating new player: {player_name}")
    new_player = Player(
        display_name=player_name,
        external_id=None  # No external ID for live games
    )
    db.add(new_player)
    db.flush()  # Get the ID
    
    # Link to game
    game_player = GamePlayer(game_id=game_id, player_id=new_player.id)
    db.add(game_player)
    
    return new_player


def validate_session_balance(players_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validate that the session balances correctly.
    
    Returns validation results and warnings.
    """
    total_buy_ins = sum(player["buyInSum"] for player in players_data)
    total_cash_outs = sum(player["buyOutSum"] for player in players_data) 
    total_in_game = sum(player["inGame"] for player in players_data)
    total_net = sum(player["net"] for player in players_data)
    
    # Check if money is conserved (buy-ins should equal cash-outs + in-game)
    total_out = total_cash_outs + total_in_game
    imbalance = total_out - total_buy_ins
    
    validation = {
        "total_buy_ins": total_buy_ins,
        "total_cash_outs": total_cash_outs,
        "total_in_game": total_in_game,
        "total_out": total_out,
        "imbalance": imbalance,
        "net_sum": total_net,
        "balanced": abs(imbalance) < 5,  # Allow 5 cent rounding error
        "warnings": []
    }
    
    if abs(imbalance) >= 5:
        validation["warnings"].append(
            f"Session doesn't balance: ${abs(imbalance)/100:.2f} "
            f"{'more out' if imbalance > 0 else 'more in'} than expected"
        )
    
    if abs(total_net - imbalance) >= 5:
        validation["warnings"].append(
            "Net calculations don't match balance calculations"
        )
    
    return validation