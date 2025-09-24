from sqlalchemy import func
from sqlalchemy.orm import Session
from db.models import Game, Session as SessionModel, PokerEvent, HandSummary, Player
from datetime import datetime
from typing import List, Dict, Any


def get_hand_analytics(public_code: str) -> Dict[str, Any]:
    from db.database import SessionLocal

    with SessionLocal() as db:
        game = db.query(Game).filter(Game.public_code == public_code).first()
        if not game:
            raise ValueError("Game not found")

        sessions_with_hands_base = db.query(
            SessionModel.id,
            SessionModel.game_number,
            SessionModel.started_at,
            func.count(func.distinct(PokerEvent.hand_number)).label('total_hands'),
            func.count(PokerEvent.id).label('total_actions'),
            func.min(PokerEvent.event_timestamp).label('first_event'),
            func.max(PokerEvent.event_timestamp).label('last_event')
        ).outerjoin(
            PokerEvent, SessionModel.id == PokerEvent.session_id
        ).filter(
            SessionModel.game_id == game.id,
            PokerEvent.id.isnot(None)
        ).group_by(
            SessionModel.id,
            SessionModel.game_number,
            SessionModel.started_at
        ).order_by(
            SessionModel.started_at.desc()
        ).all()

        sessions_with_hands = []
        for session_base in sessions_with_hands_base:
            active_players_count = db.query(
                func.count(func.distinct(PokerEvent.player_name))
            ).filter(
                PokerEvent.session_id == session_base.id,
                PokerEvent.player_name.isnot(None),
                PokerEvent.player_name != ''
            ).scalar() or 0

            sessions_with_hands.append(
                type('SessionWithPlayers', (), {
                    'id': session_base.id,
                    'game_number': session_base.game_number,
                    'started_at': session_base.started_at,
                    'total_hands': session_base.total_hands,
                    'total_actions': session_base.total_actions,
                    'first_event': session_base.first_event,
                    'last_event': session_base.last_event,
                    'active_players': active_players_count
                })()
            )

        total_sessions_in_game = db.query(SessionModel).filter(
            SessionModel.game_id == game.id
        ).count()

        session_analytics = []
        for session in sessions_with_hands:
            duration_hours = 0.0
            if session.first_event and session.last_event:
                duration = session.last_event - session.first_event
                duration_hours = round(duration.total_seconds() / 3600, 1)

            hands_per_hour = 0
            if duration_hours > 0:
                hands_per_hour = round(session.total_hands / duration_hours)

            top_winners = db.query(
                HandSummary.winner_id,
                HandSummary.winner_name,
                func.count(HandSummary.id).label('hands_won'),
                func.max(HandSummary.pot_size).label('biggest_pot')
            ).filter(
                HandSummary.session_id == session.id,
                HandSummary.winner_name.isnot(None),
                HandSummary.winner_name != ''
            ).group_by(
                HandSummary.winner_id,
                HandSummary.winner_name
            ).order_by(
                func.count(HandSummary.id).desc()
            ).limit(3).all()

            top_winners_formatted = []
            for winner in top_winners:
                win_percentage = round((winner.hands_won / session.total_hands * 100), 1) if session.total_hands > 0 else 0
                top_winners_formatted.append({
                    'player_id': str(winner.winner_id) if winner.winner_id else None,
                    'player_name': winner.winner_name,
                    'hands_won': winner.hands_won,
                    'win_percentage': win_percentage,
                    'biggest_pot': winner.biggest_pot or 0
                })

            top_10_hands = db.query(
                HandSummary.hand_number,
                HandSummary.pot_size,
                HandSummary.winner_name,
                HandSummary.board_cards,
                HandSummary.started_at,
                HandSummary.ended_at
            ).filter(
                HandSummary.session_id == session.id,
                HandSummary.pot_size.isnot(None)
            ).order_by(
                HandSummary.pot_size.desc()
            ).limit(10).all()

            hand_replays = []
            for hand in top_10_hands:
                events = db.query(
                    PokerEvent.event_type,
                    PokerEvent.player_name,
                    PokerEvent.amount,
                    PokerEvent.cards,
                    PokerEvent.event_timestamp,
                    PokerEvent.raw_entry,
                    PokerEvent.order_number
                ).filter(
                    PokerEvent.session_id == session.id,
                    PokerEvent.hand_number == hand.hand_number
                ).order_by(
                    PokerEvent.order_number.asc().nulls_last()
                ).all()

                action_log = []
                seen_hand_end = False
                for event in events:
                    if event.event_type == 'hand_end':
                        seen_hand_end = True
                        continue
                    elif event.event_type == 'hand_start' and not seen_hand_end:
                        action_log.append(f"-- Starting Hand #{hand.hand_number} --")
                    elif event.event_type == 'hand_start' and seen_hand_end:
                        continue
                    elif event.event_type == 'bet':
                        action_log.append(f"{event.player_name} bets ${event.amount / 100:.2f}")
                    elif event.event_type == 'call':
                        action_log.append(f"{event.player_name} calls ${event.amount / 100:.2f}")
                    elif event.event_type == 'fold':
                        action_log.append(f"{event.player_name} folds")
                    elif event.event_type == 'check':
                        action_log.append(f"{event.player_name} checks")
                    elif event.event_type == 'collected':
                        action_log.append(f"{event.player_name} collected ${event.amount / 100:.2f} from pot")
                    elif event.event_type == 'shows':
                        action_log.append(f"{event.player_name} shows {event.cards}")
                    elif event.event_type == 'flop':
                        action_log.append(f"Flop: {event.cards}")
                    elif event.event_type == 'turn':
                        action_log.append(f"Turn: {event.cards}")
                    elif event.event_type == 'river':
                        action_log.append(f"River: {event.cards}")
                    elif event.event_type == 'unknown':
                        continue

                hand_replays.append({
                    'hand_number': hand.hand_number,
                    'pot_size': hand.pot_size or 0,
                    'winner_name': hand.winner_name,
                    'board_cards': hand.board_cards,
                    'action_log': action_log
                })

            session_analytics.append({
                'session_id': str(session.id),
                'session_number': session.game_number,
                'date': session.started_at.strftime('%b %d, %Y') if session.started_at else 'Unknown',
                'total_actions': session.total_actions,
                'duration_hours': duration_hours,
                'total_hands': session.total_hands,
                'hands_per_hour': hands_per_hour,
                'active_players': session.active_players,
                'top_winners': top_winners_formatted,
                'top_10_hands': hand_replays
            })

        return {
            'sessions': session_analytics,
            'total_sessions_with_hand_data': len(session_analytics),
            'total_sessions_in_game': total_sessions_in_game
        }