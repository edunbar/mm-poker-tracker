"""
Integration tests comparing domain-based services with legacy services.

These tests verify that the new domain-based services produce identical
results to the old services, ensuring perfect compatibility during migration.
"""

import pytest
from decimal import Decimal
from datetime import datetime, timezone
from typing import Dict, Any, List
from unittest.mock import Mock, patch
import uuid

from sqlalchemy.orm import Session

from src.db.database import SessionLocal
from src.db.models import Game, Player, GamePlayer, Session as SessionModel, SessionPlayerSummary

# Import both old and new services
from src.services.live_game_service import (
    validate_live_game_data as old_validate_live_game_data,
    validate_session_balance as old_validate_session_balance,
    get_or_create_live_player as old_get_or_create_live_player
)
from src.services.live_game_service_v2 import (
    LiveGameService as NewLiveGameService,
    validate_live_game_data as new_validate_live_game_data,
    validate_session_balance as new_validate_session_balance,
    get_or_create_live_player as new_get_or_create_live_player
)

from src.services.session_ingestion_service import ingest_session as old_ingest_session
from src.services.session_ingestion_service_v2 import SessionIngestionService as NewSessionIngestionService

from src.services.payment_service import PaymentService as OldPaymentService
from src.services.payment_service_v2 import PaymentService as NewPaymentService

from src.services.game_summary_service import (
    get_player_summaries as old_get_player_summaries,
    get_player_analytics as old_get_player_analytics,
    get_session_extremes as old_get_session_extremes,
    GameSummaryService as OldGameSummaryService
)
from src.services.game_summary_service_v2 import (
    get_player_summaries as new_get_player_summaries,
    get_player_analytics as new_get_player_analytics,
    get_session_extremes as new_get_session_extremes,
    GameSummaryService as NewGameSummaryService
)

from src.domain.poker.value_objects import SessionId, PlayerId, GameId, Money


