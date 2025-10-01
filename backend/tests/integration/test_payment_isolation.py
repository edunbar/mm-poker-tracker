"""
Critical Financial Integrity Tests - Cross-Game Payment Isolation

These tests prevent catastrophic cross-contamination that could:
- Mix payments between different games
- Allow players to access other games' funds
- Corrupt balances across game boundaries
- Enable unauthorized payment transfers

All tests verify complete financial isolation between games.
"""

import pytest
from decimal import Decimal
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import text
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.db.database import SessionLocal, engine
from src.db.models import Game, Player, PaymentTransaction, PaymentBalance, Session, SessionPlayerSummary
from src.services.payment_service_v2 import PaymentService


class TestPaymentIsolation:
    """Critical tests for cross-game payment isolation and security."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Clean database before and after each test."""
        with engine.connect() as conn:
            # Clean up in dependency order
            conn.execute(text("DELETE FROM payment_transactions"))
            conn.execute(text("DELETE FROM payment_balances"))
            conn.execute(text("DELETE FROM session_player_summaries"))
            conn.execute(text("DELETE FROM sessions"))
            conn.execute(text("DELETE FROM game_players"))
            conn.execute(text("DELETE FROM players"))
            conn.execute(text("DELETE FROM games"))
            conn.commit()

        yield

        # Clean up after test
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM payment_transactions"))
            conn.execute(text("DELETE FROM payment_balances"))
            conn.execute(text("DELETE FROM session_player_summaries"))
            conn.execute(text("DELETE FROM sessions"))
            conn.execute(text("DELETE FROM game_players"))
            conn.execute(text("DELETE FROM players"))
            conn.execute(text("DELETE FROM games"))
            conn.commit()

    def create_game_with_players(self, game_suffix, num_players=3, poker_results=None):
        """Create a test game with players and session data."""
        if poker_results is None:
            poker_results = [5000, -2000, -3000]  # Default balanced results

        assert sum(poker_results) == 0, f"Poker results must sum to 0, got {sum(poker_results)}"

        with SessionLocal() as db:
            # Create game
            game = Game(
                public_code=f"TEST{game_suffix}",
                admin_code=f"admin-{game_suffix}-{uuid4()}",
                title=f"Isolation Test Game {game_suffix}"
            )
            db.add(game)
            db.flush()

            # Create players
            players = []
            for i in range(num_players):
                player = Player(
                    external_id=f"player_{i}_{game_suffix}@test",
                    display_name=f"Player {i+1} Game {game_suffix}"
                )
                db.add(player)
                players.append(player)

            db.flush()

            # Create session
            session = Session(
                game_id=game.id,
                external_id=f"session_{game_suffix}_{uuid4().hex[:8]}",
                game_number=1,
                started_at=datetime.now(timezone.utc),
                ended_at=datetime.now(timezone.utc)
            )
            db.add(session)
            db.flush()

            # Create session summaries
            for i, player in enumerate(players):
                summary = SessionPlayerSummary(
                    session_id=session.id,
                    player_id=player.id,
                    buy_in_sum=10000,
                    cash_out_sum=10000 + poker_results[i],
                    in_game=0,
                    net=poker_results[i],
                    names=[player.display_name]
                )
                db.add(summary)

            db.commit()
            return str(game.id), [str(p.id) for p in players]

    def test_payment_isolation_between_games(self, db_session):
        """
        CRITICAL: Payments in game A must not affect balances in game B.
        """
        # Create two separate games
        game_a_id, players_a = self.create_game_with_players("A")
        game_b_id, players_b = self.create_game_with_players("B")

        payment_service = PaymentService(db_session)
        payment_date = datetime.now(timezone.utc)

        # Get initial summaries for both games
        initial_summaries_a = payment_service.get_payment_summary(game_a_id)
        initial_summaries_b = payment_service.get_payment_summary(game_b_id)

        # Make payments in game A
        payment_service.record_payment(
            game_id=game_a_id,
            payer_id=players_a[0],
            recipient_id=players_a[1],
            amount=Decimal("100.00"),
            payment_date=payment_date,
            payment_method="Test",
            created_by="test"
        )

        payment_service.record_payment(
            game_id=game_a_id,
            payer_id=players_a[1],
            recipient_id=players_a[2],
            amount=Decimal("50.00"),
            payment_date=payment_date,
            payment_method="Test",
            created_by="test"
        )

        # Get updated summaries
        updated_summaries_a = payment_service.get_payment_summary(game_a_id)
        updated_summaries_b = payment_service.get_payment_summary(game_b_id)

        # Verify game A balances changed
        a_player_0_initial = next(s for s in initial_summaries_a if s.player_id == players_a[0])
        a_player_0_updated = next(s for s in updated_summaries_a if s.player_id == players_a[0])
        assert a_player_0_updated.total_paid != a_player_0_initial.total_paid, \
            "Game A payments not recorded"

        # CRITICAL: Verify game B balances are completely unchanged
        assert len(initial_summaries_b) == len(updated_summaries_b), \
            "Game B player count changed"

        for initial, updated in zip(initial_summaries_b, updated_summaries_b):
            assert initial.player_id == updated.player_id
            assert initial.total_paid == updated.total_paid, \
                f"Game B player {initial.player_id} total_paid changed from isolation breach"
            assert initial.total_received == updated.total_received, \
                f"Game B player {initial.player_id} total_received changed from isolation breach"
            assert initial.balance == updated.balance, \
                f"Game B player {initial.player_id} balance changed from isolation breach"

    def test_player_in_multiple_games_isolation(self, db_session):
        """
        CRITICAL: Player participating in multiple games must have isolated balances.
        """
        # Create shared players
        with SessionLocal() as db:
            shared_players = []
            for i in range(3):
                player = Player(
                    external_id=f"shared_player_{i}@test",
                    display_name=f"Shared Player {i+1}"
                )
                db.add(player)
                shared_players.append(player)
            db.commit()

        shared_player_ids = [str(p.id) for p in shared_players]

        # Create two games with the same players
        game_x_id = self.create_game_with_shared_players("X", shared_players)
        game_y_id = self.create_game_with_shared_players("Y", shared_players)

        payment_service = PaymentService(db_session)
        payment_date = datetime.now(timezone.utc)

        # Make payments in game X only
        payment_service.record_payment(
            game_id=game_x_id,
            payer_id=shared_player_ids[0],
            recipient_id=shared_player_ids[1],
            amount=Decimal("200.00"),
            payment_date=payment_date,
            payment_method="Game X",
            created_by="test"
        )

        # Get summaries for both games
        summaries_x = payment_service.get_payment_summary(game_x_id)
        summaries_y = payment_service.get_payment_summary(game_y_id)

        # Verify player 0 has payment in game X
        player_0_game_x = next(s for s in summaries_x if s.player_id == shared_player_ids[0])
        assert player_0_game_x.total_paid == Decimal("200.00")

        # CRITICAL: Verify same player has no payment in game Y
        player_0_game_y = next(s for s in summaries_y if s.player_id == shared_player_ids[0])
        assert player_0_game_y.total_paid == Decimal("0.00"), \
            "Payment in game X affected same player's balance in game Y"

        # Verify player 1 has received payment in game X
        player_1_game_x = next(s for s in summaries_x if s.player_id == shared_player_ids[1])
        assert player_1_game_x.total_received == Decimal("200.00")

        # CRITICAL: Verify same player has not received payment in game Y
        player_1_game_y = next(s for s in summaries_y if s.player_id == shared_player_ids[1])
        assert player_1_game_y.total_received == Decimal("0.00"), \
            "Payment received in game X affected same player's balance in game Y"

    def create_game_with_shared_players(self, game_suffix, shared_players):
        """Create a game with pre-existing shared players."""
        with SessionLocal() as db:
            # Create game
            game = Game(
                public_code=f"SHARED{game_suffix}",
                admin_code=f"admin-shared-{game_suffix}-{uuid4()}",
                title=f"Shared Players Game {game_suffix}"
            )
            db.add(game)
            db.flush()

            # Create session
            session = Session(
                game_id=game.id,
                external_id=f"session_shared_{game_suffix}_{uuid4().hex[:8]}",
                game_number=1,
                started_at=datetime.now(timezone.utc),
                ended_at=datetime.now(timezone.utc)
            )
            db.add(session)
            db.flush()

            # Create balanced session summaries
            poker_results = [5000, -2000, -3000]
            for i, player in enumerate(shared_players):
                summary = SessionPlayerSummary(
                    session_id=session.id,
                    player_id=player.id,
                    buy_in_sum=10000,
                    cash_out_sum=10000 + poker_results[i],
                    in_game=0,
                    net=poker_results[i],
                    names=[player.display_name]
                )
                db.add(summary)

            db.commit()
            return str(game.id)

    def test_concurrent_operations_across_games(self, db_session):
        """
        CRITICAL: Concurrent operations across different games must not interfere.
        """
        # Create multiple games
        games_and_players = []
        for i in range(5):
            game_id, player_ids = self.create_game_with_players(f"CONC{i}")
            games_and_players.append((game_id, player_ids))

        payment_date = datetime.now(timezone.utc)

        def make_game_payment(game_data):
            """Each thread gets its own session - SQLAlchemy sessions are not thread-safe."""
            game_id, player_ids = game_data
            with SessionLocal() as thread_session:
                thread_payment_service = PaymentService(thread_session)
                result = thread_payment_service.record_payment(
                    game_id=game_id,
                    payer_id=player_ids[0],
                    recipient_id=player_ids[1],
                    amount=Decimal("75.00"),
                    payment_date=payment_date,
                    payment_method="Concurrent",
                    created_by="test"
                )
                thread_session.commit()
                return result

        # Execute payments across all games simultaneously
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_game_payment, game_data) for game_data in games_and_players]
            results = [future.result() for future in as_completed(futures)]

        # Verify all payments succeeded
        for result in results:
            assert not isinstance(result, Exception), f"Concurrent payment failed: {result}"

        # Verify each game has exactly one payment and correct isolation
        for game_id, player_ids in games_and_players:
            summaries = PaymentService(db_session).get_payment_summary(game_id)

            # Verify payment amounts
            payer_summary = next(s for s in summaries if s.player_id == player_ids[0])
            recipient_summary = next(s for s in summaries if s.player_id == player_ids[1])
            other_summary = next(s for s in summaries if s.player_id == player_ids[2])

            assert payer_summary.total_paid == Decimal("75.00")
            assert recipient_summary.total_received == Decimal("75.00")
            assert other_summary.total_paid == Decimal("0.00")
            assert other_summary.total_received == Decimal("0.00")

    def test_game_deletion_isolation(self, db_session):
        """
        CRITICAL: Deleting one game must not affect other games' financial data.
        """
        # Create two games with payments
        game_1_id, players_1 = self.create_game_with_players("DEL1")
        game_2_id, players_2 = self.create_game_with_players("DEL2")

        payment_service = PaymentService(db_session)
        payment_date = datetime.now(timezone.utc)

        # Make payments in both games
        payment_service.record_payment(game_1_id, players_1[0], players_1[1], Decimal("100.00"), payment_date, "Game1", created_by="test")
        payment_service.record_payment(game_2_id, players_2[0], players_2[1], Decimal("150.00"), payment_date, "Game2", created_by="test")

        # Commit payments before deletion to avoid locks
        db_session.commit()

        # Get game 2 state before deletion
        game_2_summaries_before = payment_service.get_payment_summary(game_2_id)

        # Delete game 1 (simulate cascade delete)
        with SessionLocal() as deletion_session:
            game_to_delete = deletion_session.query(Game).filter(Game.id == game_1_id).first()
            if game_to_delete:
                deletion_session.delete(game_to_delete)
                deletion_session.commit()

        # Verify game 2 is completely unaffected
        game_2_summaries_after = payment_service.get_payment_summary(game_2_id)

        assert len(game_2_summaries_before) == len(game_2_summaries_after)

        for before, after in zip(game_2_summaries_before, game_2_summaries_after):
            assert before.player_id == after.player_id
            assert before.total_paid == after.total_paid
            assert before.total_received == after.total_received
            assert before.balance == after.balance

        # Verify game 2 still has its payment
        payer_summary = next(s for s in game_2_summaries_after if s.player_id == players_2[0])
        assert payer_summary.total_paid == Decimal("150.00")

    def test_admin_operations_respect_game_boundaries(self, db_session):
        """
        CRITICAL: Admin operations like balance recalculation must respect game boundaries.
        """
        # Create games with same-named players but different games
        game_alpha_id, players_alpha = self.create_game_with_players("ALPHA")
        game_beta_id, players_beta = self.create_game_with_players("BETA")

        payment_service = PaymentService(db_session)
        payment_date = datetime.now(timezone.utc)

        # Make different payments in each game
        payment_service.record_payment(game_alpha_id, players_alpha[0], players_alpha[1], Decimal("50.00"), payment_date, "Alpha", created_by="test")
        payment_service.record_payment(game_beta_id, players_beta[0], players_beta[1], Decimal("75.00"), payment_date, "Beta", created_by="test")

        # Force balance recalculation for game alpha only
        alpha_summaries = payment_service.get_payment_summary(game_alpha_id)

        # Get beta summaries to verify they weren't affected by alpha recalculation
        beta_summaries = payment_service.get_payment_summary(game_beta_id)

        # Verify correct amounts in each game
        alpha_payer = next(s for s in alpha_summaries if s.player_id == players_alpha[0])
        beta_payer = next(s for s in beta_summaries if s.player_id == players_beta[0])

        assert alpha_payer.total_paid == Decimal("50.00"), "Alpha game payment amount incorrect"
        assert beta_payer.total_paid == Decimal("75.00"), "Beta game payment amount incorrect"

        # CRITICAL: Verify no cross-contamination
        alpha_recipient = next(s for s in alpha_summaries if s.player_id == players_alpha[1])
        beta_recipient = next(s for s in beta_summaries if s.player_id == players_beta[1])

        assert alpha_recipient.total_received == Decimal("50.00")
        assert beta_recipient.total_received == Decimal("75.00")

    def test_settlement_isolation_between_games(self, db_session):
        """
        CRITICAL: Settlement suggestions must be completely isolated between games.
        """
        # Create games with different debt structures
        game_1_id, players_1 = self.create_game_with_players("SETT1", poker_results=[10000, -5000, -5000])
        game_2_id, players_2 = self.create_game_with_players("SETT2", poker_results=[8000, -3000, -5000])

        payment_service = PaymentService(db_session)

        # Get settlement suggestions for each game
        settlements_1 = payment_service.get_settlement_suggestions(game_1_id)
        settlements_2 = payment_service.get_settlement_suggestions(game_2_id)

        # Verify settlements only reference players from their respective games
        for settlement in settlements_1:
            assert settlement.payer_id in players_1, f"Game 1 settlement references external player: {settlement.payer_id}"
            assert settlement.recipient_id in players_1, f"Game 1 settlement references external player: {settlement.recipient_id}"

        for settlement in settlements_2:
            assert settlement.payer_id in players_2, f"Game 2 settlement references external player: {settlement.payer_id}"
            assert settlement.recipient_id in players_2, f"Game 2 settlement references external player: {settlement.recipient_id}"

        # Execute settlements in game 1 only
        payment_date = datetime.now(timezone.utc)
        for settlement in settlements_1:
            payment_service.record_payment(
                game_1_id, settlement.payer_id, settlement.recipient_id,
                settlement.amount, payment_date, "Settlement", created_by="test"
            )

        # Verify game 1 is settled
        game_1_final = payment_service.get_payment_summary(game_1_id)
        for summary in game_1_final:
            assert abs(summary.balance) < Decimal("0.01"), f"Game 1 player {summary.player_name} not settled"

        # CRITICAL: Verify game 2 is unaffected by game 1's settlements
        game_2_final = payment_service.get_payment_summary(game_2_id)
        for summary in game_2_final:
            if abs(summary.balance) > Decimal("0.01"):
                # Game 2 should still have unsettled balances
                pass
            # But none should show settlement payments
            assert summary.total_paid == Decimal("0.00"), "Game 2 affected by Game 1 settlements"
            assert summary.total_received == Decimal("0.00"), "Game 2 affected by Game 1 settlements"

    def test_database_constraint_isolation(self, db_session):
        """
        CRITICAL: Database constraints must prevent cross-game data corruption.
        """
        game_1_id, players_1 = self.create_game_with_players("CONSTRAINT1")
        game_2_id, players_2 = self.create_game_with_players("CONSTRAINT2")

        # Attempt to create payment with mismatched game and player
        # This should be prevented by application logic or database constraints
        payment_service = PaymentService(db_session)

        # Try to create payment in game 1 using player from game 2
        with pytest.raises((ValueError, Exception)):
            payment_service.record_payment(
                game_id=game_1_id,
                payer_id=players_2[0],  # Player from different game
                recipient_id=players_1[1],
                amount=Decimal("100.00"),
                payment_date=datetime.now(timezone.utc),
                payment_method="Invalid",
                created_by="test"
            )

        # Verify no corrupt data was created
        summaries_1 = payment_service.get_payment_summary(game_1_id)
        summaries_2 = payment_service.get_payment_summary(game_2_id)

        # All balances should be zero (no payments made)
        for summary in summaries_1 + summaries_2:
            assert summary.total_paid == Decimal("0.00")
            assert summary.total_received == Decimal("0.00")

    def test_payment_history_isolation(self, db_session):
        """
        CRITICAL: Payment history must be completely isolated between games.
        """
        game_1_id, players_1 = self.create_game_with_players("HIST1")
        game_2_id, players_2 = self.create_game_with_players("HIST2")

        payment_service = PaymentService(db_session)
        payment_date = datetime.now(timezone.utc)

        # Create payments in both games
        payment_service.record_payment(game_1_id, players_1[0], players_1[1], Decimal("25.00"), payment_date, "Game1Payment", created_by="test")
        payment_service.record_payment(game_2_id, players_2[0], players_2[1], Decimal("35.00"), payment_date, "Game2Payment", created_by="test")

        # Get payment history for each game
        history_1 = payment_service.get_payment_history(game_1_id)
        history_2 = payment_service.get_payment_history(game_2_id)

        # Verify each game only sees its own payments
        assert len(history_1) == 1, f"Game 1 should have 1 payment, got {len(history_1)}"
        assert len(history_2) == 1, f"Game 2 should have 1 payment, got {len(history_2)}"

        # Verify payment details are correct and isolated
        assert history_1[0]['amount'] == 25.00
        assert history_1[0]['payment_method'] == "Game1Payment"

        assert history_2[0]['amount'] == 35.00
        assert history_2[0]['payment_method'] == "Game2Payment"

        # Verify no cross-contamination in history
        assert "Game2Payment" not in str(history_1)
        assert "Game1Payment" not in str(history_2)