import csv
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from io import StringIO

class HandLogParser:

    EVENT_PATTERNS = {
        'hand_start': r'^-- starting hand #(\d+)',
        'hand_end': r'^-- ending hand #(\d+)',
        'bet': r'"([^"]+)" (bets|raises to) (\d+)',
        'fold': r'"([^"]+)" folds',
        'check': r'"([^"]+)" checks',
        'call': r'"([^"]+)" calls (\d+)',
        'collected': r'"([^"]+)" collected (\d+) from pot',
        'shows': r'"([^"]+)" shows (.+)',
        'flop': r'^Flop.*?: (.+)',
        'turn': r'^Turn.*?: (.+)',
        'river': r'^River.*?: (.+)',
    }

    @staticmethod
    def extract_player_name(player_string: str) -> Tuple[str, Optional[str]]:
        match = re.match(r'(.+?) @ ([a-zA-Z0-9]+)', player_string)
        if match:
            display_name = match.group(1).strip()
            external_id = match.group(2).strip()
            return display_name, external_id
        return player_string.strip(), None

    @staticmethod
    def parse_csv(csv_content: str) -> List[Dict]:
        events = []
        reader = csv.DictReader(StringIO(csv_content))

        for row in reader:
            entry = row.get('entry', '')
            at = row.get('at', '')
            order = row.get('order', '')

            try:
                timestamp = datetime.fromisoformat(at.replace('Z', '+00:00')) if at else None
            except (ValueError, AttributeError):
                timestamp = None

            try:
                order_num = int(order) if order else None
            except (ValueError, TypeError):
                order_num = None

            events.append({
                'entry': entry,
                'timestamp': timestamp,
                'order': order_num
            })

        return events

    @staticmethod
    def categorize_event(entry: str) -> Tuple[str, Dict]:
        for event_type, pattern in HandLogParser.EVENT_PATTERNS.items():
            match = re.search(pattern, entry, re.IGNORECASE)
            if match:
                data = {'raw_groups': match.groups()}

                if event_type == 'hand_start':
                    data['hand_number'] = int(match.group(1))
                elif event_type == 'hand_end':
                    data['hand_number'] = int(match.group(1))
                elif event_type in ['bet', 'call', 'collected']:
                    player_str = match.group(1)
                    display_name, external_id = HandLogParser.extract_player_name(player_str)
                    data['player_name'] = display_name
                    data['external_id'] = external_id
                    if event_type == 'bet':
                        data['amount'] = int(match.group(3))
                    elif event_type == 'call':
                        data['amount'] = int(match.group(2))
                    elif event_type == 'collected':
                        data['amount'] = int(match.group(2))
                elif event_type in ['fold', 'check', 'shows']:
                    player_str = match.group(1)
                    display_name, external_id = HandLogParser.extract_player_name(player_str)
                    data['player_name'] = display_name
                    data['external_id'] = external_id
                    if event_type == 'shows':
                        data['cards'] = match.group(2)
                elif event_type in ['flop', 'turn', 'river']:
                    data['cards'] = match.group(1)

                return event_type, data

        return 'unknown', {}

    @staticmethod
    def parse_hand_log(csv_content: str) -> Tuple[List[Dict], Dict]:
        raw_events = HandLogParser.parse_csv(csv_content)

        parsed_events = []
        current_hand = None
        hand_summaries = {}
        unmatched_players = set()

        for event in raw_events:
            entry = event['entry']
            event_type, data = HandLogParser.categorize_event(entry)

            if event_type == 'hand_start':
                current_hand = data['hand_number']
                hand_summaries[current_hand] = {
                    'hand_number': current_hand,
                    'started_at': event['timestamp'],
                    'events': [],
                    'board_cards': [],
                    'pot_size': 0,
                    'winner': None
                }

            parsed_event = {
                'hand_number': current_hand,
                'event_type': event_type,
                'player_name': data.get('player_name'),
                'external_id': data.get('external_id'),
                'amount': data.get('amount'),
                'cards': data.get('cards'),
                'event_timestamp': event['timestamp'],
                'order_number': event['order'],
                'raw_entry': entry
            }

            parsed_events.append(parsed_event)

            if current_hand and current_hand in hand_summaries:
                hand_summaries[current_hand]['events'].append(parsed_event)

                if event_type == 'collected':
                    hand_summaries[current_hand]['pot_size'] = data.get('amount', 0)
                    hand_summaries[current_hand]['winner'] = {
                        'name': data.get('player_name'),
                        'external_id': data.get('external_id')
                    }

                if event_type in ['flop', 'turn', 'river']:
                    hand_summaries[current_hand]['board_cards'].append(data.get('cards'))

                if event_type == 'hand_end':
                    hand_summaries[current_hand]['ended_at'] = event['timestamp']

            if data.get('player_name'):
                unmatched_players.add((data.get('player_name'), data.get('external_id')))

        return parsed_events, {
            'hand_summaries': list(hand_summaries.values()),
            'unmatched_players': list(unmatched_players),
            'total_hands': len(hand_summaries),
            'total_events': len(parsed_events)
        }