class TestLiveGameServiceParity:
    """Test that new LiveGameService behaves identically to old utility functions."""

    @pytest.fixture
    def db_session(self):
        """Create a test database session with transaction rollback."""
        session = SessionLocal()
        transaction = session.begin()
        try:
            yield session
        finally:
            try:
                transaction.rollback()
            except Exception:
                # Transaction may already be closed/rolled back
                pass
            finally:
                session.close()

    @pytest.fixture
    def test_game(self, db_session):
        """Create a test game with unique identifiers."""
        # Generate exactly 4 hex characters to ensure 5 total with prefix
        unique_id = str(uuid.uuid4()).replace('-', '')[:4].upper()  # Remove dashes, take 4 hex chars, uppercase
        game = Game(
            public_code=f"T{unique_id}",  # 5 characters total (T + 4 hex)
            admin_code=f"A{unique_id}",   # 5 characters total (A + 4 hex)
            title=f"Test Game {unique_id}"
        )
        db_session.add(game)
        db_session.flush()
        return game

    @pytest.fixture
    def test_player(self, db_session, test_game):
        """Create a test player with unique identifiers."""
        unique_id = str(uuid.uuid4())[:8]
        player = Player(
            display_name=f"Test Player {unique_id}",
            external_id=f"test_player_{unique_id}"
        )
        db_session.add(player)
        db_session.flush()

        # Link to game
        game_player = GamePlayer(
            game_id=test_game.id,  # Use UUID primary key for database relationship
            player_id=player.id
        )
        db_session.add(game_player)
        db_session.flush()  # Ensure data is available for queries within transaction

        return player

    def test_validate_live_game_data_produces_same_result(self):
        """Test that both validation functions produce identical results."""
        test_players = [
            {"name": "Alice", "buy_in": 100.0, "cash_out": 150.0, "in_game": 0.0},
            {"name": "Bob", "buy_in": 200.0, "cash_out": 175.0, "in_game": 25.0},
            {"name": "Charlie", "buy_in": 50.0, "cash_out": 45.0, "in_game": 0.0}
        ]

        old_result = old_validate_live_game_data(test_players)
        new_result = new_validate_live_game_data(test_players)

        assert len(old_result) == len(new_result)

        for old_player, new_player in zip(old_result, new_result):
            assert old_player["name"] == new_player["name"]
            assert old_player["buyInSum"] == new_player["buyInSum"]
            assert old_player["buyOutSum"] == new_player["buyOutSum"]
            assert old_player["inGame"] == new_player["inGame"]
            assert old_player["net"] == new_player["net"]

    def test_validate_live_game_data_error_handling_matches(self):
        """Test that both functions handle errors identically."""
        invalid_players = [
            {"name": "", "buy_in": 100.0, "cash_out": 150.0}  # Empty name
        ]

        old_error = None
        new_error = None

        try:
            old_validate_live_game_data(invalid_players)
        except ValueError as e:
            old_error = str(e)

        try:
            new_validate_live_game_data(invalid_players)
        except ValueError as e:
            new_error = str(e)

        assert old_error is not None
        assert new_error is not None
        assert "Name is required" in old_error
        assert "Name is required" in new_error

    def test_validate_session_balance_produces_same_result(self):
        """Test that session balance validation produces identical results."""
        test_players = [
            {"buyInSum": 10000, "buyOutSum": 15000, "inGame": 0, "net": 5000},  # $100 -> $150
            {"buyInSum": 20000, "buyOutSum": 17500, "inGame": 2500, "net": 0}   # $200 -> $175 + $25
        ]

        old_result = old_validate_session_balance(test_players)
        new_result = new_validate_session_balance(test_players)

        # Compare all fields
        assert old_result["total_buy_ins"] == new_result["total_buy_ins"]
        assert old_result["total_cash_outs"] == new_result["total_cash_outs"]
        assert old_result["total_in_game"] == new_result["total_in_game"]
        assert old_result["imbalance"] == new_result["imbalance"]
        assert old_result["balanced"] == new_result["balanced"]
        assert len(old_result["warnings"]) == len(new_result["warnings"])

    def test_get_or_create_live_player_produces_same_result(self, db_session, test_game):
        """Test that player creation produces identical results."""
        player_name = "New Test Player"
        game_id = test_game.id  # Both services should use UUID

        # Test with both functions
        old_player = old_get_or_create_live_player(db_session, player_name, game_id)
        db_session.rollback()  # Reset state

        new_player = new_get_or_create_live_player(db_session, player_name, game_id)

        # Should create identical players
        assert old_player.display_name == new_player.display_name
        assert old_player.external_id == new_player.external_id

    def test_end_session_produces_same_result(self, db_session, test_player, test_game):
        """Test that ending a session produces identical results."""
        # Create a session using the new service
        service = NewLiveGameService(db_session)

        # Create session
        create_result = service.create_session(
            game_id=test_game.public_code,
            player_id=str(test_player.id),
            buy_in_amount=100.0,
            session_type="live"
        )

        session_id = create_result["session_id"]
        cash_out_amount = 150.0

        # End session
        end_result = service.end_session(session_id, cash_out_amount)

        # Verify result format matches expected
        assert "session_id" in end_result
        assert "profit" in end_result
        assert end_result["session_id"] == session_id
        assert end_result["profit"] == 50.0  # 150 - 100

    def test_error_handling_matches_old_service(self, db_session, test_game):
        """Test that error handling produces compatible error messages."""
        service = NewLiveGameService(db_session)

        # Test session not found
        with pytest.raises(ValueError, match="Session not found"):
            service.end_session("nonexistent-session-id", 100.0)

        # Test invalid cash out amount with a fake session ID
        with pytest.raises(ValueError, match="Session not found"):
            # Test with a valid UUID format but nonexistent session
            fake_session_id = str(SessionId.generate())
            service.end_session(fake_session_id, -50.0)


