#!/usr/bin/env python3
"""
Compare local ledger data with database values to identify discrepancies.
"""

import sys
import os
from decimal import Decimal
from typing import Dict, List, Tuple, Any
from collections import defaultdict

# Add the src directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from db.database import SessionLocal
from db.models import Game, Session, SessionPlayerSummary, Player
from sqlalchemy import select
from sqlalchemy.orm import joinedload

def parse_local_ledger_data(data_text: str) -> Dict[int, Dict[str, Tuple[Decimal, Decimal]]]:
    """
    Parse the local ledger data into a structured format.
    Returns: {game_number: {player_name: (buy_in, cash_out)}}
    """
    ledger_data = defaultdict(dict)
    
    lines = data_text.strip().split('\n')
    for line in lines:
        if not line.strip():
            continue
            
        parts = line.strip().split('\t')
        if len(parts) < 4:
            # Try space-separated if tab-separated doesn't work
            parts = line.strip().split()
            
        if len(parts) >= 4:
            try:
                game_num = int(parts[0])
                player_name = parts[1]
                buy_in = Decimal(parts[2])
                cash_out = Decimal(parts[3])
                
                ledger_data[game_num][player_name] = (buy_in, cash_out)
            except (ValueError, IndexError) as e:
                print(f"Error parsing line: {line} - {e}")
                continue
    
    return dict(ledger_data)

def get_db_data(public_code: str) -> Dict[int, Dict[str, Tuple[Decimal, Decimal]]]:
    """
    Get session data from database.
    Returns: {game_number: {player_name: (buy_in_dollars, cash_out_dollars)}}
    """
    db_data = defaultdict(dict)
    
    with SessionLocal() as db:
        # Get game
        game = db.execute(
            select(Game).where(Game.public_code == public_code)
        ).scalar_one_or_none()
        
        if not game:
            print(f"Game with public code '{public_code}' not found")
            return dict(db_data)
        
        # Get all sessions with player summaries
        sessions = db.execute(
            select(Session)
            .where(Session.game_id == game.id)
            .options(
                joinedload(Session.summaries).joinedload(SessionPlayerSummary.player)
            )
            .order_by(Session.game_number)
        ).scalars().unique().all()
        
        for session in sessions:
            game_number = session.game_number
            if not game_number:
                continue
                
            for summary in session.summaries:
                player_name = summary.player.display_name
                # Convert cents to dollars
                buy_in_dollars = Decimal(summary.buy_in_sum) / 100
                cash_out_dollars = Decimal(summary.cash_out_sum) / 100
                
                db_data[game_number][player_name] = (buy_in_dollars, cash_out_dollars)
    
    return dict(db_data)

