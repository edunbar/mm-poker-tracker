#!/usr/bin/env python3
"""
Simple comparison to understand the mapping between local ledger and database.
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

def get_db_sessions_overview(public_code: str):
    """Get a simple overview of what's in the database."""
    with SessionLocal() as db:
        # Get game
        game = db.execute(
            select(Game).where(Game.public_code == public_code)
        ).scalar_one_or_none()
        
        if not game:
            print(f"Game with public code '{public_code}' not found")
            return
        
        print(f"Game ID: {game.id}")
        print(f"Game Title: {game.title}")
        print(f"Public Code: {game.public_code}")
        print()
        
        # Get all sessions
        sessions = db.execute(
            select(Session)
            .where(Session.game_id == game.id)
            .order_by(Session.game_number)
        ).scalars().all()
        
        print(f"Total sessions in DB: {len(sessions)}")
        
        # Show first 10 sessions
        print("\nFirst 10 sessions:")
        for i, session in enumerate(sessions[:10]):
            print(f"  Session {i+1}: Game #{session.game_number}, External ID: {session.external_id}")
            
            # Get summaries for this session
            summaries = db.execute(
                select(SessionPlayerSummary)
                .where(SessionPlayerSummary.session_id == session.id)
                .options(joinedload(SessionPlayerSummary.player))
            ).scalars().unique().all()
            
            for summary in summaries:
                buy_in_dollars = Decimal(summary.buy_in_sum) / 100
                cash_out_dollars = Decimal(summary.cash_out_sum) / 100
                print(f"    {summary.player.display_name}: ${buy_in_dollars} -> ${cash_out_dollars}")
            print()

def parse_local_first_games():
    """Parse and show the first few games from local data."""
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
3    Zack    20.00    27.88"""
    
    print("First 3 games from local data:")
    lines = local_ledger_text.strip().split('\n')
    for line in lines:
        if line.strip():
            parts = line.strip().split()
            if len(parts) >= 4:
                game_num = int(parts[0])
                player_name = parts[1]
                buy_in = Decimal(parts[2])
                cash_out = Decimal(parts[3])
                print(f"  Game {game_num}: {player_name}: ${buy_in} -> ${cash_out}")

def main():
    if len(sys.argv) != 2:
        print("Usage: python simple_comparison.py <public_code>")
        sys.exit(1)
    
    public_code = sys.argv[1]
    
    print("=== LOCAL LEDGER DATA ===")
    parse_local_first_games()
    print()
    
    print("=== DATABASE DATA ===")
    get_db_sessions_overview(public_code)

if __name__ == "__main__":
    main()