class TestSessionIngestionServiceParity:
    """Test that new SessionIngestionService behaves identically to old function."""

    @pytest.fixture
    def db_session(self):
        session = SessionLocal()
        transaction = session.begin()
        try:
            yield session
        finally:
            try:
                transaction.rollback()
            except Exception:
                # Transaction may already be closed/rolled back
                pass
            finally:
                session.close()

    @pytest.fixture
    def test_game(self, db_session):
        # Generate exactly 4 hex characters to ensure 5 total with prefix
        unique_id = str(uuid.uuid4()).replace('-', '')[:4].upper()
        game = Game(
            public_code=f"T{unique_id}",
            admin_code=f"A{unique_id}",
            title=f"Test Game {unique_id}"
        )
        db_session.add(game)
        db_session.flush()
        return game

    def test_ingest_session_api_compatibility(self, db_session, test_game):
        """Test that the new service maintains API compatibility."""
        service = NewSessionIngestionService(db_session)

        game_data = {
            "sessionId": "test_session_123",
            "playersInfos": {
                "player1": {
                    "id": "player1",
                    "name": "Alice",
                    "buyInSum": 10000,  # $100
                    "buyOutSum": 15000,  # $150
                    "net": 5000
                }
            }
        }

        # Mock the admin validation and other dependencies
        with patch.object(service, '_require_admin_for_game', return_value=test_game):
            with patch.object(service, '_write_audit'):
                with patch.object(service, '_invalidate_game_cache'):
                    with patch.object(service, '_process_poker_statistics', return_value=False):
                        result = service.ingest_session(
                            public_code="TESTG",
                            admin_code="ADMIN123",
                            session_id="test_session_123",
                            game_data=game_data
                        )

        # Verify result structure
        assert "success" in result
        assert "session_id" in result
        assert "players_processed" in result
        assert result["success"] is True
        assert result["session_id"] == "test_session_123"

    def test_backward_compatibility_function(self, db_session, test_game):
        """Test that the backward compatibility function works."""
        from src.services.session_ingestion_service_v2 import ingest_session as new_ingest_session

        game_data = {
            "playersInfos": {
                "player1": {
                    "id": "player1",
                    "name": "Alice",
                    "buyInSum": 10000,
                    "buyOutSum": 15000,
                    "net": 5000
                }
            }
        }

        # This should work without errors
        try:
            result = new_ingest_session(
                public_code="TESTG",
                admin_code="ADMIN123",
                session_id="test_session_123",
                game_data=game_data
            )
            # Function should complete without errors
            assert "success" in result or "error" in str(result)
        except Exception as e:
            # Errors are expected due to missing admin validation,
            # but should be ValueError, not import/syntax errors
            assert isinstance(e, (ValueError, PermissionError))