def compare_data(local_data: Dict, db_data: Dict) -> List[Dict[str, Any]]:
    """
    Compare local and database data, return list of discrepancies.
    """
    discrepancies = []
    
    # Get all game numbers from both datasets
    all_games = set(local_data.keys()) | set(db_data.keys())
    
    for game_num in sorted(all_games):
        local_game = local_data.get(game_num, {})
        db_game = db_data.get(game_num, {})
        
        # Games only in local data
        if game_num not in db_data:
            discrepancies.append({
                'type': 'missing_from_db',
                'game_number': game_num,
                'message': f"Game {game_num} exists in local data but not in database",
                'local_players': len(local_game),
                'db_players': 0
            })
            continue
        
        # Games only in DB
        if game_num not in local_data:
            discrepancies.append({
                'type': 'missing_from_local',
                'game_number': game_num,
                'message': f"Game {game_num} exists in database but not in local data",
                'local_players': 0,
                'db_players': len(db_game)
            })
            continue
        
        # Compare players in this game
        all_players = set(local_game.keys()) | set(db_game.keys())
        
        for player_name in sorted(all_players):
            local_values = local_game.get(player_name)
            db_values = db_game.get(player_name)
            
            # Player only in local data
            if player_name not in db_game:
                discrepancies.append({
                    'type': 'player_missing_from_db',
                    'game_number': game_num,
                    'player_name': player_name,
                    'message': f"Game {game_num}: Player '{player_name}' in local data but not in database",
                    'local_buy_in': local_values[0] if local_values else 0,
                    'local_cash_out': local_values[1] if local_values else 0,
                    'db_buy_in': None,
                    'db_cash_out': None
                })
                continue
            
            # Player only in DB
            if player_name not in local_game:
                discrepancies.append({
                    'type': 'player_missing_from_local',
                    'game_number': game_num,
                    'player_name': player_name,
                    'message': f"Game {game_num}: Player '{player_name}' in database but not in local data",
                    'local_buy_in': None,
                    'local_cash_out': None,
                    'db_buy_in': db_values[0] if db_values else 0,
                    'db_cash_out': db_values[1] if db_values else 0
                })
                continue
            
            # Compare values
            local_buy_in, local_cash_out = local_values
            db_buy_in, db_cash_out = db_values
            
            buy_in_diff = abs(local_buy_in - db_buy_in)
            cash_out_diff = abs(local_cash_out - db_cash_out)
            
            # Allow for small rounding differences (1 cent)
            if buy_in_diff > Decimal('0.01') or cash_out_diff > Decimal('0.01'):
                discrepancies.append({
                    'type': 'value_mismatch',
                    'game_number': game_num,
                    'player_name': player_name,
                    'message': f"Game {game_num}: '{player_name}' has different values",
                    'local_buy_in': local_buy_in,
                    'local_cash_out': local_cash_out,
                    'db_buy_in': db_buy_in,
                    'db_cash_out': db_cash_out,
                    'buy_in_diff': buy_in_diff,
                    'cash_out_diff': cash_out_diff
                })
    
    return discrepancies

def print_summary_stats(local_data: Dict, db_data: Dict):
    """Print summary statistics for comparison."""
    local_games = len(local_data)
    db_games = len(db_data)
    
    local_total_entries = sum(len(game) for game in local_data.values())
    db_total_entries = sum(len(game) for game in db_data.values())
    
    print(f"\n=== SUMMARY STATISTICS ===")
    print(f"Local data: {local_games} games, {local_total_entries} player entries")
    print(f"Database:   {db_games} games, {db_total_entries} player entries")
    print(f"Game count difference: {db_games - local_games}")
    print(f"Entry count difference: {db_total_entries - local_total_entries}")

