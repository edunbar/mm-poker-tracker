#!/usr/bin/env python3
"""
Merge Duplicate Players Script

Finds and merges duplicate players (same display name, case-insensitive) within games.
This happens when:
- PokerNow returns different capitalization for external_id (e.g., "lw0lJXpCtc" vs "lw0lJXpCtC")
- Same player joins as guest instead of logged-in account (different external_ids)
- Case-sensitive matching creates unnecessary duplicates

The script automatically:
1. Groups players by display name (case-insensitive) within each game
2. Selects the "keeper" (player with most sessions, or earliest created if tied)
3. Merges all other duplicates into the keeper
4. Preserves all session data and payment history

Usage:
    # Dry run (shows what would be merged, no changes)
    PYTHONPATH=src python merge_duplicate_players.py --dry-run

    # Fix specific game
    PYTHONPATH=src python merge_duplicate_players.py --game-code C4QRO

    # Fix all games
    PYTHONPATH=src python merge_duplicate_players.py
"""

import argparse
import sys
from collections import defaultdict
from datetime import datetime
from typing import List, Dict, Optional, Tuple

from sqlalchemy import func
from db.database import SessionLocal
from db.models import Game, Player, SessionPlayerSummary, Session
from services.player_merge_service_v2 import PlayerMergeServiceV2


def find_duplicates_in_game(db, game_id: str) -> Dict[str, List[Dict]]:
    """
    Find duplicate players (same display name) in a game.

    Returns:
        Dictionary mapping normalized display name to list of player records:
        {
            'remy': [
                {'id': '...', 'display_name': 'Remy', 'external_id': '...', 'num_sessions': 23, ...},
                {'id': '...', 'display_name': 'REMY', 'external_id': '...', 'num_sessions': 1, ...}
            ]
        }
    """
    # Query all players in this game with session counts
    players_query = (
        db.query(
            Player.id,
            Player.display_name,
            Player.external_id,
            Player.created_at,
            func.count(SessionPlayerSummary.session_id).label('num_sessions')
        )
        .join(SessionPlayerSummary, Player.id == SessionPlayerSummary.player_id)
        .join(Session, SessionPlayerSummary.session_id == Session.id)
        .filter(Session.game_id == game_id)
        .group_by(Player.id, Player.display_name, Player.external_id, Player.created_at)
        .order_by(Player.display_name, Player.created_at)
        .all()
    )

    # Group by normalized display name
    groups = defaultdict(list)
    for player in players_query:
        normalized_name = player.display_name.lower().strip()
        groups[normalized_name].append({
            'id': str(player.id),
            'display_name': player.display_name,
            'external_id': player.external_id,
            'created_at': player.created_at,
            'num_sessions': player.num_sessions
        })

    # Filter to only groups with duplicates (count > 1)
    duplicates = {name: players for name, players in groups.items() if len(players) > 1}

    return duplicates


def select_keeper_and_sources(duplicates: List[Dict]) -> Tuple[Dict, List[Dict]]:
    """
    Select which player to keep and which to merge.

    Strategy:
    - Keep player with most sessions
    - If tied, keep earliest created
    - Merge all others into keeper

    Returns:
        (keeper_player, source_players_list)
    """
    # Sort by: num_sessions DESC, created_at ASC
    sorted_players = sorted(
        duplicates,
        key=lambda p: (-p['num_sessions'], p['created_at'])
    )

    keeper = sorted_players[0]
    sources = sorted_players[1:]

    return keeper, sources