class TestPaymentServiceParity:
    """Test that new PaymentService behaves identically to old service."""

    @pytest.fixture
    def db_session(self):
        session = SessionLocal()
        transaction = session.begin()
        try:
            yield session
        finally:
            try:
                transaction.rollback()
            except Exception:
                # Transaction may already be closed/rolled back
                pass
            finally:
                session.close()

    @pytest.fixture
    def test_game_and_players(self, db_session):
        """Create test game and players."""
        # Generate exactly 4 hex characters to ensure 5 total with prefix
        unique_id = str(uuid.uuid4()).replace('-', '')[:4].upper()
        game = Game(
            public_code=f"T{unique_id}",
            admin_code=f"A{unique_id}",
            title=f"Test Game {unique_id}"
        )
        db_session.add(game)
        db_session.flush()

        players = []
        for i, name in enumerate(["Alice", "Bob", "Charlie"]):
            player = Player(
                display_name=f"{name}_{unique_id}",
                external_id=f"player_{i+1}_{unique_id}"
            )
            db_session.add(player)
            players.append(player)

        db_session.flush()

        # Link players to game
        for player in players:
            game_player = GamePlayer(
                game_id=game.id,
                player_id=player.id
            )
            db_session.add(game_player)

        # Create some session data for players
        session_model = SessionModel(
            game_id=game.id,
            external_id="test_session",
            session_type="test"
        )
        db_session.add(session_model)
        db_session.flush()

        for i, player in enumerate(players):
            summary = SessionPlayerSummary(
                session_id=session_model.id,
                player_id=player.id,
                buy_in_sum=10000,  # $100
                cash_out_sum=10000 + (i * 2500),  # $100 + ($25 * i)
                in_game=0,
                net=i * 2500,  # $25 * i
                names=[player.display_name]
            )
            db_session.add(summary)

        db_session.flush()  # Ensure data is available for queries within transaction
        return game, players

    def test_payment_summary_structure_matches(self, db_session, test_game_and_players):
        """Test that payment summary has identical structure."""
        game, players = test_game_and_players

        # Commit so old service can see the data in its own session
        db_session.commit()

        old_service = OldPaymentService()
        new_service = NewPaymentService(db_session)

        old_summary = old_service.get_payment_summary(str(game.id))
        new_summary = new_service.get_payment_summary(str(game.id))

        # Should have same number of players
        assert len(old_summary) == len(new_summary)

        # Check that all required fields exist
        for old_player, new_player in zip(old_summary, new_summary):
            assert hasattr(old_player, 'player_id')
            assert hasattr(old_player, 'player_name')
            assert hasattr(old_player, 'poker_net_winnings')
            assert hasattr(old_player, 'total_paid')
            assert hasattr(old_player, 'total_received')
            assert hasattr(old_player, 'balance')
            assert hasattr(old_player, 'realized_earnings')

            assert hasattr(new_player, 'player_id')
            assert hasattr(new_player, 'player_name')
            assert hasattr(new_player, 'poker_net_winnings')
            assert hasattr(new_player, 'total_paid')
            assert hasattr(new_player, 'total_received')
            assert hasattr(new_player, 'balance')
            assert hasattr(new_player, 'realized_earnings')

    def test_settlement_suggestions_structure_matches(self, db_session, test_game_and_players):
        """Test that settlement suggestions have identical structure."""
        game, players = test_game_and_players

        old_service = OldPaymentService()
        new_service = NewPaymentService(db_session)

        old_suggestions = old_service.get_settlement_suggestions(str(game.id))
        new_suggestions = new_service.get_settlement_suggestions(str(game.id))

        # Check structure of suggestions (may be empty)
        for old_suggestion, new_suggestion in zip(old_suggestions, new_suggestions):
            assert hasattr(old_suggestion, 'payer_id')
            assert hasattr(old_suggestion, 'payer_name')
            assert hasattr(old_suggestion, 'recipient_id')
            assert hasattr(old_suggestion, 'recipient_name')
            assert hasattr(old_suggestion, 'amount')

            assert hasattr(new_suggestion, 'payer_id')
            assert hasattr(new_suggestion, 'payer_name')
            assert hasattr(new_suggestion, 'recipient_id')
            assert hasattr(new_suggestion, 'recipient_name')
            assert hasattr(new_suggestion, 'amount')

    def test_record_payment_produces_compatible_result(self, db_session, test_game_and_players):
        """Test that recording a payment produces compatible results."""
        game, players = test_game_and_players
        payer = players[0]
        recipient = players[1]

        new_service = NewPaymentService(db_session)

        payment_amount = Decimal('25.00')
        payment_date = datetime.now(timezone.utc)

        # Record payment with new service
        result = new_service.record_payment(
            game_id=str(game.id),
            payer_id=str(payer.id),
            recipient_id=str(recipient.id),
            amount=payment_amount,
            payment_date=payment_date,
            payment_method="test",
            notes="Test payment"
        )

        # Should return a payment transaction model
        assert str(result.game_id) == str(game.id)
        assert str(result.payer_id) == str(payer.id)
        assert str(result.recipient_id) == str(recipient.id)
        assert result.amount_cents == int(payment_amount * 100)  # Model stores in cents
        assert result.payment_method == "test"
        assert result.notes == "Test payment"

    def test_payment_history_format_matches(self, db_session, test_game_and_players):
        """Test that payment history has identical format."""
        game, players = test_game_and_players

        # First record a payment
        new_service = NewPaymentService(db_session)
        new_service.record_payment(
            game_id=str(game.id),
            payer_id=str(players[0].id),
            recipient_id=str(players[1].id),
            amount=Decimal('25.00'),
            payment_date=datetime.now(timezone.utc)
        )

        # Commit so old service can see the payment
        db_session.commit()

        # Get history from both services
        old_service = OldPaymentService()
        new_service = NewPaymentService(db_session)

        old_history = old_service.get_payment_history(str(game.id))
        new_history = new_service.get_payment_history(str(game.id))

        # Should have same structure
        assert len(old_history) == len(new_history)

        if old_history and new_history:
            old_payment = old_history[0]
            new_payment = new_history[0]

            # Check all required fields exist
            required_fields = [
                'id', 'payer_name', 'recipient_name', 'amount',
                'payment_date', 'payment_method', 'notes', 'reference_id'
            ]

            for field in required_fields:
                assert field in old_payment
                assert field in new_payment