def main():
    if len(sys.argv) != 2:
        print("Usage: python compare_ledger_data.py <public_code>")
        sys.exit(1)
    
    public_code = sys.argv[1]
    
    # Your local ledger data (paste it here)
    local_ledger_text = """1    Eric    40.00    0.00    
1    Grant    60.00    116.11    
1    Jake    20.00    54.99    
1    Max    20.00    24.79    
1    Sturt    20.00    24.11    
1    Tomo    60.00    0.00    
2    Eric    60.00    0.00    
2    Fiona    20.00    0.00    
2    Grant    40.00    164.60    
2    Jack    20.00    48.30    
2    Jake    20.00    108.50    
2    Luke    60.00    0.00    
2    Max    60.00    0.00    
2    Sturt    20.00    0.00    
2    Tomo    80.00    58.60    
3    Grant    40.00    14.54    
3    Jake    20.00    0.00    
3    Max    20.00    41.30    
3    Tomo    20.00    36.28    
3    Zack    20.00    27.88    
4    Cade    20.00    0.00    
4    Eric    20.00    0.00    
4    Jack    20.00    180.00    
4    Jake    20.00    0.00    
4    Marshall    20.00    0.00    
4    Max    20.00    0.00    
4    Sturt    20.00    0.00    
4    Tomo    40.00    0.00    
5    Eric    20.00    26.40    
5    Grant    60.00    0.00    
5    Jack    20.00    38.23    
5    Jake    20.00    39.00    
5    Sturt    20.00    0.00    
5    Tomo    40.00    76.37    
6    Grant    20.00    73.47    
6    Jake    40.00    0.00    
6    Luke    20.00    55.91    
6    Max    60.00    0.00    
6    Nuck    20.00    0.00    
6    Tomo    20.00    50.62    
7    Eric    20.00    87.10    
7    Fiona    20.00    21.47    
7    Grant    20.00    29.76    
7    Luke    20.00    53.12    
7    Max    20.00    0.00    
7    Sturt    20.00    0.00    
7    Tomo    80.00    8.55    
8    Casey    40.00    15.40    
8    Eric    20.00    0.00    
8    Fiona    20.00    9.94    
8    Grant    20.00    161.55    
8    Jack    100.00    19.26    
8    Jake    20.00    0.00    
8    Luke    40.00    22.55    
8    Max    40.00    19.61    
8    Nuck    20.00    93.38    
8    Sturt    20.00    14.64    
8    Tomo    40.00    23.67    
9    Casey    20.00    31.97    
9    Eric    20.00    61.99    
9    Grant    60.00    145.90    
9    Jack    40.00    0.00    
9    Luke    20.00    20.14    
9    Max    20.00    0.00    
9    OV    40.00    0.00    
9    Sturt    20.00    0.00    
9    Tomo    20.00    0.00    
10    Eric    40.00    70.40    
10    Grant    60.00    0.00    
10    Jack    40.00    0.00    
10    Max    60.00    141.80    
10    Tomo    60.00    47.80    
11    Cade    40.00    0.00    
11    Eric    20.00    55.70    
11    Fiona    80.00    66.71    
11    Max    20.00    97.59    
11    Tomo    60.00    0.00    
12    Eric    20.00    0.00    
12    Grant    60.00    0.00    
12    Jack    40.00    0.00    
12    Max    20.00    167.38    
12    Sturt    40.00    32.62    
12    Tomo    20.00    0.00    
13    Eric    60.00    0.00    
13    Jack    60.00    0.00    
13    Max    80.00    133.14    
13    Sturt    20.00    0.00    
13    Tomo    40.00    126.86    
14    Cade    20.00    9.94    
14    Casey    20.00    0.00    
14    Fiona    20.00    0.00    
14    Max    20.00    53.18    
14    Sturt    40.00    0.00    
14    Tomo    20.00    76.88    
15    Birday    40.00    0.00    
15    Eric    20.00    0.00    
15    Fiona    20.00    0.00    
15    Jake    20.00    62.40    
15    Sturt    60.00    84.82    
15    Tomo    40.00    52.78    
16    Casey    20.00    0.00    
16    Eric    20.00    49.75    
16    Jake    40.00    74.16    
16    Max    20.00    19.26    
16    Nuck    40.00    28.49    
16    Sturt    20.00    48.34    
16    Tomo    60.00    0.00    
17    Jake    40.00    0.00    
17    Max    20.00    99.63    
17    Sturt    20.00    87.43    
17    Tomo    80.00    0.00    
17    Zack    100.00    72.94    
18    Casey    20.00    0.00    
18    Eric    60.00    117.71    
18    Fiona    20.00    51.26    
18    Max    20.00    0.00    
18    Sturt    60.00    51.03    
18    Tomo    40.00    0.00    
19    Casey    40.00    34.41    
19    Eric    100.00    0.00    
19    Fiona    40.00    18.69    
19    Grant    60.00    91.71    
19    Max    80.00    98.42    
19    Nuck    20.00    114.98    
19    Sturt    40.00    52.76    
19    Tomo    40.00    9.03    
20    Casey    40.00    52.94    
20    Eric    60.00    0.00    
20    Grant    40.00    73.53    
20    Jack    40.00    0.00    
20    Jake    40.00    59.90    
20    Max    40.00    26.76    
20    Nuck    20.00    45.33    
20    Sturt    60.00    71.52    
20    Tomo    20.00    70.02    
20    Zack    40.00    0.00    
21    Casey    20.00    51.66    
21    Eric    60.00    0.00    
21    Jack    20.00    0.00    
21    Jake    40.00    0.00    
21    Max    20.00    76.65    
21    Sturt    20.00    47.07    
21    Tomo    100.00    124.62    
21    Zack    20.00    0.00    
22    Grant    20.00    105.75    
22    Jack    40.00    0.00    
22    Max    120.00    0.00    
22    Nuck    20.00    91.07    
22    Tomo    80.00    83.18    
23    Jack    20.00    37.92    
23    Nuck    20.00    27.63    
23    Sturt    40.00    54.45    
23    Tomo    40.00    0.00    
24    Birday    20.00    0.00    
24    Casey    20.00    55.38    
24    Eric    20.00    0.00    
24    Fiona    40.00    0.00    
24    Grant    20.00    102.29    
24    Max    40.00    0.00    
24    Nuck    60.00    59.95    
24    Rex    20.00    21.62    
24    Sturt    40.00    0.00    
24    Tomo    40.00    75.10    
24    Zack    20.00    25.66    
25    Casey    20.00    0.00    
25    Eric    20.00    0.00    
25    Fiona    20.00    34.99    
25    Grant    40.00    36.75    
25    Jack    40.00    69.59    
25    Jake    40.00    80.11    
25    Max    80.00    35.61    
25    Remy    20.00    0.00    
25    Sturt    60.00    202.95    
25    Tomo    120.00    0.00    
26    Casey    40.00    7.51    
26    Eric    20.00    18.19    
26    Fiona    20.00    32.65    
26    Sturt    20.00    61.65    
26    Tomo    20.00    0.00    
27    Andrew    100.00    0.00    
27    Casey    80.00    128.20    
27    Eric    20.00    23.23    
27    Grant    20.00    130.49    
27    Jack    40.00    0.00    
27    Sturt    20.00    0.00    
27    Tomo    40.00    0.00    
27    Zack    80.00    118.08    
28    Andrew    40.00    95.13    
28    Cade    40.00    20.96    
28    Casey    40.00    102.94    
28    Eric    60.00    54.84    
28    Fiona    40.00    0.00    
28    Grant    20.00    0.00    
28    Jack    40.00    0.00    
28    Luke    20.00    18.95    
28    Nuck    60.00    0.00    
28    Sturt    40.00    0.00    
28    Tomo    20.00    127.18    
29    Max    40.00    0.00    
29    Sturt    20.00    0.00    
29    Tomo    20.00    0.00    
29    Zack    40.00    120.00    
30    Andrew    20.00    125.77    
30    Eric    20.00    67.14    
30    Fiona    20.00    69.99    
30    Grant    60.00    0.00    
30    Jack    20.00    8.23    
30    Jake    20.00    0.00    
30    Max    20.00    0.00    
30    Remy    20.00    0.00    
30    Sturt    20.00    0.00    
30    Tomo    60.00    27.32    
30    Zack    60.00    41.55    
31    Andrew    20.00    0.00    
31    Sturt    40.00    37.76    
31    Tomo    20.00    113.66    
31    Zack    20.00    32.04    
31    Max    60.00    0.00    
31    Eric    40.00    19.07    
31    Fiona    20.00    17.47    
32    Tomo    80.00    20.00    
32    Eric    40.00    81.50    
32    Zack    160.00    38.20    
32    Casey    40.00    0.00    
32    Jack    40.00    24.08    
32    Birday    40.00    70.01    
32    Nuck    40.00    181.81    
32    Max    80.00    186.70    
32    Remy    40.00    0.00    
32    Sturt    160.00    117.70    
33    Zack    40.00    117.72    
33    Tomo    40.00    44.46    
33    Andrew    40.00    36.90    
33    Fiona    40.00    0.00    
33    Casey    40.00    40.92    
33    Sturt    40.00    0.00    
34    Eric    40.00    0.00    
34    Tomo    40.00    105.68    
34    Max    40.00    46.55    
34    Jack    40.00    0.00    
34    Sturt    40.00    47.77    
35    Casey    40.00    20.25    
35    Tomo    40.00    60.95    
35    Marshall    20.00    37.89    
35    Cade    20.00    0.00    
35    Sturt    20.00    20.91    
36    Jack    40.00    83.44    
36    Grant    120.00    114.79    
36    Max    200.00    91.14    
36    Eric    40.00    190.63    
36    Tomo    40.00    0.00    
36    Sturt    40.00    0.00    
37    Eric    40.00    107.21    
37    Tomo    40.00    64.52    
37    Casey    80.00    120.51    
37    Nuck    80.00    0.00    
37    Max    80.00    86.75    
37    Sturt    40.00    0.00    
37    Zack    80.00    141.01    
37    Grant    80.00    0.00    
38    Eric    40.00    167.15    
38    Tomo    40.00    140.04    
38    Zack    120.00    173.53    
38    Birday    40.00    91.43    
38    Grant    40.00    90.82    
38    Casey    80.00    70.27    
38    Nuck    40.00    0.00    
38    Andrew    110.00    0.00    
38    Max    320.00    96.76    
39    Nuck    40.00    33.71    
39    Eric    40.00    171.97    
39    Zack    40.00    0.00    
39    Casey    40.00    37.70    
39    Remy    40.00    126.36    
39    Max    120.00    0.00    
39    Tomo    120.00    0.00    
39    Jack    40.00    87.65    
39    Luke    40.00    0.00    
39    Sturt    40.00    102.61    
40    Sturt    40.00    0.00    
40    Tomo    40.00    61.95    
40    Jack    40.00    33.06    
40    Max    80.00    182.96    
40    Eric    40.00    133.09    
40    Casey    160.00    68.94    
40    Zack    80.00    0.00    
41    Nuck    40.00    192.39    
41    Jack    40.00    104.29    
41    Sturt    80.00    59.61    
41    Eric    40.00    0.00    
41    Remy    80.00    39.82    
41    Max    120.00    56.19    
41    Tomo    160.00    0.00    
41    Zack    40.00    147.70    
42    Tomo    5.00    20.00    
42    Max    5.00    0.00    
42    Nuck    5.00    0.00    
42    Luke    5.00    0.00    
43    Max    80.00    243.40    
43    Sturt    40.00    135.00    
43    Jack    80.00    122.62    
43    Eric    80.00    98.98    
43    Remy    40.00    0.00    
43    Nuck    80.00    0.00    
43    Zack    80.00    0.00    
43    Tomo    120.00    0.00    
44    Andrew    40.00    522.61    
44    Jack    40.00    105.59    
44    Max    80.00    0.00    
44    Nuck    40.00    11.80    
44    Sturt    40.00    0.00    
44    Fiona    40.00    0.00    
44    Tomo    40.00    0.00    
44    Griff    120.00    0.00    
44    Zack    200.00    0.00    
45    Jack    80.00    295.98    
45    Casey    40.00    137.66    
45    Tomo    40.00    128.02    
45    Zack    40.00    95.70    
45    Nuck    40.00    0.00    
45    Sturt    120.00    0.00    
45    Max    240.00    194.06    
45    Remy    120.00    27.29    
45    Eric    160.00    0.00    
45    Andrew    40.00    41.29    
46    Eric    40.00    116.92    
46    Max    80.00    135.14    
46    Casey    40.00    83.70    
46    Sturt    40.00    79.82    
46    Remy    80.00    95.22    
46    Trevor    80.00    90.58    
46    Fiona    40.00    38.62    
46    Cade    40.00    0.00    
46    Zack    40.00    0.00    
46    Tomo    160.00    0.00    
47    Trevor    40.00    71.22    
47    Jack    40.00    58.96    
47    Andrew    40.00    37.23    
47    Tomo    40.00    32.59    
47    Casey    40.00    0.00    
48    Cade    20.00    69.82    
48    Fiona    20.00    69.82    
48    Jake    80.00    123.59    
48    Eric    40.00    80.09    
48    Casey    40.00    70.92    
48    Max    80.00    109.47    
48    Zack    40.00    0.00    
48    Tomo    80.00    36.29    
48    Remy    80.00    0.00    
48    Sturt    80.00    0.00    
49    Max    40.00    280.00    
49    Nuck    80.00    0.00    
49    Fiona    40.00    0.00    
49    Sturt    40.00    0.00    
49    Eric    40.00    0.00    
49    Casey    40.00    0.00    
50    Eric    80.00    204.45    
50    Andrew    40.00    120.57    
50    Remy    80.00    77.30    
50    Max    160.00    125.65    
50    Casey    80.00    64.02    
50    Tomo    120.00    102.30    
50    Jack    40.00    0.00    
50    Zack    240.00    145.71    
51    Nuck    80.00    174.28    
51    Remy    80.00    170.06    
51    Zack    200.00    250.00    
51    Max    40.00    31.29    
51    Eric    80.00    88.79    
51    Tomo    120.00    85.58    
51    Sturt    40.00    0.00    
51    Casey    80.00    0.00    
51    Jack    80.00    0.00    
52    Max    120.00    209.75    
52    Jack    40.00    113.89    
52    Tomo    160.00    119.46    
52    Casey    120.00    76.90    
52    Remy    80.00    0.00    
53    Max    160.00    285.70    
53    Casey    80.00    205.62    
53    Tomo    80.00    148.68    
53    Sturt    40.00    0.00    
53    Eric    80.00    0.00    
53    Nuck    80.00    0.00    
53    Jack    120.00    0.00    
54    Tomo    40.00    242.43    
54    Eric    80.00    188.16    
54    Casey    80.00    128.21    
54    Zack    120.00    168.00    
54    Grant    80.00    0.00    
54    Griff    200.00    107.11    
54    Max    320.00    86.09    
55    Trevor    240.00    404.88    
55    Zack    80.00    156.71    
55    Nuck    80.00    124.07    
55    Eric    80.00    103.04    
55    Grant    160.00    181.30    
55    Max    150.00    0.00    
55    Griff    180.00    0.00    
56    Max    290.00    473.16    
56    Trevor    80.00    246.93    
56    Grant    80.00    212.28    
56    Jack    40.00    90.07    
56    Casey    80.00    116.90    
56    Tomo    160.00    175.76    
56    Remy    120.00    14.90    
56    Griff    282.30    42.30    
56    Zack    240.00    0.00    
57    Casey    200.00    97.29    
57    Remy    80.00    0.00    
57    Tomo    200.00    0.00    
57    Andrew    120.00    116.25    
57    Nuck    120.00    0.00    
57    Zack    80.00    247.42    
57    Trevor    80.00    209.76    
57    Grant    140.00    61.23    
57    Jack    120.00    488.05    
57    Max    80.00    0.00    
58    Trevor    120.00    212.30    
58    Nuck    62.30    143.19    
58    Casey    40.00    114.30    
58    Zack    80.00    150.46    
58    Eric    40.00    77.33    
58    Grant    80.00    66.86    
58    Max    40.00    0.01    
58    Dylan    40.00    0.00    
58    Griff    40.00    0.00    
58    Andrew    148.42    98.40    
58    Remy    80.00    0.00    
58    Tomo    160.00    67.87    
59    Tomo    40.00    80.00    
59    Nuck    40.00    0.00    
60    Nuck    40.00    249.41    
60    Grant    80.00    276.53    
60    Max    40.00    166.06    
60    Zack    80.00    167.32    
60    Casey    120.00    101.09    
60    Eric    80.00    0.00    
60    Tomo    320.00    87.53    
60    Trevor    400.00    112.06    
61    Zack    120.00    712.03    
61    Trevor    40.00    143.78    
61    Jack    80.00    90.57    
61    Casey    140.00    33.62    
61    Grant    120.00    0.00    
61    Tomo    200.00    0.00    
61    Max    280.00    0.00    
62    Griff    80.00    249.88    
62    Jack    40.00    149.35    
62    Zack    220.00    244.95    
62    Casey    160.00    55.82    
62    Tomo    200.00    0.00    
63    Remy    40.00    351.18    
63    Trevor    80.00    332.59    
63    Jack    117.00    238.39    
63    Zack    200.00    289.17    
63    Tomo    280.00    322.67    
63    Griff    120.00    0.00    
63    Grant    160.00    0.00    
63    Casey    280.00    53.00    
63    Max    310.00    0.00    
64    Max    40.00    160.00    
64    Remy    40.00    0.00    
64    Nuck    40.00    0.00    
64    Tomo    40.00    0.00    
65    Griff    220.00    448.90    
65    Tomo    260.00    410.91    
65    Casey    100.00    197.65    
65    Eric    40.00    75.53    
65    Zack    110.00    108.01    
65    Nuck    80.00    0.00    
65    Remy    201.00    0.00    
65    Max    230.00    0.00    
66    Nuck    40.00    344.97    
66    Jack    40.00    337.65    
66    Zack    80.00    247.01    
66    Marshall    40.00    57.19    
66    Eric    80.00    53.18    
66    Max    40.00    0.00    
66    Tomo    40.00    0.00    
66    Remy    80.00    0.00    
66    Grant    120.00    0.00    
66    Griff    120.00    0.00    
66    Trevor    360.00    0.00    
67    Tomo    80.00    338.53    
67    Jack    120.00    137.50    
67    Fiona    40.00    43.97    
67    Eric    40.00    0.00    
67    Casey    40.00    0.00    
67    Remy    80.00    0.00    
67    Griff    120.00    0.00    
68    Max    80.00    253.70    
68    Sturt    40.00    150.65    
68    Trevor    40.00    122.66    
68    Nuck    40.00    118.92    
68    Grant    40.00    104.38    
68    Zack    80.00    79.80    
68    Casey    120.00    89.89    
68    Fiona    40.00    0.00    
68    Eric    40.00    0.00    
68    Remy    80.00    0.00    
68    Jack    160.00    0.00    
68    Tomo    160.00    0.00    
69    Tomo    40.00    188.80    
69    Casey    80.00    91.20    
69    Griff    40.00    0.00    
69    Max    40.00    0.00    
69    Sturt    40.00    0.00    
69    Eric    40.00    0.00    
70    Sturt    40.00    49.61    
70    Max    40.00    42.85    
70    Casey    40.00    27.54    
71    Nuck    120.00    245.20    
71    Tomo    260.00    313.99    
71    Eric    40.00    85.34    
71    Sturt    40.00    0.00    
71    Max    120.00    55.47    
71    Casey    120.00    0.00    
72    Tomo    120.00    715.71    
72    Max    120.00    400.79    
72    Grant    80.00    221.34    
72    Jim    80.00    57.08    
72    Sturt    40.00    0.00    
72    Jack    80.00    0.00    
72    Eric    100.00    0.00    
72    Nuck    160.00    0.00    
72    Casey    320.00    105.08    
72    Trevor    400.00    0.00    
73    Grant    160.00    294.11    
73    Eric    40.00    183.57    
73    Zack    102.82    108.23    
73    Sturt    160.00    129.49    
73    Casey    120.00    76.97    
73    Max    209.55    0.00    
74    Jack    40.00    537.21    
74    Trevor    80.00    201.96    
74    Casey    40.00    81.96    
74    Sturt    120.00    130.55    
74    Max    120.00    63.72    
74    Tomo    200.00    84.25    
74    Eric    120.00    0.00    
74    Zack    254.24    131.03    
74    Griff    280.00    23.56    
75    Trevor    160.00    371.17    
75    Nuck    40.00    177.46    
75    Eric    40.00    102.29    
75    Casey    160.00    215.54    
75    Tomo    80.00    0.00    
75    Grant    80.00    0.00    
75    Max    160.00    60.54    
75    Sturt    100.00    0.00    
75    Jack    107.00    0.00    
76    Nuck    40.00    319.11    
76    Max    422.38    609.99    
76    Grant    100.00    152.64    
76    Eric    120.00    0.00    
76    Casey    490.00    330.64    
76    Tomo    240.00    0.00    
77    Eric    40.00    75.53    
77    Trevor    40.00    47.07    
77    Casey    80.00    83.72    
77    Max    320.00    302.63    
77    Sturt    80.00    51.05    
78    Eric    80.00    312.86    
78    Grant    40.00    251.91    
78    Casey    80.00    107.76    
78    Sturt    40.00    0.00    
78    Trevor    160.00    47.61    
78    Max    600.00    279.86    
79    Nuck    40.00    258.99    
79    Max    40.00    224.48    
79    Fiona    40.00    95.96    
79    Sturt    10.00    51.08    
79    Casey    120.00    156.08    
79    Remy    80.00    68.00    
79    Eric    120.00    0.00    
79    Trevor    320.00    181.27    
79    Tomo    280.00    14.14    
80    Sturt    15.00    103.75    
80    Eric    40.00    106.94    
80    Nuck    80.00    141.00    
80    Casey    80.00    112.80    
80    Max    80.00    80.80    
80    Trevor    120.00    115.83    
80    Fiona    40.00    13.88    
80    Griff    100.00    0.00    
80    Tomo    120.00    0.00    
81    Casey    180.00    292.27    
81    Max    40.00    143.35    
81    Sturt    30.00    121.10    
81    Nuck    80.00    93.28    
81    Jack    80.00    40.00    
81    Eric    40.00    0.00    
81    Grant    120.00    0.00    
81    Tomo    120.00    0.00    
82    Casey    60.00    219.96    
82    Grant    60.00    157.15    
82    Nuck    60.00    64.36    
82    Max    45.00    34.45    
82    Eric    140.00    49.08    
82    Sturt    160.00    0.00    
83    Casey    50.00    120.55    
83    Nuck    50.00    93.65    
83    Sturt    20.00    0.00    
83    Trevor    100.00    55.80    
83    Sturt    50.00    0.00    
84    Max    50.00    157.78    
84    Sturt    80.00    134.16    
84    Nuck    40.00    117.01    
84    Eric    50.00    57.72    
84    Tomo    50.00    0.00    
84    Casey    170.00    73.33    
84    Trevor    150.00    50.00"""
    
    print("Parsing local ledger data...")
    local_data = parse_local_ledger_data(local_ledger_text)
    
    print("Fetching database data...")
    db_data = get_db_data(public_code)
    
    print("Comparing data...")
    discrepancies = compare_data(local_data, db_data)
    
    # Print summary
    print_summary_stats(local_data, db_data)
    
    # Print discrepancies
    if discrepancies:
        print(f"\n=== FOUND {len(discrepancies)} DISCREPANCIES ===")
        
        # Group by type
        by_type = defaultdict(list)
        for disc in discrepancies:
            by_type[disc['type']].append(disc)
        
        for disc_type, discs in by_type.items():
            print(f"\n--- {disc_type.upper().replace('_', ' ')} ({len(discs)} issues) ---")
            
            for disc in sorted(discs, key=lambda x: (x['game_number'], x.get('player_name', ''))):
                print(f"  Game {disc['game_number']}: {disc['message']}")
                
                if disc_type == 'value_mismatch':
                    print(f"    Local:  Buy-in=${disc['local_buy_in']:<8} Cash-out=${disc['local_cash_out']}")
                    print(f"    DB:     Buy-in=${disc['db_buy_in']:<8} Cash-out=${disc['db_cash_out']}")
                    print(f"    Diff:   Buy-in=${disc['buy_in_diff']:<8} Cash-out=${disc['cash_out_diff']}")
                elif disc_type in ['player_missing_from_db', 'player_missing_from_local']:
                    if disc['local_buy_in'] is not None:
                        print(f"    Local:  Buy-in=${disc['local_buy_in']:<8} Cash-out=${disc['local_cash_out']}")
                    if disc['db_buy_in'] is not None:
                        print(f"    DB:     Buy-in=${disc['db_buy_in']:<8} Cash-out=${disc['db_cash_out']}")
                
                print()
    else:
        print("\n🎉 NO DISCREPANCIES FOUND! Local data matches database perfectly.")

if __name__ == "__main__":
    main()