"""
Test for external_id conflict fix.

This test verifies that session ingestion correctly handles the scenario where:
1. A player exists in Game A with external_id "ABC123"
2. A player exists in Game B with NULL external_id but same display name
3. New session ingestion for Game B has player with external_id "ABC123"
4. Code should use the player from Game A (correct match) not try to update Game B player

This was causing: duplicate key value violates unique constraint "uq_players_external_id"
"""

import pytest
from sqlalchemy import select
from db.database import SessionLocal
from db.models import Game, Player, GamePlayer, Session as SessionModel, SessionPlayerSummary
from services.session_ingestion_service import ingest_session
import secrets


class TestExternalIdConflictFix:
    """Test that external_id is prioritized over display_name during player matching."""

    @pytest.fixture
    def setup_conflict_scenario(self):
        """
        Setup:
        - Game A with Player "Remy" (external_id="ABC123")
        - Game B with Player "Remy" (external_id=NULL)
        """
        db = SessionLocal()
        try:
            # Generate unique codes for each test run
            unique_suffix = secrets.token_urlsafe(4)

            # Create Game A
            game_a = Game(
                public_code=f"GAMEA{unique_suffix}",
                admin_code=secrets.token_urlsafe(32),
                title="Game A"
            )
            db.add(game_a)

            # Create Game B
            game_b = Game(
                public_code=f"GAMEB{unique_suffix}",
                admin_code=secrets.token_urlsafe(32),
                title="Game B"
            )
            db.add(game_b)
            db.flush()

            # Create Player "Remy" with external_id in Game A
            # Use unique external_id for each test run
            test_external_id = f"ABC{unique_suffix}"
            player_with_id = Player(
                display_name="Remy",
                external_id=test_external_id
            )
            db.add(player_with_id)
            db.flush()

            # Link to Game A
            db.add(GamePlayer(game_id=game_a.id, player_id=player_with_id.id))

            # Create Player "Remy" without external_id in Game B
            player_without_id = Player(
                display_name="Remy",
                external_id=None
            )
            db.add(player_without_id)
            db.flush()

            # Link to Game B
            db.add(GamePlayer(game_id=game_b.id, player_id=player_without_id.id))

            db.commit()

            yield {
                "game_a": game_a,
                "game_b": game_b,
                "player_with_id": player_with_id,
                "player_without_id": player_without_id,
                "test_external_id": test_external_id
            }

        finally:
            # Cleanup
            db.rollback()
            db.close()

    def test_external_id_prioritized_over_display_name(self, setup_conflict_scenario):
        """
        Test that when ingesting a session with external_id into Game B,
        the code uses the player from Game A (who has that external_id) rather than
        trying to set external_id on Game B's player.
        """
        game_b = setup_conflict_scenario["game_b"]
        player_with_id = setup_conflict_scenario["player_with_id"]
        player_without_id = setup_conflict_scenario["player_without_id"]
        test_external_id = setup_conflict_scenario["test_external_id"]

        # Ingest session into Game B with player "Remy" (external_id from setup)
        session_data = {
            "playersInfos": {
                test_external_id: {
                    "id": test_external_id,
                    "names": ["Remy"],
                    "buyInSum": 10000,
                    "buyOutSum": 15000,
                    "inGame": 0,
                    "net": 5000
                }
            }
        }

        # This should NOT raise duplicate key error
        result = ingest_session(
            public_code=game_b.public_code,
            admin_code=game_b.admin_code,
            session_id="test_session_123",
            game_data=session_data
        )

        assert result["success"]

        # Verify the session was linked to the correct player (player_with_id from Game A)
        db = SessionLocal()
        try:
            session = db.execute(
                select(SessionModel).where(
                    SessionModel.game_id == game_b.id,
                    SessionModel.external_id == "test_session_123"
                )
            ).scalar_one()

            summaries = db.execute(
                select(SessionPlayerSummary).where(
                    SessionPlayerSummary.session_id == session.id
                )
            ).scalars().all()

            assert len(summaries) == 1
            assert summaries[0].player_id == player_with_id.id  # Should use player from Game A
            assert summaries[0].player_id != player_without_id.id  # NOT the Game B player

            # Verify player is now linked to both games
            game_players = db.execute(
                select(GamePlayer).where(GamePlayer.player_id == player_with_id.id)
            ).scalars().all()

            assert len(game_players) == 2  # Linked to both Game A and Game B

            # Verify Game B's original player still has NULL external_id
            refreshed_player_without_id = db.execute(
                select(Player).where(Player.id == player_without_id.id)
            ).scalar_one()
            assert refreshed_player_without_id.external_id is None

        finally:
            db.close()

    def test_case_insensitive_external_id_matching(self, setup_conflict_scenario):
        """
        Test that external_id matching is case-insensitive.
        PokerNow sometimes sends different casing.
        """
        game_b = setup_conflict_scenario["game_b"]
        player_with_id = setup_conflict_scenario["player_with_id"]
        test_external_id = setup_conflict_scenario["test_external_id"]

        # Ingest with lowercase external_id (player has whatever casing from setup)
        lowercase_external_id = test_external_id.lower()
        session_data = {
            "playersInfos": {
                lowercase_external_id: {  # lowercase
                    "id": lowercase_external_id,
                    "names": ["Remy"],
                    "buyInSum": 10000,
                    "buyOutSum": 15000,
                    "inGame": 0,
                    "net": 5000
                }
            }
        }

        result = ingest_session(
            public_code=game_b.public_code,
            admin_code=game_b.admin_code,
            session_id="test_session_lowercase",
            game_data=session_data
        )

        assert result["success"]

        # Verify it matched the existing player despite case difference
        db = SessionLocal()
        try:
            session = db.execute(
                select(SessionModel).where(
                    SessionModel.game_id == game_b.id,
                    SessionModel.external_id == "test_session_lowercase"
                )
            ).scalar_one()

            summaries = db.execute(
                select(SessionPlayerSummary).where(
                    SessionPlayerSummary.session_id == session.id
                )
            ).scalars().all()

            assert len(summaries) == 1
            assert summaries[0].player_id == player_with_id.id

        finally:
            db.close()
