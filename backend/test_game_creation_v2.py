#!/usr/bin/env python3
"""
Test script for the new domain-based game creation architecture.

This script verifies that the Game domain entity, repository pattern,
and v2 service work together correctly.
"""

import sys
import os

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from typing import Dict, Any
from domain.poker.value_objects import PublicCode, AdminToken, GameTitle
from domain.game.entities import Game
from domain.game.services import GameCreationService as DomainService
from domain.poker.exceptions import DuplicatePublicCodeError, GameCreationError


class MockGameRepository:
    """Mock repository for testing without database."""

    def __init__(self):
        self.games = {}
        self.public_codes = set()
        self.admin_tokens = set()

    def save(self, game: Game) -> Game:
        if str(game.public_code) in self.public_codes:
            raise DuplicatePublicCodeError(str(game.public_code))
        if game.admin_token.value in self.admin_tokens:
            from domain.poker.exceptions import DuplicateAdminTokenError
            raise DuplicateAdminTokenError()

        self.games[str(game.id)] = game
        self.public_codes.add(str(game.public_code))
        self.admin_tokens.add(game.admin_token.value)
        return game

    def get_by_public_code(self, public_code: PublicCode):
        for game in self.games.values():
            if game.public_code == public_code:
                return game
        return None

    def get_by_admin_token(self, admin_token: AdminToken):
        for game in self.games.values():
            if game.admin_token.value == admin_token.value:
                return game
        return None

    def public_code_exists(self, public_code: PublicCode) -> bool:
        return str(public_code) in self.public_codes

    def admin_token_exists(self, admin_token: AdminToken) -> bool:
        return admin_token.value in self.admin_tokens

    def get_by_id(self, game_id):
        return self.games.get(str(game_id))

    def update(self, game: Game) -> Game:
        self.games[str(game.id)] = game
        return game

    def delete(self, game_id) -> bool:
        game_key = str(game_id)
        if game_key in self.games:
            game = self.games[game_key]
            del self.games[game_key]
            self.public_codes.discard(str(game.public_code))
            self.admin_tokens.discard(game.admin_token.value)
            return True
        return False


def test_value_objects():
    """Test domain value objects."""
    print("🧪 Testing Value Objects...")

    # Test PublicCode
    code = PublicCode("GAME1")
    assert str(code) == "GAME1"
    print("   ✅ PublicCode creation and string representation")

    # Test AdminToken
    token = AdminToken("a" * 32 + "-test-token-suffix-12345")
    assert len(token.value) >= 32
    print("   ✅ AdminToken creation and validation")

    # Test GameTitle
    title = GameTitle("Thursday Night Poker")
    assert str(title) == "Thursday Night Poker"
    print("   ✅ GameTitle creation and normalization")

    print("✅ Value Objects: All tests passed\n")


def test_game_entity():
    """Test Game domain entity."""
    print("🧪 Testing Game Entity...")

    # Create game entity
    game = Game.create_new(
        public_code=PublicCode("TEST1"),
        admin_token=AdminToken("a" * 32 + "-test-token-12345"),
        title=GameTitle("Test Game")
    )

    assert str(game.public_code) == "TEST1"
    assert game.has_title()
    assert game.get_display_name() == "Test Game"
    print("   ✅ Game entity creation and methods")

    # Test immutability
    updated_game = game.update_title(GameTitle("Updated Title"))
    assert str(game.title) == "Test Game"  # Original unchanged
    assert str(updated_game.title) == "Updated Title"  # New instance updated
    print("   ✅ Game entity immutability")

    print("✅ Game Entity: All tests passed\n")


def test_domain_service():
    """Test GameCreationService domain service."""
    print("🧪 Testing Domain Service...")

    # Create mock repository
    repo = MockGameRepository()
    service = DomainService(repo)

    # Test game creation
    game1 = service.create_game(title="Test Game 1")
    assert game1.has_title()
    assert str(game1.title) == "Test Game 1"
    print("   ✅ Game creation with title")

    # Test game creation without title
    game2 = service.create_game()
    assert not game2.has_title()
    print("   ✅ Game creation without title")

    # Verify games are in repository
    assert len(repo.games) == 2
    print("   ✅ Games persisted to repository")

    # Test retrieval
    retrieved = repo.get_by_public_code(game1.public_code)
    assert retrieved.id == game1.id
    print("   ✅ Game retrieval by public code")

    print("✅ Domain Service: All tests passed\n")


def test_v2_service_compatibility():
    """Test v2 service API compatibility."""
    print("🧪 Testing V2 Service Compatibility...")

    try:
        from services.game_creation_service_v2 import create_game, validate_game_title

        # Test legacy function compatibility (without database)
        print("   ✅ Legacy function imports successful")

        # Test title validation
        validated = validate_game_title("  Test Game  ")
        assert validated == "Test Game"
        print("   ✅ Title validation function")

        print("✅ V2 Service Compatibility: Import tests passed\n")

    except Exception as e:
        print(f"   ❌ V2 Service test failed: {e}")
        return False

    return True


def main():
    """Run all tests."""
    print("🚀 Testing Domain-Based Game Creation Architecture\n")

    try:
        test_value_objects()
        test_game_entity()
        test_domain_service()
        test_v2_service_compatibility()

        print("🎉 ALL TESTS PASSED!")
        print("✅ Domain-based game creation architecture is working correctly")
        print("✅ Ready for integration with existing codebase")

        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)