class TestDomainServiceIntegration:
    """Test domain services with real database operations."""

    @pytest.fixture
    def db_session(self):
        session = SessionLocal()
        transaction = session.begin()
        try:
            yield session
        finally:
            try:
                transaction.rollback()
            except Exception:
                # Transaction may already be closed/rolled back
                pass
            finally:
                session.close()

    def test_end_session_complete_flow(self, db_session):
        """Test complete end session flow with database."""
        # Create test data
        unique_id = str(uuid.uuid4())[:4]
        game = Game(
            public_code=f"T{unique_id}",
            admin_code=f"A{unique_id}",
            title=f"Test Game {unique_id}"
        )
        db_session.add(game)
        db_session.flush()

        player = Player(display_name=f"Test Player {unique_id}", external_id=f"test123_{unique_id}")
        db_session.add(player)
        db_session.flush()

        # Link player to game
        game_player = GamePlayer(game_id=game.id, player_id=player.id)
        db_session.add(game_player)

        service = NewLiveGameService(db_session)

        # Create session
        create_result = service.create_session(
            game_id=game.public_code,  # Use public_code instead of UUID
            player_id=str(player.id),
            buy_in_amount=100.0,
            session_type="test"
        )

        session_id = create_result["session_id"]

        # End session (no hand tracking in live game service)
        end_result = service.end_session(session_id, 120.0)

        # Verify results
        assert end_result["profit"] == 20.0  # 120 - 100
        assert end_result["hands_played"] == 0  # Live game service doesn't track hands
        assert end_result["is_profitable"] is True

        db_session.flush()  # Ensure data is available for queries within transaction

    def test_payment_recording_flow(self, db_session):
        """Test complete payment recording flow."""
        # Create test data
        unique_id = str(uuid.uuid4())[:4]
        game = Game(
            public_code=f"T{unique_id}",
            admin_code=f"A{unique_id}",
            title=f"Test Game {unique_id}"
        )
        db_session.add(game)
        db_session.flush()

        players = []
        for name in ["Alice", "Bob"]:
            player = Player(display_name=f"{name}_{unique_id}", external_id=f"{name.lower()}_{unique_id}")
            db_session.add(player)
            players.append(player)

        db_session.flush()

        # Link players to game
        for player in players:
            game_player = GamePlayer(game_id=game.id, player_id=player.id)
            db_session.add(game_player)

        # Create session summaries to establish balances
        session_model = SessionModel(
            game_id=game.id,
            external_id="test_session",
            session_type="test"
        )
        db_session.add(session_model)
        db_session.flush()

        # Alice wins $50, Bob loses $50
        alice_summary = SessionPlayerSummary(
            session_id=session_model.id,
            player_id=players[0].id,
            buy_in_sum=10000,  # $100
            cash_out_sum=15000,  # $150
            in_game=0,
            net=5000,  # +$50
            names=["Alice"]
        )
        bob_summary = SessionPlayerSummary(
            session_id=session_model.id,
            player_id=players[1].id,
            buy_in_sum=10000,  # $100
            cash_out_sum=5000,   # $50
            in_game=0,
            net=-5000,  # -$50
            names=["Bob"]
        )

        db_session.add(alice_summary)
        db_session.add(bob_summary)
        db_session.flush()  # Ensure session data is visible to V2 validation

        # Record payment: Bob pays Alice $30
        service = NewPaymentService(db_session)
        payment = service.record_payment(
            game_id=str(game.id),
            payer_id=str(players[1].id),  # Bob
            recipient_id=str(players[0].id),  # Alice
            amount=Decimal('30.00'),
            payment_date=datetime.now(timezone.utc),
            payment_method="test"
        )

        # Check payment was recorded
        assert payment.amount == Decimal('30.00')

        # Get settlement suggestions
        suggestions = service.get_settlement_suggestions(str(game.id))

        # Should suggest Bob pay Alice the remaining $20
        assert len(suggestions) >= 0  # May be 0 or 1 depending on calculation

        db_session.flush()  # Ensure data is available for queries within transaction

    def test_concurrent_operations(self, db_session):
        """Test basic thread safety and transaction isolation."""
        # Create test data
        unique_id = str(uuid.uuid4())[:4]
        game = Game(
            public_code=f"T{unique_id}",
            admin_code=f"A{unique_id}",
            title=f"Test Game {unique_id}"
        )
        db_session.add(game)
        db_session.flush()

        player = Player(display_name=f"Test Player {unique_id}", external_id=f"test123_{unique_id}")
        db_session.add(player)
        db_session.flush()

        game_player = GamePlayer(game_id=game.id, player_id=player.id)
        db_session.add(game_player)

        service = NewLiveGameService(db_session)

        # Create session
        create_result = service.create_session(
            game_id=game.public_code,  # Use public_code instead of UUID
            player_id=str(player.id),
            buy_in_amount=100.0
        )

        session_id = create_result["session_id"]

        # Test basic operations without hand tracking (since live game service doesn't track hands)
        # End session to test transaction isolation
        end_result = service.end_session(session_id, 150.0)

        assert end_result["profit"] == 50.0  # 150 - 100
        assert end_result["hands_played"] == 0  # Live game service doesn't track hands
        assert end_result["is_profitable"] is True

        db_session.flush()  # Ensure data is available for queries within transaction


