"""
Poker Statistics Service

Processes poker events to calculate professional statistics:
- VPIP (Voluntarily Put money In Pot)
- PFR (Pre-Flop Raise)
- AF (Aggression Frequency)

Parses PokerNow raw entries and populates hand participation data.
"""

import re
from typing import Dict, List, Optional, Set, Tuple
from decimal import Decimal
from sqlalchemy.orm import Session
from db.models import (
    PokerEvent, PlayerHandParticipation, PlayerStatisticsCache,
    Player, Session as SessionModel, Game
)
from .game_statistics_config_service import GameStatisticsConfigService


class PokerStatisticsProcessor:
    """Processes poker events to calculate statistics."""

    def __init__(self, db_session: Session):
        self.db = db_session
        self.street_markers = {'Flop:', 'Turn:', 'River:'}

    def process_session_statistics(self, session_id: str) -> Dict:
        """Process all hands in a session to calculate statistics."""

        # Get all poker events for this session, ordered by hand and sequence
        events = (self.db.query(PokerEvent)
                 .filter(PokerEvent.session_id == session_id)
                 .order_by(PokerEvent.hand_number, PokerEvent.order_number)
                 .all())

        if not events:
            return {"message": "No poker events found for session"}

        # Group events by hand number
        hands_data = {}
        for event in events:
            hand_num = event.hand_number
            if hand_num not in hands_data:
                hands_data[hand_num] = []
            hands_data[hand_num].append(event)

        # Process each hand
        processed_hands = 0
        for hand_number, hand_events in hands_data.items():
            if hand_number is not None:
                self._process_single_hand(session_id, hand_number, hand_events)
                processed_hands += 1

        # Calculate aggregated statistics
        self._calculate_session_statistics(session_id)

        return {
            "session_id": session_id,
            "hands_processed": processed_hands,
            "message": "Statistics calculated successfully"
        }

    def _extract_player_from_raw_entry(self, raw_entry: str) -> Optional[str]:
        """Extract player name from raw entry like 'Player "name @ id" does action'."""
        if not raw_entry:
            return None

        # Pattern to match player names in quotes with @ symbol
        import re
        match = re.search(r'"([^"]+?)\s*@\s*([^"]+?)"', raw_entry)
        if match:
            return match.group(2).strip()  # Return the external ID part
        return None

    def _get_player_id_from_external_id(self, external_id: str) -> Optional[str]:
        """Get Player.id UUID from external_id."""
        if not external_id:
            return None

        player = self.db.query(Player).filter(Player.external_id == external_id).first()
        return str(player.id) if player else None

    def _process_single_hand(self, session_id: str, hand_number: int, events: List[PokerEvent]):
        """Process a single hand to determine player actions and participation."""

        # Track hand state
        current_street = 'preflop'
        players_in_hand: Set[str] = set()
        player_actions: Dict[str, Dict] = {}  # external_id -> action data

        # Initialize tracking for all players who act in this hand
        for event in events:
            # Try to get player ID from event, or extract from raw entry and map to UUID
            player_key = event.player_id
            if not player_key:
                external_id = self._extract_player_from_raw_entry(event.raw_entry)
                if external_id:
                    player_key = self._get_player_id_from_external_id(external_id)

            if player_key and player_key not in player_actions:
                player_actions[player_key] = {
                    'was_dealt_cards': False,
                    'posted_blind': False,
                    'posted_sb_amount': None,
                    'posted_bb_amount': None,
                    'vpip_eligible': False,
                    'vpip_action': False,
                    'pfr_action': False,
                    'preflop_fold': False,
                    'postflop_actions': 0,
                    'postflop_aggressive': 0,
                    'postflop_passive': 0,
                    'flop_actions': 0,
                    'flop_aggressive': 0,
                    'turn_actions': 0,
                    'turn_aggressive': 0,
                    'river_actions': 0,
                    'river_aggressive': 0,
                }

        # Process each event in sequence
        for event in events:
            if not event.raw_entry:
                continue

            raw = event.raw_entry.strip()

            # Detect street changes
            if any(marker in raw for marker in self.street_markers):
                if 'Flop:' in raw:
                    current_street = 'flop'
                elif 'Turn:' in raw:
                    current_street = 'turn'
                elif 'River:' in raw:
                    current_street = 'river'
                continue

            # Parse player actions - get player key the same way as initialization
            player_key = event.player_id
            if not player_key:
                external_id = self._extract_player_from_raw_entry(event.raw_entry)
                if external_id:
                    player_key = self._get_player_id_from_external_id(external_id)

            if player_key:
                self._parse_player_action(event, current_street, player_actions, player_key)

        # Determine which players were dealt cards (had opportunity to act)
        self._determine_dealt_players(player_actions)

        # Save hand participation data
        for player_id, actions in player_actions.items():
            participation = PlayerHandParticipation(
                session_id=session_id,
                player_id=player_id,
                hand_number=hand_number,
                **actions
            )

            # Check if participation already exists
            existing = (self.db.query(PlayerHandParticipation)
                       .filter_by(session_id=session_id, player_id=player_id, hand_number=hand_number)
                       .first())

            if existing:
                # Update existing record
                for key, value in actions.items():
                    setattr(existing, key, value)
            else:
                # Add new record
                self.db.add(participation)

    def _parse_player_action(self, event: PokerEvent, street: str, player_actions: Dict[str, Dict], player_key: str):
        """Parse individual player action from raw entry."""

        raw = event.raw_entry

        if player_key not in player_actions:
            return

        actions = player_actions[player_key]

        # Blind posts
        if 'posts small blind' in raw:
            actions['posted_blind'] = True
            actions['posted_sb_amount'] = event.amount
            actions['was_dealt_cards'] = True

        elif 'posts big blind' in raw:
            actions['posted_blind'] = True
            actions['posted_bb_amount'] = event.amount
            actions['was_dealt_cards'] = True

        # Pre-flop actions
        elif street == 'preflop':
            actions['was_dealt_cards'] = True
            actions['vpip_eligible'] = True

            if 'calls' in raw:
                actions['vpip_action'] = True

            elif 'raises' in raw or 'bets' in raw:
                actions['vpip_action'] = True
                actions['pfr_action'] = True

            elif 'folds' in raw:
                actions['preflop_fold'] = True

            # Big blind check is not VPIP
            elif 'checks' in raw:
                pass  # BB checking is not VPIP

        # Post-flop actions
        else:
            if any(action in raw for action in ['calls', 'checks', 'bets', 'raises', 'folds']):
                actions['postflop_actions'] += 1

                # Count aggressive vs passive actions
                if 'bets' in raw or 'raises' in raw:
                    actions['postflop_aggressive'] += 1

                    # Street-specific tracking
                    if street == 'flop':
                        actions['flop_actions'] += 1
                        actions['flop_aggressive'] += 1
                    elif street == 'turn':
                        actions['turn_actions'] += 1
                        actions['turn_aggressive'] += 1
                    elif street == 'river':
                        actions['river_actions'] += 1
                        actions['river_aggressive'] += 1

                elif 'calls' in raw or 'checks' in raw:
                    actions['postflop_passive'] += 1

                    # Street-specific tracking (just actions, not aggressive)
                    if street == 'flop':
                        actions['flop_actions'] += 1
                    elif street == 'turn':
                        actions['turn_actions'] += 1
                    elif street == 'river':
                        actions['river_actions'] += 1

    def _determine_dealt_players(self, player_actions: Dict[str, Dict]):
        """Determine which players were actually dealt cards."""

        # Players are considered dealt cards if they:
        # 1. Posted a blind, OR
        # 2. Took any action (call, raise, fold, check)
        for player_id, actions in player_actions.items():
            if (actions['posted_blind'] or
                actions['vpip_action'] or
                actions['pfr_action'] or
                actions['preflop_fold'] or
                actions['postflop_actions'] > 0):
                actions['was_dealt_cards'] = True

    def _calculate_session_statistics(self, session_id: str):
        """Calculate and cache aggregated statistics for the session."""

        # Get all players who participated in this session
        participants = (self.db.query(PlayerHandParticipation.player_id)
                       .filter(PlayerHandParticipation.session_id == session_id)
                       .distinct()
                       .all())

        for (player_id,) in participants:
            self._calculate_player_session_stats(session_id, player_id)

    def _calculate_player_session_stats(self, session_id: str, player_id: str):
        """Calculate statistics for a specific player in a session."""

        # Get all hand participations for this player in this session
        participations = (self.db.query(PlayerHandParticipation)
                         .filter_by(session_id=session_id, player_id=player_id)
                         .all())

        if not participations:
            return

        # Count statistics
        hands_dealt = sum(1 for p in participations if p.was_dealt_cards)
        vpip_hands = sum(1 for p in participations if p.vpip_action)
        pfr_hands = sum(1 for p in participations if p.pfr_action)

        postflop_total_actions = sum(p.postflop_actions for p in participations)
        postflop_aggressive_actions = sum(p.postflop_aggressive for p in participations)
        postflop_passive_actions = sum(p.postflop_passive for p in participations)

        # Calculate percentages
        vpip_percentage = (vpip_hands / hands_dealt * 100) if hands_dealt > 0 else None
        pfr_percentage = (pfr_hands / hands_dealt * 100) if hands_dealt > 0 else None

        # AF = (Bets + Raises) / (Bets + Raises + Calls) * 100
        total_actions = postflop_aggressive_actions + postflop_passive_actions
        aggression_frequency = (postflop_aggressive_actions / total_actions * 100) if total_actions > 0 else None

        # Calculate street-specific AF
        flop_agg = sum(p.flop_aggressive for p in participations)
        flop_total = sum(p.flop_actions for p in participations)
        flop_af = (flop_agg / flop_total * 100) if flop_total > 0 else None

        turn_agg = sum(p.turn_aggressive for p in participations)
        turn_total = sum(p.turn_actions for p in participations)
        turn_af = (turn_agg / turn_total * 100) if turn_total > 0 else None

        river_agg = sum(p.river_aggressive for p in participations)
        river_total = sum(p.river_actions for p in participations)
        river_af = (river_agg / river_total * 100) if river_total > 0 else None

        # Classify play style
        play_style = self._classify_play_style(vpip_percentage, pfr_percentage, aggression_frequency)

        # Save or update statistics cache
        existing_stats = (self.db.query(PlayerStatisticsCache)
                         .filter_by(session_id=session_id, player_id=player_id)
                         .first())

        stats_data = {
            'hands_dealt': hands_dealt,
            'vpip_hands': vpip_hands,
            'pfr_hands': pfr_hands,
            'postflop_hands': sum(1 for p in participations if p.postflop_actions > 0),
            'postflop_total_actions': postflop_total_actions,
            'postflop_aggressive_actions': postflop_aggressive_actions,
            'postflop_passive_actions': postflop_passive_actions,
            'vpip_percentage': Decimal(str(round(vpip_percentage, 2))) if vpip_percentage is not None else None,
            'pfr_percentage': Decimal(str(round(pfr_percentage, 2))) if pfr_percentage is not None else None,
            'aggression_frequency': Decimal(str(round(aggression_frequency, 2))) if aggression_frequency is not None else None,
            'flop_af': Decimal(str(round(flop_af, 2))) if flop_af is not None else None,
            'turn_af': Decimal(str(round(turn_af, 2))) if turn_af is not None else None,
            'river_af': Decimal(str(round(river_af, 2))) if river_af is not None else None,
            'play_style': play_style,
        }

        if existing_stats:
            # Update existing
            for key, value in stats_data.items():
                setattr(existing_stats, key, value)
        else:
            # Create new
            stats = PlayerStatisticsCache(
                session_id=session_id,
                player_id=player_id,
                **stats_data
            )
            self.db.add(stats)

    def _classify_play_style(self, vpip: Optional[float], pfr: Optional[float], af: Optional[float]) -> Optional[str]:
        """Classify player style using fun, descriptive names optimized for high-stack cash games."""

        if vpip is None or pfr is None:
            return None

        # Use the same fun classification logic as the config service
        # Special cases (check these first)
        if vpip > 65 and pfr < 10:
            return "Calling Station"

        if vpip > 70 and pfr > 35:
            return "Maniac"

        if vpip > 70 and pfr < 15:
            return "ATM"

        if vpip < 40:  # Very tight for this game type
            if pfr < 10:
                return "Super Nit"
            else:
                return "Nit"

        # VPIP > 65% (Very Loose)
        if vpip > 65:
            if pfr > 25:
                return "Splashy Aggressive"
            elif 15 <= pfr <= 25:
                return "Splashy Balanced"
            # < 15 covered by special cases above

        # VPIP 55-65% (Loose)
        elif vpip >= 55:
            if pfr > 30:
                return "LAG Monster"
            elif 20 <= pfr <= 30:
                return "Action Player"
            elif 10 <= pfr < 20:
                return "Loose Cannon"
            else:  # pfr < 10
                return "Passive Fish"

        # Check for TAG Crusher first (high PFR regardless of VPIP in moderate range)
        elif pfr > 30:
            return "TAG Crusher"

        # VPIP 45-55% (Standard for this game)
        elif vpip >= 45:
            if pfr > 25:
                return "Aggressive Regular"
            elif 15 <= pfr <= 25:
                return "Active Player"
            else:  # pfr < 15
                return "Passive Regular"

        # VPIP < 45% (Tight for this game) - remaining cases
        else:
            if 20 <= pfr <= 30:
                return "Selective Aggressive"
            elif 10 <= pfr < 20:
                return "Cautious Player"
            else:  # pfr < 10
                return "Rock"

        # Fallback (shouldn't reach here)
        return "Mystery Player"

    def get_session_statistics(self, session_id: str, use_adaptive_classification: bool = True) -> List[Dict]:
        """Get calculated statistics for all players in a session with adaptive classification."""

        # Get session and game info
        session = self.db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if not session:
            return []

        stats = (self.db.query(PlayerStatisticsCache, Player.display_name)
                .join(Player, PlayerStatisticsCache.player_id == Player.id)
                .filter(PlayerStatisticsCache.session_id == session_id)
                .all())

        if not stats:
            return []

        # Get game configuration for adaptive classification
        config_service = GameStatisticsConfigService(self.db)
        game_config = None
        if use_adaptive_classification:
            game_config = config_service.get_or_create_game_config(session.game_id)

        result = []
        for stat, player_name in stats:
            player_data = {
                'playerId': str(stat.player_id),
                'playerName': player_name,
                'handsPlayed': stat.hands_dealt,
                'vpip': float(stat.vpip_percentage) if stat.vpip_percentage else 0,
                'pfr': float(stat.pfr_percentage) if stat.pfr_percentage else 0,
                'aggressionFrequency': float(stat.aggression_frequency) if stat.aggression_frequency else 0,
                'flopAF': float(stat.flop_af) if stat.flop_af else 0,
                'turnAF': float(stat.turn_af) if stat.turn_af else 0,
                'riverAF': float(stat.river_af) if stat.river_af else 0,
            }

            # Add adaptive classification if enabled
            if use_adaptive_classification and game_config:
                classification = config_service.classify_player(
                    player_data['vpip'],
                    player_data['pfr'],
                    player_data['aggressionFrequency'],
                    game_config
                )
                player_data.update({
                    'playStyle': classification.style,
                    'styleColor': classification.style_color,
                    'styleDescription': classification.description,
                    'vpipCategory': classification.vpip_category,
                    'pfrCategory': classification.pfr_category,
                    'afCategory': classification.af_category,
                })
            else:
                # Use legacy classification
                player_data['playStyle'] = stat.play_style or 'Unknown'

            result.append(player_data)

        return sorted(result, key=lambda x: x['handsPlayed'], reverse=True)