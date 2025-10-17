#!/usr/bin/env python3
"""
One-time script to clean up orphaned GamePlayer links.

An orphaned GamePlayer link exists when a player is linked to a game
but has no session_player_summaries in that game (ghost players).

This can happen when:
1. A session is deleted but the GamePlayer link persists
2. Test data is created and then removed

Run this script to clean up existing orphaned links.

Usage:
    python scripts/cleanup_orphaned_game_players.py [--dry-run]
"""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from sqlalchemy import text
from db.database import SessionLocal
from db.models import GamePlayer, SessionPlayerSummary, Session as SessionModel, Game, Player


def find_orphaned_game_players(db):
    """Find all orphaned GamePlayer links."""

    query = text("""
        SELECT
            gp.game_id,
            gp.player_id,
            g.public_code,
            g.title as game_title,
            p.display_name as player_name,
            p.external_id,
            gp.joined_at
        FROM game_players gp
        JOIN games g ON gp.game_id = g.id
        JOIN players p ON gp.player_id = p.id
        LEFT JOIN (
            SELECT DISTINCT sps.player_id, s.game_id
            FROM session_player_summaries sps
            JOIN sessions s ON sps.session_id = s.id
        ) active_sessions ON
            active_sessions.game_id = gp.game_id
            AND active_sessions.player_id = gp.player_id
        WHERE active_sessions.player_id IS NULL
        ORDER BY g.public_code, p.display_name
    """)

    result = db.execute(query)
    return result.fetchall()


def cleanup_orphaned_links(db, dry_run=True):
    """Clean up orphaned GamePlayer links."""

    orphaned = find_orphaned_game_players(db)

    if not orphaned:
        print("✅ No orphaned GamePlayer links found!")
        return

    print(f"\n🔍 Found {len(orphaned)} orphaned GamePlayer link(s):\n")

    for row in orphaned:
        print(f"  • Game: {row.public_code} ({row.game_title})")
        print(f"    Player: {row.player_name} (external_id: {row.external_id or 'None'})")
        print(f"    Joined: {row.joined_at}")
        print(f"    GamePlayer ID: game_id={row.game_id}, player_id={row.player_id}")
        print()

    if dry_run:
        print("🔵 DRY RUN MODE - No changes made")
        print("   Run with --execute flag to actually delete these links\n")
        return

    # Actually delete the orphaned links
    deleted_count = 0
    for row in orphaned:
        result = db.execute(
            text("""
                DELETE FROM game_players
                WHERE game_id = :game_id AND player_id = :player_id
            """),
            {"game_id": row.game_id, "player_id": row.player_id}
        )
        deleted_count += result.rowcount

    db.commit()

    print(f"✅ Deleted {deleted_count} orphaned GamePlayer link(s)\n")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Clean up orphaned GamePlayer links"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually delete orphaned links (default is dry-run)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompt (use with --execute)"
    )

    args = parser.parse_args()
    dry_run = not args.execute

    print("=" * 70)
    print("Orphaned GamePlayer Link Cleanup Script")
    print("=" * 70)

    if dry_run:
        print("\n⚠️  DRY RUN MODE - No changes will be made")
        print("   Use --execute flag to actually delete orphaned links\n")
    else:
        print("\n⚠️  EXECUTION MODE - Orphaned links will be DELETED")
        if not args.force:
            response = input("   Are you sure you want to continue? (yes/no): ")
            if response.lower() != "yes":
                print("\n❌ Aborted")
                return
        else:
            print("   --force flag detected, skipping confirmation")
        print()

    with SessionLocal() as db:
        cleanup_orphaned_links(db, dry_run=dry_run)

    print("=" * 70)
    print("Cleanup complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
