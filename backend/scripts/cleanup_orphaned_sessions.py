#!/usr/bin/env python3
"""
Manual cleanup script for orphaned sessions.
This script finds sessions that have no associated player summaries and removes them.
"""

import sys
import os

# Set up environment for local execution
if 'DATABASE_URL' not in os.environ:
    # Use localhost instead of 'db' for local execution
    os.environ['DATABASE_URL'] = 'postgresql+psycopg2://pokeruser:supersecret@localhost:5432/poker_analytics'

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from sqlalchemy import text
from db.database import SessionLocal
from db.models import Session, SessionPlayerSummary, Game

def find_orphaned_sessions():
    """Find sessions that have no associated player summaries."""
    with SessionLocal() as db:
        # Find sessions with no player summaries
        orphaned_sessions = db.execute(text("""
            SELECT s.id, s.game_id, s.external_id, s.game_number, g.public_code
            FROM sessions s
            JOIN games g ON s.game_id = g.id
            LEFT JOIN session_player_summaries sps ON s.id = sps.session_id
            WHERE sps.session_id IS NULL
        """)).fetchall()
        
        return orphaned_sessions

def cleanup_orphaned_sessions(dry_run=True):
    """Clean up orphaned sessions."""
    with SessionLocal() as db:
        orphaned = find_orphaned_sessions()
        
        if not orphaned:
            print("No orphaned sessions found.")
            return
        
        print(f"Found {len(orphaned)} orphaned sessions:")
        for session in orphaned:
            print(f"  - Game {session.public_code}, Session ID: {session.id}, Game Number: {session.game_number}, External ID: {session.external_id}")
        
        if dry_run:
            print("\nDry run mode - no changes made.")
            print("To actually delete these sessions, run with --confirm")
            return
        
        # Delete orphaned sessions
        for session in orphaned:
            db.execute(text("DELETE FROM sessions WHERE id = :session_id"), {"session_id": session.id})
            print(f"Deleted session {session.id} (Game {session.public_code}, Game Number: {session.game_number})")
        
        db.commit()
        print(f"\nCleaned up {len(orphaned)} orphaned sessions.")

def find_specific_game_number_sessions(game_number: int, public_code: str = None):
    """Find sessions with a specific game number."""
    with SessionLocal() as db:
        query = """
            SELECT s.id, s.game_id, s.external_id, s.game_number, g.public_code,
                   COUNT(sps.session_id) as player_count
            FROM sessions s
            JOIN games g ON s.game_id = g.id
            LEFT JOIN session_player_summaries sps ON s.id = sps.session_id
            WHERE s.game_number = :game_number
        """
        params = {"game_number": game_number}
        
        if public_code:
            query += " AND g.public_code = :public_code"
            params["public_code"] = public_code
            
        query += " GROUP BY s.id, s.game_id, s.external_id, s.game_number, g.public_code"
        
        sessions = db.execute(text(query), params).fetchall()
        return sessions

def delete_specific_session(session_id: str, dry_run=True):
    """Delete a specific session by ID."""
    with SessionLocal() as db:
        # Check if session exists and get info
        session_info = db.execute(text("""
            SELECT s.id, s.game_id, s.external_id, s.game_number, g.public_code,
                   COUNT(sps.session_id) as player_count
            FROM sessions s
            JOIN games g ON s.game_id = g.id
            LEFT JOIN session_player_summaries sps ON s.id = sps.session_id
            WHERE s.id = :session_id
            GROUP BY s.id, s.game_id, s.external_id, s.game_number, g.public_code
        """), {"session_id": session_id}).fetchone()
        
        if not session_info:
            print(f"Session {session_id} not found.")
            return
        
        print(f"Session details:")
        print(f"  - ID: {session_info.id}")
        print(f"  - Game: {session_info.public_code}")
        print(f"  - Game Number: {session_info.game_number}")
        print(f"  - External ID: {session_info.external_id}")
        print(f"  - Player Count: {session_info.player_count}")
        
        if dry_run:
            print("\nDry run mode - no changes made.")
            print("To actually delete this session, run with --confirm")
            return
        
        # Delete all player summaries first (if any)
        if session_info.player_count > 0:
            db.execute(text("DELETE FROM session_player_summaries WHERE session_id = :session_id"), 
                      {"session_id": session_id})
            print(f"Deleted {session_info.player_count} player summaries.")
        
        # Delete the session
        db.execute(text("DELETE FROM sessions WHERE id = :session_id"), {"session_id": session_id})
        db.commit()
        
        print(f"Successfully deleted session {session_id}.")

def check_in_game_amounts(public_code: str = "C4QROK"):
    """Check for in-game amounts that might explain discrepancies."""
    with SessionLocal() as db:
        result = db.execute(text("""
            SELECT 
                SUM(sps.in_game) as total_in_game_chips,
                ROUND(SUM(sps.in_game)/100.0, 2) as total_in_game_dollars,
                COUNT(*) as entries_with_in_game,
                SUM(sps.buy_in_sum) as total_buy_ins,
                SUM(sps.cash_out_sum) as total_cash_outs,
                SUM(sps.net) as total_net
            FROM sessions s
            JOIN session_player_summaries sps ON s.id = sps.session_id
            JOIN games g ON g.id = s.game_id
            WHERE g.public_code = :public_code
        """), {"public_code": public_code}).fetchone()
        
        if result:
            print(f"Game Summary Calculations for {public_code}:")
            print(f"  Total Buy-ins: ${result.total_buy_ins/100:.2f}")
            print(f"  Total Cash-outs: ${result.total_cash_outs/100:.2f}")
            print(f"  Total In-game: ${result.total_in_game_chips/100:.2f}")
            print(f"  Realized Net (cash-out - buy-in): ${(result.total_cash_outs - result.total_buy_ins)/100:.2f}")
            print(f"  Total Net (including in-game): ${result.total_net/100:.2f}")
            print(f"  Effective Balance: ${(result.total_cash_outs + result.total_in_game_chips - result.total_buy_ins)/100:.2f}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Clean up orphaned sessions")
    parser.add_argument("--confirm", action="store_true", help="Actually perform the cleanup (default is dry run)")
    parser.add_argument("--find-game-number", type=int, help="Find sessions with specific game number")
    parser.add_argument("--public-code", help="Filter by public code (use with --find-game-number)")
    parser.add_argument("--delete-session", help="Delete a specific session by ID")
    parser.add_argument("--check-amounts", action="store_true", help="Check in-game amounts")
    
    args = parser.parse_args()
    
    if args.check_amounts:
        check_in_game_amounts(args.public_code or "C4QROK")
    elif args.find_game_number:
        sessions = find_specific_game_number_sessions(args.find_game_number, args.public_code)
        if sessions:
            print(f"Found {len(sessions)} sessions with game number {args.find_game_number}:")
            for session in sessions:
                print(f"  - ID: {session.id}, Game: {session.public_code}, Players: {session.player_count}")
        else:
            print(f"No sessions found with game number {args.find_game_number}")
    elif args.delete_session:
        delete_specific_session(args.delete_session, dry_run=not args.confirm)
    else:
        cleanup_orphaned_sessions(dry_run=not args.confirm)