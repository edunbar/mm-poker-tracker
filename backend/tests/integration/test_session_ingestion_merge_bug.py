"""
Integration test for session ingestion merge tool bug fix.

This test reproduces the bug where merging players with in_game chips
resulted in incorrect net calculations.

The bug occurred because the merge tool used:
  net = (buyOutSum === 0 ? inGame : buyOutSum) - buyInSum

When it should have been:
  net = (buyOutSum + inGame) - buyInSum

This test ensures the backend always recalculates net correctly,
regardless of what the frontend sends.
"""
import pytest
from decimal import Decimal
from datetime import datetime, timezone

from db.database import SessionLocal
from db.models import Game, Session as SessionModel, SessionPlayerSummary, Player
from services.session_ingestion_service import ingest_session


@pytest.fixture
def test_game(db_session):
    """Create a test game for session ingestion."""
    game = Game(
        public_code="TEST123",
        admin_code="ADMIN123",
    )
    db_session.add(game)
    db_session.commit()
    return game


def cents(dollars: float) -> int:
    """Convert dollars to cents (integer)."""
    return int(round(dollars * 100))


class TestSessionIngestionMergeBug:
    """Test cases for the session ingestion merge tool bug."""

    def test_merge_with_in_game_chips_frontend_bug(self, test_game):
        """
        Test that backend correctly recalculates net even when frontend
        sends incorrect net value due to merge tool bug.

        Scenario: Player Max has two identities that get merged:
        - Merged: buy_in=$240.13, cash_out=$137.49, in_game=$330.95

        BUGGY frontend calculation (old merge tool):
        - net = $137.49 - $240.13 = -$102.64 (WRONG!)

        CORRECT calculation:
        - net = $137.49 + $330.95 - $240.13 = $228.31 (CORRECT!)

        This test sends the buggy frontend net value and verifies
        that the backend recalculates it correctly.
        """
        # Simulate what the frontend would send with the BUGGY merge tool
        buggy_frontend_net = cents(137.49 - 240.13)  # -102.64 (WRONG!)
        correct_net = cents(137.49 + 330.95 - 240.13)  # 228.31 (CORRECT!)

        game_data = {
            "playersInfos": {
                "max_external_id": {
                    "id": "max_external_id",
                    "names": ["Max", "Trevor Neubauer"],
                    "buyInSum": cents(240.13),
                    "buyOutSum": cents(137.49),
                    "inGame": cents(330.95),
                    "net": buggy_frontend_net,  # Frontend sends WRONG value
                }
            }
        }

        # Ingest the session
        result = ingest_session(
            public_code="TEST123",
            admin_code="ADMIN123",
            session_id="test_merge_session",
            game_data=game_data,
        )

        assert result["success"] is True

        # Verify the backend IGNORED the buggy frontend net and recalculated
        with SessionLocal() as db:
            session = db.query(SessionModel).filter_by(
                external_id="test_merge_session"
            ).first()

            assert session is not None

            summary = db.query(SessionPlayerSummary).filter_by(
                session_id=session.id
            ).first()

            assert summary is not None

            # The backend should have CORRECTED the net value
            assert summary.net == correct_net, (
                f"Backend should recalculate net correctly. "
                f"Expected {correct_net} cents (${correct_net/100:.2f}), "
                f"got {summary.net} cents (${summary.net/100:.2f})"
            )

            # Verify the calculation components
            assert summary.buy_in_sum == cents(240.13)
            assert summary.cash_out_sum == cents(137.49)
            assert summary.in_game == cents(330.95)

    def test_merge_multiple_players_with_in_game(self, db_session):
        """
        Test merging two players where both have in_game chips.

        This ensures the merge calculation works correctly when:
        - Merged result: buy_in=$300, cash_out=$150, in_game=$225
        - Expected net: $150 + $225 - $300 = $75
        """
        # Create a separate game for this test
        game = Game(
            public_code="TEST456",
            admin_code="ADMIN456",
        )
        db_session.add(game)
        db_session.commit()

        game_data = {
            "playersInfos": {
                "player_merged": {
                    "id": "player_merged",
                    "names": ["Alice", "Alice Smith"],
                    "buyInSum": cents(300.00),
                    "buyOutSum": cents(150.00),
                    "inGame": cents(225.00),
                    # Frontend might send wrong net, but backend should fix it
                    "net": cents(50.00),  # WRONG - should be 75.00
                }
            }
        }

        result = ingest_session(
            public_code="TEST456",
            admin_code="ADMIN456",
            session_id="test_merge_multiple",
            game_data=game_data,
        )

        assert result["success"] is True

        with SessionLocal() as db:
            session = db.query(SessionModel).filter_by(
                external_id="test_merge_multiple"
            ).first()

            summary = db.query(SessionPlayerSummary).filter_by(
                session_id=session.id
            ).first()

            # Backend should calculate: 150 + 225 - 300 = 75
            expected_net = cents(75.00)
            assert summary.net == expected_net

    def test_no_in_game_chips_still_works(self, db_session):
        """
        Test that normal sessions (no in_game chips) still work correctly.

        Player: buy_in=$200, cash_out=$250, in_game=$0
        Expected net: $50
        """
        # Create a separate game for this test
        game = Game(
            public_code="TEST789",
            admin_code="ADMIN789",
        )
        db_session.add(game)
        db_session.commit()

        game_data = {
            "playersInfos": {
                "bob_id": {
                    "id": "bob_id",
                    "names": ["Bob"],
                    "buyInSum": cents(200.00),
                    "buyOutSum": cents(250.00),
                    "inGame": cents(0.00),
                    "net": cents(50.00),
                }
            }
        }

        result = ingest_session(
            public_code="TEST789",
            admin_code="ADMIN789",
            session_id="test_no_in_game",
            game_data=game_data,
        )

        assert result["success"] is True

        with SessionLocal() as db:
            session = db.query(SessionModel).filter_by(
                external_id="test_no_in_game"
            ).first()

            summary = db.query(SessionPlayerSummary).filter_by(
                session_id=session.id
            ).first()

            expected_net = cents(50.00)
            assert summary.net == expected_net

    def test_zero_cash_out_with_in_game(self, db_session):
        """
        Test the specific edge case that caused the original bug:
        When cash_out is zero but in_game has chips.

        Player busts but game is incomplete, so chips are still on table.
        The old merge tool would use: net = (0 === 0 ? inGame : 0) - buy_in = inGame - buy_in

        This test verifies we handle this correctly.
        """
        # Create a separate game for this test
        game = Game(
            public_code="TEST999",
            admin_code="ADMIN999",
        )
        db_session.add(game)
        db_session.commit()

        game_data = {
            "playersInfos": {
                "charlie_id": {
                    "id": "charlie_id",
                    "names": ["Charlie"],
                    "buyInSum": cents(100.00),
                    "buyOutSum": cents(0.00),  # Busted or game incomplete
                    "inGame": cents(50.00),     # Still has chips on table
                    "net": cents(50.00),        # Frontend might send this (inGame - buy_in)
                }
            }
        }

        result = ingest_session(
            public_code="TEST999",
            admin_code="ADMIN999",
            session_id="test_zero_cashout",
            game_data=game_data,
        )

        assert result["success"] is True

        with SessionLocal() as db:
            session = db.query(SessionModel).filter_by(
                external_id="test_zero_cashout"
            ).first()

            summary = db.query(SessionPlayerSummary).filter_by(
                session_id=session.id
            ).first()

            # Backend should calculate: 0 + 50 - 100 = -50
            expected_net = cents(-50.00)
            assert summary.net == expected_net

            # Verify components
            assert summary.buy_in_sum == cents(100.00)
            assert summary.cash_out_sum == cents(0.00)
            assert summary.in_game == cents(50.00)
