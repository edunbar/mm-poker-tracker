from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from db.models import PokerEvent, HandSummary, Player, Session as SessionModel
from services.hand_log_parser import HandLogParser
import logging

logger = logging.getLogger(__name__)

class HandLogService:

    @staticmethod
    def check_duplicate_import(db: Session, session_id: str) -> bool:
        existing = db.query(PokerEvent).filter(
            PokerEvent.session_id == session_id
        ).first()
        return existing is not None

    @staticmethod
    def match_players(db: Session, unmatched_players: List[tuple], game_id: str) -> Dict:
        matched = {}
        unmatched = []

        for display_name, external_id in unmatched_players:
            player = None

            if external_id:
                player = db.query(Player).filter(
                    Player.external_id == external_id
                ).first()

            if not player and display_name:
                player = db.query(Player).join(
                    Player.games
                ).filter(
                    Player.display_name.ilike(display_name)
                ).first()

            if player:
                matched[(display_name, external_id)] = str(player.id)
            else:
                unmatched.append({
                    'display_name': display_name,
                    'external_id': external_id
                })

        return {
            'matched': matched,
            'unmatched': unmatched
        }

    @staticmethod
    def apply_player_mappings(events: List[Dict], mappings: Dict[str, str]) -> List[Dict]:
        for event in events:
            key = (event.get('player_name'), event.get('external_id'))
            if key in mappings:
                event['player_id'] = mappings[key]
        return events

    @staticmethod
    def import_hand_log(
        db: Session,
        session_id: str,
        csv_content: str,
        player_mappings: Optional[Dict] = None
    ) -> Dict:
        if HandLogService.check_duplicate_import(db, session_id):
            return {
                'status': 'success',
                'message': 'Hand log already imported for this session',
                'events_created': 0,
                'hands_created': 0
            }

        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        parsed_events, metadata = HandLogParser.parse_hand_log(csv_content)

        player_match_result = HandLogService.match_players(
            db,
            metadata['unmatched_players'],
            str(session.game_id)
        )

        if player_match_result['unmatched'] and not player_mappings:
            return {
                'status': 'needs_mapping',
                'unmatched_players': player_match_result['unmatched'],
                'total_events': metadata['total_events'],
                'total_hands': metadata['total_hands']
            }

        if player_mappings:
            parsed_events = HandLogService.apply_player_mappings(parsed_events, player_mappings)

        events_created = 0
        hands_created = 0

        for event_data in parsed_events:
            player_id = event_data.get('player_id') or player_match_result['matched'].get(
                (event_data.get('player_name'), event_data.get('external_id'))
            )

            poker_event = PokerEvent(
                session_id=session_id,
                hand_number=event_data.get('hand_number'),
                event_type=event_data['event_type'],
                player_id=player_id,
                player_name=event_data.get('player_name'),
                amount=event_data.get('amount'),
                cards=event_data.get('cards'),
                event_timestamp=event_data.get('event_timestamp'),
                order_number=event_data.get('order_number'),
                raw_entry=event_data.get('raw_entry')
            )
            db.add(poker_event)
            events_created += 1

        for hand_data in metadata['hand_summaries']:
            winner_info = hand_data.get('winner')
            winner_id = None

            if winner_info:
                winner_key = (winner_info.get('name'), winner_info.get('external_id'))
                winner_id = player_mappings.get(winner_key) if player_mappings else player_match_result['matched'].get(winner_key)

            hand_summary = HandSummary(
                session_id=session_id,
                hand_number=hand_data['hand_number'],
                started_at=hand_data.get('started_at'),
                ended_at=hand_data.get('ended_at'),
                pot_size=hand_data.get('pot_size'),
                winner_id=winner_id,
                winner_name=winner_info.get('name') if winner_info else None,
                board_cards=', '.join(hand_data.get('board_cards', [])),
                num_players=len(set(e.get('player_name') for e in hand_data['events'] if e.get('player_name')))
            )
            db.add(hand_summary)
            hands_created += 1

        db.commit()

        return {
            'status': 'success',
            'events_created': events_created,
            'hands_created': hands_created,
            'total_hands': metadata['total_hands']
        }