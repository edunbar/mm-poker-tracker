#!/usr/bin/env python3
"""
Seed test data for Player Identity Claims feature.

This script creates test users, games, players, and sample claims
for local development and testing of the Player Identity Claims functionality.
"""

import os
import sys
import base64
import secrets
from datetime import datetime, timezone

# Add the backend src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from db.database import SessionLocal
from db.models import User, Game, Player, GamePlayer, PokerIdentityClaim
from infrastructure.security.bcrypt_password_hasher import BcryptPasswordHasher


def short_code(n=6):
    """Generate short random code for public_code"""
    return base64.b32encode(secrets.token_bytes(n)).decode().strip("=").upper()[:n]


def long_token(nbytes=32):
    """Generate long random token for admin_code"""
    return secrets.token_urlsafe(nbytes)


def create_test_users(db, password_hasher):
    """Create test users with hashed passwords."""
    print("\n" + "=" * 60)
    print("CREATING TEST USERS")
    print("=" * 60)

    users = []
    test_password = "TestPassword123!"

    user_data = [
        {
            'email': 'testuser1@example.com',
            'display_name': 'Test User One'
        },
        {
            'email': 'testuser2@example.com',
            'display_name': 'Test User Two'
        }
    ]

    for data in user_data:
        # Check if user already exists
        existing = db.query(User).filter(User.email == data['email']).first()
        if existing:
            print(f"✓ User already exists: {data['email']}")
            users.append(existing)
            continue

        # Hash password using bcrypt
        hashed_password = password_hasher.hash(test_password)

        # Create user
        user = User(
            email=data['email'],
            password_hash=hashed_password,
            display_name=data['display_name'],
            email_verified=True
        )
        db.add(user)
        db.flush()  # Get the ID
        users.append(user)

        print(f"✓ Created user: {data['email']}")
        print(f"  Display Name: {data['display_name']}")
        print(f"  Password: {test_password}")

    return users


def create_test_game_with_players(db, public_code, title, player_names):
    """Create a game with players."""
    print(f"\n{'=' * 60}")
    print(f"CREATING GAME: {title}")
    print("=" * 60)

    # Check if game already exists
    existing_game = db.query(Game).filter(Game.public_code == public_code).first()
    if existing_game:
        print(f"✓ Game already exists: {public_code}")
        # Get existing players
        players = db.query(Player).join(GamePlayer).filter(
            GamePlayer.game_id == existing_game.id
        ).all()
        return existing_game, players

    # Create game
    game = Game(
        public_code=public_code,
        admin_code=long_token(32),
        title=title,
        meta={}
    )
    db.add(game)
    db.flush()

    print(f"✓ Created game: {title}")
    print(f"  Public Code: {public_code}")
    print(f"  Admin Code: {game.admin_code}")

    # Create players
    players = []
    print(f"\nCreating {len(player_names)} players...")
    for name in player_names:
        player = Player(display_name=name)
        db.add(player)
        db.flush()

        # Link player to game
        game_player = GamePlayer(
            game_id=game.id,
            player_id=player.id
        )
        db.add(game_player)

        players.append(player)
        print(f"  ✓ Player: {name} (ID: {player.id})")

    return game, players


def create_test_claims(db, users, game1_players, game2_players):
    """Create test claims linking users to players."""
    print(f"\n{'=' * 60}")
    print("CREATING PLAYER IDENTITY CLAIMS")
    print("=" * 60)

    claims = []

    # User 1 claims TestPlayer1
    claim_data = [
        {
            'user': users[0],
            'player': game1_players[0],
            'verification_method': 'manual'
        },
        {
            'user': users[1],
            'player': game1_players[1],
            'verification_method': 'manual'
        }
    ]

    for data in claim_data:
        # Check if claim already exists
        existing = db.query(PokerIdentityClaim).filter(
            PokerIdentityClaim.player_id == data['player'].id
        ).first()
        if existing:
            print(f"✓ Claim already exists: {data['user'].email} → {data['player'].display_name}")
            claims.append(existing)
            continue

        claim = PokerIdentityClaim(
            user_id=data['user'].id,
            player_id=data['player'].id,
            verification_method=data['verification_method'],
            claimed_at=datetime.now(timezone.utc)
        )
        db.add(claim)
        db.flush()
        claims.append(claim)

        print(f"✓ Created claim:")
        print(f"  User: {data['user'].email}")
        print(f"  Player: {data['player'].display_name}")
        print(f"  Method: {data['verification_method']}")

    return claims


def print_summary(users, game1, game1_players, game2, game2_players, claims):
    """Print summary of created test data."""
    print(f"\n{'=' * 60}")
    print("SEED DATA SUMMARY")
    print("=" * 60)

    print("\n📧 TEST USERS:")
    print("  Email                      | Display Name      | Password")
    print("  " + "-" * 70)
    for user in users:
        print(f"  {user.email:25} | {user.display_name:15} | TestPassword123!")

    print("\n🎮 TEST GAMES:")
    print(f"  Game 1: {game1.title}")
    print(f"    Public Code: {game1.public_code}")
    print(f"    Players: {', '.join([p.display_name for p in game1_players])}")
    print(f"\n  Game 2: {game2.title}")
    print(f"    Public Code: {game2.public_code}")
    print(f"    Players: {', '.join([p.display_name for p in game2_players])}")

    print("\n✅ PLAYER CLAIMS:")
    claimed_player_ids = [claim.player_id for claim in claims]
    for claim in claims:
        user = next(u for u in users if u.id == claim.user_id)
        player = next(
            p for p in game1_players + game2_players
            if p.id == claim.player_id
        )
        print(f"  {user.email:25} → {player.display_name}")

    print("\n🔓 UNCLAIMED PLAYERS (for testing):")
    all_players = game1_players + game2_players
    unclaimed = [p for p in all_players if p.id not in claimed_player_ids]
    for player in unclaimed:
        game = game1 if player in game1_players else game2
        print(f"  {player.display_name:20} (in {game.title})")

    print("\n" + "=" * 60)
    print("✓ Seed data created successfully!")
    print("=" * 60)
    print("\nYou can now:")
    print("  1. Login with testuser1@example.com / TestPassword123!")
    print("  2. Login with testuser2@example.com / TestPassword123!")
    print("  3. Navigate to /settings to view claimed players")
    print(f"  4. Try claiming unclaimed players in game {game1.public_code}")
    print("=" * 60)


def main():
    print("\n" + "=" * 60)
    print("PLAYER IDENTITY CLAIMS - SEED DATA SCRIPT")
    print("=" * 60)

    password_hasher = BcryptPasswordHasher()

    with SessionLocal() as db:
        try:
            # Create test users
            users = create_test_users(db, password_hasher)

            # Create first game with players
            game1, game1_players = create_test_game_with_players(
                db,
                public_code="TEST1",
                title="Test Poker Night",
                player_names=["TestPlayer1", "TestPlayer2", "TestPlayer3"]
            )

            # Create second game with players
            game2, game2_players = create_test_game_with_players(
                db,
                public_code="TEST2",
                title="Friday Game",
                player_names=["User One", "BigStack", "LuckyPlayer"]
            )

            # Create test claims
            claims = create_test_claims(db, users, game1_players, game2_players)

            # Commit all changes
            db.commit()

            # Print summary
            print_summary(users, game1, game1_players, game2, game2_players, claims)

        except Exception as e:
            db.rollback()
            print(f"\n❌ ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    main()
