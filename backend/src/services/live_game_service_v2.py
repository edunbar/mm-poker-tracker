"""
Domain-based LiveGameService v2

Direct replacement for live_game_service.py using domain layer.
Maintains exact API compatibility while using clean domain architecture.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from decimal import Decimal

from sqlalchemy.orm import Session

from db.database import SessionLocal
from domain.poker.entities.poker_session import PokerSession
from domain.poker.value_objects import (
    SessionId, PlayerId, GameId, Money, Hand
)
from domain.poker.exceptions import (
    SessionNotFoundError as DomainSessionNotFoundError,
    SessionAlreadyEndedError as DomainSessionAlreadyEndedError,
    InvalidCashOutAmountError as DomainInvalidCashOutAmountError,
)
from infrastructure.persistence.sqlalchemy.poker_repository import SQLAlchemyPokerSessionRepository

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

    This allows us to reuse existing session_ingestion_service.py logic.
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


class LiveGameService:
    """
    Domain-based LiveGameService that replaces the old utility functions approach.

    Uses domain entities and repositories for business logic while maintaining
    exact API compatibility with the existing Flask routes.
    """

    def __init__(self, db_session: Session):
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
        self._repository = SQLAlchemyPokerSessionRepository(self._db_session)

    def end_session(self, session_id: str, cash_out_amount: float) -> Dict[str, Any]:
        """
        End a poker session using domain layer.

        Args:
            session_id: Session identifier
            cash_out_amount: Cash out amount in dollars

        Returns:
            Dictionary with session results (maintains compatibility)

        Raises:
            ValueError: For business rule violations (matches old service)
        """
        log.info(f"Ending session {session_id} with cash out ${cash_out_amount}")

        try:
            # Convert to domain value objects
            try:
                domain_session_id = SessionId(session_id)
            except ValueError:
                # If SessionId is invalid format, treat as "not found" for compatibility
                log.warning(f"Invalid session ID format: {session_id}")
                raise ValueError("Session not found")

            domain_cash_out = Money(str(cash_out_amount))

            # Find the session using repository
            session = self._repository.find_by_id(domain_session_id)
            if session is None:
                log.warning(f"Session not found: {session_id}")
                raise ValueError("Session not found")

            log.debug(f"Found session {session_id}, current state: {session.state}")

            # Use domain methods for business logic
            session.end_session(domain_cash_out)

            # Calculate results using domain logic
            profit = session.calculate_profit()
            hourly_rate = session.calculate_hourly_rate() if session.is_ended() else Money.zero()

            # Save using repository
            self._repository.save(session)

            log.info(f"Session {session_id} ended successfully. Profit: ${profit.amount}")

            # Return compatible format
            return {
                "session_id": session_id,
                "profit": float(profit.amount),
                "hourly_rate": float(hourly_rate.amount),
                "duration_minutes": session.get_duration().minutes,
                "hands_played": session.get_hand_count(),
                "is_profitable": session.is_profitable()
            }

        except DomainSessionNotFoundError:
            log.warning(f"Domain: Session not found: {session_id}")
            raise ValueError("Session not found")

        except DomainSessionAlreadyEndedError:
            log.warning(f"Domain: Session already ended: {session_id}")
            raise ValueError("Session already ended")

        except DomainInvalidCashOutAmountError as e:
            log.warning(f"Domain: Invalid cash out amount: {e}")
            raise ValueError("Cannot cash out negative amount")

        except ValueError as e:
            # Re-raise ValueError for compatibility
            log.error(f"Validation error ending session {session_id}: {e}")
            raise

        except Exception as e:
            log.error(f"Unexpected error ending session {session_id}: {e}")
            raise ValueError(f"Internal error: {str(e)}")

    def create_session(
        self,
        game_id: str,
        player_id: str,
        buy_in_amount: float,
        session_type: str = "live",
        session_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new poker session using domain layer.

        Args:
            game_id: Game identifier (5 characters)
            player_id: Player UUID
            buy_in_amount: Buy-in amount in dollars
            session_type: Type of session
            session_name: Optional session name

        Returns:
            Dictionary with session details

        Raises:
            ValueError: For validation errors
        """
        log.info(f"Creating session for player {player_id} in game {game_id}")

        try:
            # Create domain value objects
            domain_session_id = SessionId.generate()
            domain_player_id = PlayerId(player_id)
            # Use the actual game_id if it's 5 characters (public_code), otherwise use a dummy
            if len(game_id) == 5:
                domain_game_id = GameId(game_id)
            else:
                domain_game_id = GameId("DUMMY")  # For UUIDs, use dummy for domain compatibility
            domain_buy_in = Money(str(buy_in_amount))

            # Create domain entity
            session = PokerSession(
                session_id=domain_session_id,
                player_id=domain_player_id,
                game_id=domain_game_id,
                buy_in_amount=domain_buy_in,
                session_type=session_type,
                session_name=session_name
            )

            # Save using repository
            self._repository.save(session)

            log.info(f"Created session {domain_session_id} for player {player_id}")

            # Return compatible format
            return {
                "session_id": str(domain_session_id),
                "player_id": player_id,
                "game_id": game_id,
                "buy_in_amount": float(domain_buy_in.amount),
                "session_type": session_type,
                "session_name": session_name,
                "created_at": session.created_at.isoformat(),
                "state": session.state.value
            }

        except ValueError as e:
            # Domain validation errors
            log.error(f"Validation error creating session: {e}")
            raise ValueError(str(e))

        except Exception as e:
            log.error(f"Unexpected error creating session: {e}")
            raise ValueError(f"Internal error: {str(e)}")

    def get_session_details(self, session_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a session.

        Args:
            session_id: Session identifier

        Returns:
            Dictionary with session details

        Raises:
            ValueError: If session not found
        """
        log.debug(f"Getting details for session {session_id}")

        try:
            domain_session_id = SessionId(session_id)
            session = self._repository.find_by_id(domain_session_id)

            if session is None:
                log.warning(f"Session not found: {session_id}")
                raise ValueError("Session not found")

            # Calculate stats using domain logic
            current_profit = session.calculate_profit() if session.is_ended() else session._calculate_hands_profit()
            stats = session.get_session_stats()
            duration = session.get_duration()

            return {
                "session_id": str(session.session_id),
                "player_id": str(session.player_id),
                "game_id": str(session.game_id),
                "buy_in_amount": float(session.buy_in_amount.amount),
                "cash_out_amount": float(session.cash_out_amount.amount) if session.cash_out_amount else None,
                "session_type": session.session_type,
                "session_name": session.session_name,
                "created_at": session.created_at.isoformat(),
                "ended_at": session.ended_at.isoformat() if session.ended_at else None,
                "state": session.state.value,
                "current_profit": float(current_profit.amount),
                "duration_minutes": duration.minutes,
                "hands_played": stats.total_hands,
                "winning_hands": stats.winning_hands,
                "win_rate": stats.win_rate(),
                "is_profitable": session.is_profitable(),
                "is_marathon": duration.is_marathon_session()
            }

        except ValueError as e:
            log.error(f"Error getting session details: {e}")
            raise

        except Exception as e:
            log.error(f"Unexpected error getting session details: {e}")
            raise ValueError(f"Internal error: {str(e)}")

    def add_hand_to_session(
        self,
        session_id: str,
        hand_number: int,
        pot_size: float,
        player_result: float
    ) -> Dict[str, Any]:
        """
        Add a hand to an existing session.

        Args:
            session_id: Session identifier
            hand_number: Hand number (must be unique within session)
            pot_size: Size of the pot in dollars
            player_result: Player's result for this hand in dollars

        Returns:
            Dictionary with hand details

        Raises:
            ValueError: For validation errors
        """
        log.debug(f"Adding hand {hand_number} to session {session_id}")

        try:
            domain_session_id = SessionId(session_id)
            session = self._repository.find_by_id(domain_session_id)

            if session is None:
                log.warning(f"Session not found: {session_id}")
                raise ValueError("Session not found")

            # Create domain hand object
            hand = Hand(
                hand_number=hand_number,
                pot_size=Money(str(pot_size)),
                player_result=Money(str(player_result))
            )

            # Use domain method to add hand
            session.add_hand(hand)

            # Save changes
            self._repository.save(session)

            log.info(f"Added hand {hand_number} to session {session_id}")

            return {
                "session_id": session_id,
                "hand_number": hand_number,
                "pot_size": pot_size,
                "player_result": player_result,
                "total_hands": session.get_hand_count(),
                "current_profit": float(session._calculate_hands_profit().amount)
            }

        except ValueError as e:
            log.error(f"Error adding hand: {e}")
            raise

        except Exception as e:
            log.error(f"Unexpected error adding hand: {e}")
            raise ValueError(f"Internal error: {str(e)}")

    def get_active_sessions_for_player(self, player_id: str) -> List[Dict[str, Any]]:
        """
        Get all active sessions for a player.

        Args:
            player_id: Player UUID

        Returns:
            List of active session dictionaries
        """
        log.debug(f"Getting active sessions for player {player_id}")

        try:
            domain_player_id = PlayerId(player_id)
            sessions = self._repository.find_active_sessions_for_player(domain_player_id)

            result = []
            for session in sessions:
                current_profit = session._calculate_hands_profit()
                duration = session.get_duration()

                result.append({
                    "session_id": str(session.session_id),
                    "game_id": str(session.game_id),
                    "buy_in_amount": float(session.buy_in_amount.amount),
                    "session_type": session.session_type,
                    "session_name": session.session_name,
                    "created_at": session.created_at.isoformat(),
                    "current_profit": float(current_profit.amount),
                    "duration_minutes": duration.minutes,
                    "hands_played": session.get_hand_count()
                })

            log.info(f"Found {len(result)} active sessions for player {player_id}")
            return result

        except ValueError as e:
            log.error(f"Error getting active sessions: {e}")
            raise

        except Exception as e:
            log.error(f"Unexpected error getting active sessions: {e}")
            raise ValueError(f"Internal error: {str(e)}")


# Maintain backward compatibility with function-based API
def get_or_create_live_player(db: Session, player_name: str, game_id: str):
    """
    Legacy function for backward compatibility.

    This function is maintained to support existing code that imports it directly.
    """
    from sqlalchemy import select, func
    from ..db.models import Player, GamePlayer

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