def merge_duplicate_players(game_code: Optional[str] = None, dry_run: bool = True):
    """
    Find and merge duplicate players in games.

    Args:
        game_code: If provided, only process this game. Otherwise process all games.
        dry_run: If True, only show what would be merged without making changes.
    """
    with SessionLocal() as db:
        # Get games to process
        if game_code:
            games = db.query(Game).filter(Game.public_code == game_code).all()
            if not games:
                print(f"ERROR: Game with code '{game_code}' not found")
                return
        else:
            games = db.query(Game).all()

        print(f"\n{'='*80}")
        print(f"Mode: {'DRY RUN (no changes will be made)' if dry_run else 'LIVE MERGE'}")
        print(f"Games to process: {len(games)}")
        print(f"{'='*80}\n")

        total_duplicate_sets = 0
        total_merges = 0

        for game in games:
            print(f"\nProcessing game: {game.title or game.public_code} ({game.public_code})")
            print(f"-" * 80)

            # Find duplicates in this game
            duplicates = find_duplicates_in_game(db, game.id)

            if not duplicates:
                print("  No duplicate players found")
                continue

            print(f"  Found {len(duplicates)} duplicate set(s):\n")
            total_duplicate_sets += len(duplicates)

            for name, players in duplicates.items():
                # Select keeper and sources
                keeper, sources = select_keeper_and_sources(players)

                print(f"  Duplicate set: \"{keeper['display_name']}\" ({len(players)} players)")
                print(f"    KEEP:   {keeper['id'][:8]} (external_id: {keeper['external_id']}) - {keeper['num_sessions']} sessions, created {keeper['created_at']}")

                for source in sources:
                    print(f"    MERGE:  {source['id'][:8]} (external_id: {source['external_id']}) - {source['num_sessions']} sessions, created {source['created_at']}")

                print(f"    Action: Merge {sum(s['num_sessions'] for s in sources)} session(s) into keeper")

                if not dry_run:
                    # Execute merge
                    try:
                        # Determine external_id to use:
                        # - If all players have EXACTLY the same external_id (case-sensitive), use it
                        # - Otherwise, pass None and let merge service handle it (will keep keeper's)
                        all_external_ids = [keeper['external_id']] + [s['external_id'] for s in sources if s['external_id']]
                        unique_external_ids = set(eid for eid in all_external_ids if eid)

                        if len(unique_external_ids) == 1:
                            # All exactly the same - safe to use
                            merge_external_id = keeper['external_id']
                        else:
                            # Different external_ids (including case-only differences)
                            # Pass None so merge service doesn't validate, keeper's will be inherited
                            merge_external_id = None
                            if len(unique_external_ids) > 1:
                                print(f"    Note: Different external_ids detected, keeper's will be used")

                        merge_service = PlayerMergeServiceV2(db)
                        result = merge_service.merge_players(
                            target_player_id=keeper['id'],
                            source_player_ids=[s['id'] for s in sources],
                            verified_name=keeper['display_name'],
                            external_id=merge_external_id,
                            game_id=str(game.id)
                        )
                        print(f"    ✓ Successfully merged {len(sources)} player(s)")
                        total_merges += len(sources)
                        db.commit()
                    except Exception as e:
                        print(f"    ✗ ERROR: Failed to merge: {e}")
                        db.rollback()
                else:
                    print(f"    ✓ Would merge {len(sources)} player(s) (dry run)")
                    total_merges += len(sources)

                print()

        print(f"\n{'='*80}")
        print(f"Summary:")
        print(f"  Duplicate sets found: {total_duplicate_sets}")
        print(f"  Players {'merged' if not dry_run else 'to merge'}: {total_merges}")
        if dry_run:
            print(f"\n  NOTE: This was a dry run. No changes were made.")
            print(f"        Run without --dry-run to apply changes.")
        print(f"{'='*80}\n")


def main():
    parser = argparse.ArgumentParser(
        description='Merge duplicate players (same display name) within games'
    )
    parser.add_argument(
        '--game-code',
        type=str,
        help='Only process this specific game code (e.g., C4QRO)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        default=False,
        help='Show what would be merged without making changes'
    )

    args = parser.parse_args()

    try:
        merge_duplicate_players(
            game_code=args.game_code,
            dry_run=args.dry_run
        )
    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