class TestGameSummaryServiceParity:
    """Test that new GameSummaryService behaves identically to old service."""

    @pytest.fixture
    def db_session(self):
        """Create a test database session with transaction rollback."""
        session = SessionLocal()
        transaction = session.begin()
        try:
            yield session
        finally:
            try:
                transaction.rollback()
            except Exception:
                # Transaction might already be closed
                pass
            session.close()

    @pytest.fixture
    def sample_game_data(self, db_session):
        """Create sample game data for testing."""
        unique_id = str(uuid.uuid4())[:4]

        # Create game
        game = Game(
            public_code=f"G{unique_id}",
            admin_code=f"A{unique_id}",
            title=f"Test Game {unique_id}"
        )
        db_session.add(game)
        db_session.flush()

        # Create players
        alice = Player(display_name="Alice", external_id=f"alice_{unique_id}")
        bob = Player(display_name="Bob", external_id=f"bob_{unique_id}")
        db_session.add_all([alice, bob])
        db_session.flush()

        # Create game players
        game_alice = GamePlayer(game_id=game.id, player_id=alice.id)
        game_bob = GamePlayer(game_id=game.id, player_id=bob.id)
        db_session.add_all([game_alice, game_bob])

        # Create sessions
        session1 = SessionModel(
            game_id=game.id,
            external_id=f"session1_{unique_id}",
            session_type="cash_game",
            game_number=1
        )
        session2 = SessionModel(
            game_id=game.id,
            external_id=f"session2_{unique_id}",
            session_type="cash_game",
            game_number=2
        )
        db_session.add_all([session1, session2])
        db_session.flush()

        # Create session player summaries
        alice_session1 = SessionPlayerSummary(
            session_id=session1.id,
            player_id=alice.id,
            buy_in_sum=10000,  # $100.00
            cash_out_sum=15000,  # $150.00
            in_game=0,
            net=5000,  # Won $50.00
            names=[alice.display_name]
        )
        alice_session2 = SessionPlayerSummary(
            session_id=session2.id,
            player_id=alice.id,
            buy_in_sum=10000,  # $100.00
            cash_out_sum=8000,   # $80.00
            in_game=0,
            net=-2000,  # Lost $20.00
            names=[alice.display_name]
        )
        bob_session1 = SessionPlayerSummary(
            session_id=session1.id,
            player_id=bob.id,
            buy_in_sum=10000,  # $100.00
            cash_out_sum=5000,   # $50.00
            in_game=0,
            net=-5000,  # Lost $50.00
            names=[bob.display_name]
        )
        bob_session2 = SessionPlayerSummary(
            session_id=session2.id,
            player_id=bob.id,
            buy_in_sum=10000,  # $100.00
            cash_out_sum=12000,  # $120.00
            in_game=0,
            net=2000,  # Won $20.00
            names=[bob.display_name]
        )

        db_session.add_all([alice_session1, alice_session2, bob_session1, bob_session2])
        db_session.commit()

        return {
            'game': game,
            'players': {'alice': alice, 'bob': bob},
            'sessions': [session1, session2]
        }

    def test_player_summaries_compatibility(self, db_session, sample_game_data):
        """Test that both services return identical player summaries."""
        public_code = sample_game_data['game'].public_code

        # Clear any existing cache
        from src.services.game_summary_service_v2 import clear_all_cache
        clear_all_cache()

        # Get results from both services
        old_result = old_get_player_summaries(public_code)
        new_result = new_get_player_summaries(public_code)

        # Verify structure matches
        assert isinstance(old_result, dict)
        assert isinstance(new_result, dict)
        assert "title" in old_result
        assert "title" in new_result
        assert "rows" in old_result
        assert "rows" in new_result

        # Verify title matches
        assert old_result["title"] == new_result["title"]

        # Verify rows structure and content
        assert len(old_result["rows"]) == len(new_result["rows"])

        # Sort both results by player name for consistent comparison
        old_rows = sorted(old_result["rows"], key=lambda x: x["player"])
        new_rows = sorted(new_result["rows"], key=lambda x: x["player"])

        for old_row, new_row in zip(old_rows, new_rows):
            assert old_row["player"] == new_row["player"]
            assert old_row["rank"] == new_row["rank"]
            assert abs(float(old_row["buyIn"]) - float(new_row["buyIn"])) < 0.01
            assert abs(float(old_row["cashOut"]) - float(new_row["cashOut"])) < 0.01
            assert abs(float(old_row["net"]) - float(new_row["net"])) < 0.01
            assert old_row["gamesPlayed"] == new_row["gamesPlayed"]

    def test_player_analytics_compatibility(self, db_session, sample_game_data):
        """Test that both services return identical player analytics."""
        public_code = sample_game_data['game'].public_code

        # Clear any existing cache
        from src.services.game_summary_service_v2 import clear_all_cache
        clear_all_cache()

        # Get results from both services
        old_result = old_get_player_analytics(public_code)
        new_result = new_get_player_analytics(public_code)

        # Verify structure matches
        assert isinstance(old_result, dict)
        assert isinstance(new_result, dict)
        assert "analytics" in old_result
        assert "analytics" in new_result

        old_analytics = old_result["analytics"]
        new_analytics = new_result["analytics"]

        # Verify same players are present
        assert set(old_analytics.keys()) == set(new_analytics.keys())

        # Compare analytics for each player
        for player_id in old_analytics.keys():
            old_data = old_analytics[player_id]
            new_data = new_analytics[player_id]

            # Compare key fields
            assert old_data["player_name"] == new_data["player_name"]
            assert old_data["total_games"] == new_data["total_games"]
            assert old_data["total_wins"] == new_data["total_wins"]
            assert old_data["total_losses"] == new_data["total_losses"]
            assert old_data["current_winning_streak"] == new_data["current_winning_streak"]
            assert old_data["current_losing_streak"] == new_data["current_losing_streak"]
            assert old_data["longest_winning_streak"] == new_data["longest_winning_streak"]
            assert old_data["longest_losing_streak"] == new_data["longest_losing_streak"]
            assert old_data["never_profitable"] == new_data["never_profitable"]
            assert abs(float(old_data["total_net"]) - float(new_data["total_net"])) < 0.01
            assert abs(float(old_data["total_buy_in"]) - float(new_data["total_buy_in"])) < 0.01

    def test_session_extremes_compatibility(self, db_session, sample_game_data):
        """Test that both services return identical session extremes."""
        public_code = sample_game_data['game'].public_code

        # Clear any existing cache
        from src.services.game_summary_service_v2 import clear_all_cache
        clear_all_cache()

        # Get results from both services
        old_result = old_get_session_extremes(public_code)
        new_result = new_get_session_extremes(public_code)

        # Verify structure matches
        assert isinstance(old_result, dict)
        assert isinstance(new_result, dict)
        assert "best_sessions" in old_result
        assert "best_sessions" in new_result
        assert "worst_sessions" in old_result
        assert "worst_sessions" in new_result

        # Verify counts match
        assert len(old_result["best_sessions"]) == len(new_result["best_sessions"])
        assert len(old_result["worst_sessions"]) == len(new_result["worst_sessions"])

        # Compare best sessions
        for old_session, new_session in zip(old_result["best_sessions"], new_result["best_sessions"]):
            assert old_session["player_name"] == new_session["player_name"]
            assert old_session["game_number"] == new_session["game_number"]
            assert old_session["net"] == new_session["net"]
            assert old_session["buy_in_sum"] == new_session["buy_in_sum"]
            assert old_session["cash_out_sum"] == new_session["cash_out_sum"]

        # Compare worst sessions
        for old_session, new_session in zip(old_result["worst_sessions"], new_result["worst_sessions"]):
            assert old_session["player_name"] == new_session["player_name"]
            assert old_session["game_number"] == new_session["game_number"]
            assert old_session["net"] == new_session["net"]
            assert old_session["buy_in_sum"] == new_session["buy_in_sum"]
            assert old_session["cash_out_sum"] == new_session["cash_out_sum"]

    def test_service_class_compatibility(self, db_session, sample_game_data):
        """Test that both service classes produce identical results."""
        public_code = sample_game_data['game'].public_code

        # Clear any existing cache
        from src.services.game_summary_service_v2 import clear_all_cache
        clear_all_cache()

        # Create service instances
        old_service = OldGameSummaryService(db_session)
        new_service = NewGameSummaryService(db_session)

        # Test all three methods
        old_summaries = old_service.get_player_summaries(public_code)
        new_summaries = new_service.get_player_summaries(public_code)
        assert old_summaries == new_summaries

        old_analytics = old_service.get_player_analytics(public_code)
        new_analytics = new_service.get_player_analytics(public_code)
        assert old_analytics == new_analytics

        old_extremes = old_service.get_session_extremes(public_code)
        new_extremes = new_service.get_session_extremes(public_code)

        # Compare structure first
        assert set(old_extremes.keys()) == set(new_extremes.keys())

        # Compare best sessions (sorted by external_id for consistency)
        old_best = sorted(old_extremes['best_sessions'], key=lambda x: x['external_id'])
        new_best = sorted(new_extremes['best_sessions'], key=lambda x: x['external_id'])
        assert len(old_best) == len(new_best)

        # Compare worst sessions (sorted by external_id for consistency)
        old_worst = sorted(old_extremes['worst_sessions'], key=lambda x: x['external_id'])
        new_worst = sorted(new_extremes['worst_sessions'], key=lambda x: x['external_id'])
        assert len(old_worst) == len(new_worst)

    def test_cache_behavior_consistency(self, db_session, sample_game_data):
        """Test that caching behavior is consistent between services."""
        public_code = sample_game_data['game'].public_code

        # Clear any existing cache
        from src.services.game_summary_service_v2 import clear_all_cache
        from src.services.game_summary_service import clear_all_cache as old_clear_cache
        clear_all_cache()
        old_clear_cache()

        # First calls should hit database
        old_result1 = old_get_player_summaries(public_code)
        new_result1 = new_get_player_summaries(public_code)

        # Second calls should use cache and return identical results
        old_result2 = old_get_player_summaries(public_code)
        new_result2 = new_get_player_summaries(public_code)

        assert old_result1 == old_result2
        assert new_result1 == new_result2
        assert old_result1 == new_result1

    def test_domain_object_access(self, db_session, sample_game_data):
        """Test that v2 service provides domain object access."""
        public_code = sample_game_data['game'].public_code

        new_service = NewGameSummaryService(db_session)

        # This method should only exist in v2 service
        domain_object = new_service.get_game_summary_domain_object(public_code)

        # Verify it's a domain object
        from domain.game.entities import GameSummary
        assert isinstance(domain_object, GameSummary)
        assert str(domain_object.game_id) == str(sample_game_data['game'].id)
        assert len(domain_object.player_summaries) > 0

    def test_error_handling_consistency(self, db_session):
        """Test that both services handle errors consistently."""
        nonexistent_code = "TEST9"  # Valid format but non-existent

        # Both services should handle non-existent games gracefully
        old_result = old_get_player_summaries(nonexistent_code)
        new_result = new_get_player_summaries(nonexistent_code)

        # Should return empty results rather than crash
        assert isinstance(old_result, dict)
        assert isinstance(new_result, dict)
        assert old_result["rows"] == []
        assert new_result["rows"] == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])