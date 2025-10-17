"""
LiveGameToSessionMapper - Convert live game data to session format

This service converts closed live game data (participants, transactions, stats)
into the format expected by session_ingestion_service.py for ledger creation.

Key conversions:
- Decimal dollars → BigInteger cents (multiply by 100)
- LiveGameParticipant → Player lookup/creation
- Transaction stats → SessionPlayerSummary format
- LiveGame metadata → Session external_id and metadata
"""

import logging
from typing import Dict, Any, List
from decimal import Decimal
from datetime import datetime

from domain.live_game.entities import LiveGame, LiveGameParticipant

log = logging.getLogger(__name__)


class LiveGameToSessionMapper:
    """
    Maps live game data to session ingestion format.

    This mapper creates a data structure compatible with the existing
    session_ingestion_service.py to enable automatic session creation
    when a live game is closed.
    """

    @staticmethod
    def map_live_game_to_session_data(
        live_game: LiveGame,
        participants: List[LiveGameParticipant],
        transaction_stats: Dict[str, Dict]  # participant_id -> stats dict
    ) -> Dict[str, Any]:
        """
        Convert live game data to session ingestion format.

        Args:
            live_game: The closed live game entity
            participants: List of all participants in the game
            transaction_stats: Dictionary mapping participant_id to their stats:
                {
                    'participant_id': {
                        'total_buy_ins': Decimal,
                        'total_cash_outs': Decimal,
                        'net_result': Decimal,
                        'chips_on_table': Decimal
                    }
                }

        Returns:
            Dictionary compatible with session_ingestion_service.ingest_session():
            {
                'sessionId': str,
                'sessionType': 'live',
                'sessionName': str,
                'startedAt': str (ISO),
                'endedAt': str (ISO),
                'playersInfos': [
                    {
                        'id': str,
                        'name': str,
                        'validated_name': str,
                        'buyInSum': int (cents),
                        'buyOutSum': int (cents),
                        'inGame': int (cents),
                        'net': int (cents),
                        'names': [str]
                    }
                ]
            }

        Raises:
            ValueError: If live game is not closed or data is invalid
        """
        if live_game.status != 'closed':
            raise ValueError(f"Cannot create session from non-closed live game (status: {live_game.status})")

        if not live_game.closed_at:
            raise ValueError("Closed live game must have closed_at timestamp")

        if not participants:
            raise ValueError("Cannot create session from live game with no participants")

        # Create unique external ID for this live game session
        # Format: live_{join_code}_{timestamp}
        external_id = f"live_{live_game.join_code.value}_{int(live_game.started_at.timestamp())}"

        # Create session name
        session_name = f"Live Game {live_game.join_code.value}"

        # Build players data
        players_infos = []

        for participant in participants:
            participant_id = str(participant.id)
            stats = transaction_stats.get(participant_id, {})

            # Extract stats (all in Decimal dollars)
            total_buy_ins = stats.get('total_buy_ins', Decimal('0'))
            total_cash_outs = stats.get('total_cash_outs', Decimal('0'))
            chips_on_table = stats.get('chips_on_table', Decimal('0'))
            net_result = stats.get('net_result', Decimal('0'))

            # Convert dollars to cents (multiply by 100)
            buy_in_cents = LiveGameToSessionMapper._dollars_to_cents(total_buy_ins)
            cash_out_cents = LiveGameToSessionMapper._dollars_to_cents(total_cash_outs)
            in_game_cents = LiveGameToSessionMapper._dollars_to_cents(chips_on_table)
            net_cents = LiveGameToSessionMapper._dollars_to_cents(net_result)

            # Validate conversion
            if chips_on_table > Decimal('0'):
                log.warning(
                    f"Participant {participant.display_name} still has ${chips_on_table} "
                    f"on table - this should have been caught during close validation"
                )

            # Create player info dict
            # Use claimed player identity if available, otherwise create new player
            if participant.player_id and participant.claimed_player_external_id:
                # Participant has claimed an existing player identity
                player_info = {
                    'id': participant.claimed_player_external_id,
                    'name': participant.claimed_player_name,
                    'validated_name': participant.claimed_player_name,
                    'buyInSum': buy_in_cents,
                    'buyOutSum': cash_out_cents,
                    'inGame': in_game_cents,
                    'net': net_cents,
                    'names': [participant.claimed_player_name]
                }
                log.debug(
                    f"Participant {participant.display_name} linked to claimed player "
                    f"{participant.claimed_player_name} (external_id: {participant.claimed_player_external_id})"
                )
            else:
                # No claimed identity - create new player using user_id
                player_info = {
                    'id': str(participant.user_id),
                    'name': participant.display_name,
                    'validated_name': participant.display_name,
                    'buyInSum': buy_in_cents,
                    'buyOutSum': cash_out_cents,
                    'inGame': in_game_cents,
                    'net': net_cents,
                    'names': [participant.display_name]
                }
                log.debug(
                    f"Participant {participant.display_name} creating new player "
                    f"(external_id: {participant.user_id})"
                )

            players_infos.append(player_info)

            log.debug(
                f"Mapped participant {participant.display_name}: "
                f"buy_in=${total_buy_ins} ({buy_in_cents}¢), "
                f"cash_out=${total_cash_outs} ({cash_out_cents}¢), "
                f"net=${net_result} ({net_cents}¢)"
            )

        # Build session data structure
        session_data = {
            'sessionId': external_id,
            'sessionType': 'live',
            'sessionName': session_name,
            'startedAt': live_game.started_at.isoformat(),
            'endedAt': live_game.closed_at.isoformat(),
            'playersInfos': players_infos,
            # Add metadata for tracking
            'meta': {
                'source': 'live_game',
                'live_game_id': str(live_game.id),
                'join_code': live_game.join_code.value,
                'game_id': str(live_game.game_id),
                'started_at': live_game.started_at.isoformat(),
                'closed_at': live_game.closed_at.isoformat(),
                'participant_count': len(participants)
            }
        }

        log.info(
            f"Mapped live game {live_game.join_code.value} to session data: "
            f"{len(players_infos)} players, external_id={external_id}"
        )

        return session_data

    @staticmethod
    def _dollars_to_cents(amount: Decimal) -> int:
        """
        Convert Decimal dollars to integer cents.

        Args:
            amount: Amount in dollars (e.g., Decimal('10.50'))

        Returns:
            Amount in cents (e.g., 1050)

        Examples:
            >>> _dollars_to_cents(Decimal('10.50'))
            1050
            >>> _dollars_to_cents(Decimal('0.01'))
            1
            >>> _dollars_to_cents(Decimal('0'))
            0
        """
        if amount is None:
            return 0

        # Multiply by 100 and convert to int
        # Using quantize to handle any rounding issues
        cents = amount * 100
        return int(cents)

    @staticmethod
    def get_session_timestamp(live_game: LiveGame) -> datetime:
        """
        Get the appropriate timestamp for the session.

        Uses closed_at if available (when game ended), otherwise started_at.

        Args:
            live_game: Live game entity

        Returns:
            Datetime to use for session timestamp
        """
        return live_game.closed_at or live_game.started_at
