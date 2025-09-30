"""
Integration tests for Player Merge Service V2.

Tests the domain-driven player merging functionality.
"""

import pytest
from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy import text

from db.database import SessionLocal, engine
from db.models import Game, Player, Session, SessionPlayerSummary, GamePlayer
from services.player_merge_service_v2 import PlayerMergeServiceV2


class TestPlayerMergeV2:
    """Integration tests for player merge service."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Clean database before and after each test."""
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM session_player_summaries"))
            conn.execute(text("DELETE FROM sessions"))
            conn.execute(text("DELETE FROM game_players"))
            conn.execute(text("DELETE FROM players"))
            conn.execute(text("DELETE FROM games"))
            conn.commit()
        yield
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM session_player_summaries"))
            conn.execute(text("DELETE FROM sessions"))
            conn.execute(text("DELETE FROM game_players"))
            conn.execute(text("DELETE FROM players"))
            conn.execute(text("DELETE FROM games"))
            conn.commit()

    def create_test_game(self, db):
        """Helper to create a test game."""
        game = Game(
            public_code="TEST1",
            admin_code="admin-123",
            title="Test Game"
        )
        db.add(game)
        db.flush()
        return game

    def create_test_session(self, db, game_id):
        """Helper to create a test session."""
        session = Session(
            game_id=game_id,
            external_id=f"session-{game_id}",
            game_number=1,
            started_at=datetime.now(timezone.utc)
        )
        db.add(session)
        db.flush()
        return session

    def test_find_duplicates_exact_match(self):
        """Test finding duplicates with exact name match."""
        with SessionLocal() as db:
            game = self.create_test_game(db)
            session = self.create_test_session(db, game.id)

            # Create players with similar names
            player1 = Player(display_name="John Smith", external_id=None)
            player2 = Player(display_name="john smith", external_id=None)
            player3 = Player(display_name="Jane Doe", external_id=None)

            db.add_all([player1, player2, player3])
            db.flush()

            # Link players to game
            db.add_all([
                GamePlayer(game_id=game.id, player_id=player1.id),
                GamePlayer(game_id=game.id, player_id=player2.id),
                GamePlayer(game_id=game.id, player_id=player3.id)
            ])

            # Add session data
            db.add_all([
                SessionPlayerSummary(
                    session_id=session.id,
                    player_id=player1.id,
                    buy_in_sum=10000,
                    cash_out_sum=15000,
                    net=5000,
                    in_game=0,
                    names=["John Smith", "JSmith"]
                ),
                SessionPlayerSummary(
                    session_id=session.id,
                    player_id=player2.id,
                    buy_in_sum=10000,
                    cash_out_sum=8000,
                    net=-2000,
                    in_game=0,
                    names=["john smith"]
                )
            ])

            db.commit()

            # Find duplicates
            service = PlayerMergeServiceV2(db)
            result = service.find_potential_duplicates(
                game_id=str(game.id),
                verified_name="John Smith"
            )

            # Should find both players
            assert result['match_count'] >= 2
            assert result['verified_name'] == "John Smith"

            # Check that player1 and player2 are in results
            player_ids = [m['player_id'] for m in result['potential_matches']]
            assert str(player1.id) in player_ids
            assert str(player2.id) in player_ids

            # Jane Doe should not match (or have low score)
            jane_matches = [m for m in result['potential_matches'] if m['player_id'] == str(player3.id)]
            assert len(jane_matches) == 0 or jane_matches[0]['match_score'] < 30

    def test_merge_two_players_success(self):
        """Test successfully merging two players."""
        with SessionLocal() as db:
            game = self.create_test_game(db)
            session1 = self.create_test_session(db, game.id)
            session1.external_id = "session-1"
            db.flush()

            # Create target and source players
            target = Player(display_name="John Smith", external_id=None)
            source = Player(display_name="J Smith", external_id="john_venmo")

            db.add_all([target, source])
            db.flush()

            # Link to game
            db.add_all([
                GamePlayer(game_id=game.id, player_id=target.id),
                GamePlayer(game_id=game.id, player_id=source.id)
            ])

            # Add session summaries
            db.add_all([
                SessionPlayerSummary(
                    session_id=session1.id,
                    player_id=target.id,
                    buy_in_sum=10000,
                    cash_out_sum=15000,
                    net=5000,
                    in_game=0,
                    names=["John Smith"]
                ),
                SessionPlayerSummary(
                    session_id=session1.id,
                    player_id=source.id,
                    buy_in_sum=5000,
                    cash_out_sum=7000,
                    net=2000,
                    in_game=0,
                    names=["J Smith"]
                )
            ])

            db.commit()

            target_id = str(target.id)
            source_id = str(source.id)

            # Merge players
            service = PlayerMergeServiceV2(db)
            result = service.merge_players(
                target_player_id=target_id,
                source_player_ids=[source_id],
                verified_name="John Smith",
                external_id="john_venmo"
            )

            db.commit()

            # Verify result
            assert result['message'] == "Players merged successfully"
            assert result['merged_player_count'] == 1
            assert result['verified_name'] == "John Smith"
            assert result['external_id'] == "john_venmo"

            # Verify target player was updated
            updated_target = db.query(Player).filter(Player.id == target_id).first()
            assert updated_target is not None
            assert updated_target.display_name == "John Smith"
            assert updated_target.external_id == "john_venmo"

            # Verify source player was deleted
            deleted_source = db.query(Player).filter(Player.id == source_id).first()
            assert deleted_source is None

            # Verify session summaries were merged
            summaries = db.query(SessionPlayerSummary).filter(
                SessionPlayerSummary.player_id == target_id
            ).all()
            assert len(summaries) >= 1

            # Verify totals were combined
            total_buy_in = sum(s.buy_in_sum for s in summaries)
            total_cash_out = sum(s.cash_out_sum for s in summaries)
            assert total_buy_in == 15000  # 10000 + 5000
            assert total_cash_out == 22000  # 15000 + 7000

    def test_merge_with_duplicate_sessions(self):
        """Test merging players who both participated in the same session."""
        with SessionLocal() as db:
            game = self.create_test_game(db)
            session = self.create_test_session(db, game.id)

            # Create players (both in same session)
            target = Player(display_name="Player One", external_id=None)
            source = Player(display_name="Player 1", external_id=None)

            db.add_all([target, source])
            db.flush()

            # Link to game
            db.add_all([
                GamePlayer(game_id=game.id, player_id=target.id),
                GamePlayer(game_id=game.id, player_id=source.id)
            ])

            # Both players in same session (should merge stats)
            db.add_all([
                SessionPlayerSummary(
                    session_id=session.id,
                    player_id=target.id,
                    buy_in_sum=10000,
                    cash_out_sum=12000,
                    net=2000,
                    in_game=0,
                    names=["Player One"]
                ),
                SessionPlayerSummary(
                    session_id=session.id,
                    player_id=source.id,
                    buy_in_sum=5000,
                    cash_out_sum=6000,
                    net=1000,
                    in_game=0,
                    names=["Player 1"]
                )
            ])

            db.commit()

            target_id = str(target.id)
            source_id = str(source.id)

            # Merge players
            service = PlayerMergeServiceV2(db)
            result = service.merge_players(
                target_player_id=target_id,
                source_player_ids=[source_id],
                verified_name="Player One"
            )

            db.commit()

            # Should have only one summary for the session now
            summaries = db.query(SessionPlayerSummary).filter(
                SessionPlayerSummary.player_id == target_id,
                SessionPlayerSummary.session_id == session.id
            ).all()

            assert len(summaries) == 1

            # Stats should be combined
            merged_summary = summaries[0]
            assert merged_summary.buy_in_sum == 15000  # 10000 + 5000
            assert merged_summary.cash_out_sum == 18000  # 12000 + 6000
            assert merged_summary.net == 3000  # 2000 + 1000

            # Names should be combined (unique)
            assert "Player One" in merged_summary.names
            assert "Player 1" in merged_summary.names

    def test_merge_validation_target_not_found(self):
        """Test merge fails if target player doesn't exist."""
        with SessionLocal() as db:
            service = PlayerMergeServiceV2(db)

            with pytest.raises(ValueError, match="Target player not found"):
                service.merge_players(
                    target_player_id="00000000-0000-0000-0000-000000000000",
                    source_player_ids=["00000000-0000-0000-0000-000000000001"],
                    verified_name="Test Player"
                )

    def test_merge_validation_source_not_found(self):
        """Test merge fails if source player doesn't exist."""
        with SessionLocal() as db:
            game = self.create_test_game(db)

            # Create only target
            target = Player(display_name="Target", external_id=None)
            db.add(target)
            db.flush()

            db.add(GamePlayer(game_id=game.id, player_id=target.id))
            db.commit()

            service = PlayerMergeServiceV2(db)

            with pytest.raises(ValueError, match="Source player not found"):
                service.merge_players(
                    target_player_id=str(target.id),
                    source_player_ids=["00000000-0000-0000-0000-000000000001"],
                    verified_name="Test Player"
                )

    def test_exclude_player_from_duplicate_search(self):
        """Test excluding a player from duplicate search results."""
        with SessionLocal() as db:
            game = self.create_test_game(db)
            session = self.create_test_session(db, game.id)

            # Create players
            player1 = Player(display_name="John Smith", external_id=None)
            player2 = Player(display_name="John Smith", external_id=None)

            db.add_all([player1, player2])
            db.flush()

            db.add_all([
                GamePlayer(game_id=game.id, player_id=player1.id),
                GamePlayer(game_id=game.id, player_id=player2.id)
            ])

            db.add(SessionPlayerSummary(
                session_id=session.id,
                player_id=player1.id,
                buy_in_sum=10000,
                cash_out_sum=10000,
                net=0,
                in_game=0,
                names=["John Smith"]
            ))

            db.commit()

            # Find duplicates, excluding player1
            service = PlayerMergeServiceV2(db)
            result = service.find_potential_duplicates(
                game_id=str(game.id),
                verified_name="John Smith",
                exclude_player_id=str(player1.id)
            )

            # Should only find player2
            player_ids = [m['player_id'] for m in result['potential_matches']]
            assert str(player1.id) not in player_ids
            assert str(player2.id) in player_ids

    def test_merge_multiple_source_players(self):
        """Test merging multiple source players into one target."""
        with SessionLocal() as db:
            game = self.create_test_game(db)
            session1 = self.create_test_session(db, game.id)

            # Create second session
            session2 = Session(
                game_id=game.id,
                external_id="session-2",
                game_number=2,
                started_at=datetime.now(timezone.utc)
            )
            db.add(session2)
            db.flush()

            # Create target and multiple sources
            target = Player(display_name="John", external_id=None)
            source1 = Player(display_name="J Smith", external_id=None)
            source2 = Player(display_name="Johnny", external_id="john_venmo")

            db.add_all([target, source1, source2])
            db.flush()

            # Link to game
            db.add_all([
                GamePlayer(game_id=game.id, player_id=target.id),
                GamePlayer(game_id=game.id, player_id=source1.id),
                GamePlayer(game_id=game.id, player_id=source2.id)
            ])

            # Add session summaries
            db.add_all([
                SessionPlayerSummary(
                    session_id=session1.id,
                    player_id=target.id,
                    buy_in_sum=10000,
                    cash_out_sum=15000,
                    net=5000,
                    in_game=0,
                    names=["John"]
                ),
                SessionPlayerSummary(
                    session_id=session1.id,
                    player_id=source1.id,
                    buy_in_sum=5000,
                    cash_out_sum=4000,
                    net=-1000,
                    in_game=0,
                    names=["J Smith"]
                ),
                SessionPlayerSummary(
                    session_id=session2.id,
                    player_id=source2.id,
                    buy_in_sum=8000,
                    cash_out_sum=12000,
                    net=4000,
                    in_game=0,
                    names=["Johnny"]
                )
            ])

            db.commit()

            target_id = str(target.id)
            source1_id = str(source1.id)
            source2_id = str(source2.id)

            # Merge all sources into target
            service = PlayerMergeServiceV2(db)
            result = service.merge_players(
                target_player_id=target_id,
                source_player_ids=[source1_id, source2_id],
                verified_name="John Smith",
                external_id="john_venmo"
            )

            db.commit()

            # Verify result
            assert result['merged_player_count'] == 2
            assert result['merged_sessions'] == 2

            # Verify both sources deleted
            assert db.query(Player).filter(Player.id == source1_id).first() is None
            assert db.query(Player).filter(Player.id == source2_id).first() is None

            # Verify target has all sessions
            # Note: target and source1 both have session1, so they should be merged into 1 summary
            # source2 has session2, which is moved to target
            # Total: 2 summaries (merged session1 + moved session2)
            summaries = db.query(SessionPlayerSummary).filter(
                SessionPlayerSummary.player_id == target_id
            ).all()
            assert len(summaries) == 2

            # Verify totals
            total_buy_in = sum(s.buy_in_sum for s in summaries)
            total_cash_out = sum(s.cash_out_sum for s in summaries)
            assert total_buy_in == 23000  # 10000 + 5000 + 8000
            assert total_cash_out == 31000  # 15000 + 4000 + 12000

    def test_external_id_conflict_validation(self):
        """Test that merge fails if external_id already exists on another player."""
        with SessionLocal() as db:
            game = self.create_test_game(db)

            # Create three players
            target = Player(display_name="John", external_id=None)
            source = Player(display_name="J Smith", external_id=None)
            other = Player(display_name="Other Player", external_id="john_venmo")

            db.add_all([target, source, other])
            db.flush()

            db.add_all([
                GamePlayer(game_id=game.id, player_id=target.id),
                GamePlayer(game_id=game.id, player_id=source.id),
                GamePlayer(game_id=game.id, player_id=other.id)
            ])

            db.commit()

            service = PlayerMergeServiceV2(db)

            # Try to merge with external_id that belongs to another player
            with pytest.raises(ValueError, match="External ID .* is already assigned"):
                service.merge_players(
                    target_player_id=str(target.id),
                    source_player_ids=[str(source.id)],
                    verified_name="John Smith",
                    external_id="john_venmo"
                )

    def test_external_id_inheritance_from_source(self):
        """Test that target inherits external_id from source player."""
        with SessionLocal() as db:
            game = self.create_test_game(db)
            session = self.create_test_session(db, game.id)

            # Target has no external_id, source has one
            target = Player(display_name="John", external_id=None)
            source = Player(display_name="J Smith", external_id="john_venmo")

            db.add_all([target, source])
            db.flush()

            db.add_all([
                GamePlayer(game_id=game.id, player_id=target.id),
                GamePlayer(game_id=game.id, player_id=source.id)
            ])

            db.add_all([
                SessionPlayerSummary(
                    session_id=session.id,
                    player_id=target.id,
                    buy_in_sum=10000,
                    cash_out_sum=10000,
                    net=0,
                    in_game=0,
                    names=["John"]
                ),
                SessionPlayerSummary(
                    session_id=session.id,
                    player_id=source.id,
                    buy_in_sum=5000,
                    cash_out_sum=5000,
                    net=0,
                    in_game=0,
                    names=["J Smith"]
                )
            ])

            db.commit()

            # Merge without specifying external_id (should inherit)
            service = PlayerMergeServiceV2(db)
            result = service.merge_players(
                target_player_id=str(target.id),
                source_player_ids=[str(source.id)],
                verified_name="John Smith"
            )

            db.commit()

            # Verify target inherited external_id
            updated_target = db.query(Player).filter(Player.id == target.id).first()
            assert updated_target.external_id == "john_venmo"

    def test_audit_log_creation(self):
        """Test that merge operation creates proper audit log."""
        from db.models import AuditLog

        with SessionLocal() as db:
            game = self.create_test_game(db)
            session = self.create_test_session(db, game.id)

            target = Player(display_name="John", external_id=None)
            source = Player(display_name="J Smith", external_id=None)

            db.add_all([target, source])
            db.flush()

            db.add_all([
                GamePlayer(game_id=game.id, player_id=target.id),
                GamePlayer(game_id=game.id, player_id=source.id)
            ])

            db.add_all([
                SessionPlayerSummary(
                    session_id=session.id,
                    player_id=target.id,
                    buy_in_sum=10000,
                    cash_out_sum=10000,
                    net=0,
                    in_game=0,
                    names=["John"]
                )
            ])

            db.commit()

            target_id = str(target.id)

            # Perform merge
            service = PlayerMergeServiceV2(db)
            result = service.merge_players(
                target_player_id=target_id,
                source_player_ids=[str(source.id)],
                verified_name="John Smith",
                admin_code="admin-123",
                game_id=str(game.id)
            )

            db.commit()

            # Verify audit log exists
            audit_logs = db.query(AuditLog).filter(
                AuditLog.action == "PLAYER_MERGE",
                AuditLog.target_id == result['operation_id']
            ).all()

            assert len(audit_logs) == 1
            audit = audit_logs[0]
            assert audit.before is not None
            assert audit.after is not None
            assert 'target_player' in audit.before
            assert 'source_players' in audit.before

    def test_fuzzy_matching_contains(self):
        """Test fuzzy matching with 'contains' logic."""
        with SessionLocal() as db:
            game = self.create_test_game(db)
            session = self.create_test_session(db, game.id)

            # Create players with names that contain each other
            player1 = Player(display_name="John", external_id=None)
            player2 = Player(display_name="John Smith", external_id=None)
            player3 = Player(display_name="Johnny", external_id=None)

            db.add_all([player1, player2, player3])
            db.flush()

            db.add_all([
                GamePlayer(game_id=game.id, player_id=player1.id),
                GamePlayer(game_id=game.id, player_id=player2.id),
                GamePlayer(game_id=game.id, player_id=player3.id)
            ])

            db.add_all([
                SessionPlayerSummary(
                    session_id=session.id,
                    player_id=player1.id,
                    buy_in_sum=10000,
                    cash_out_sum=10000,
                    net=0,
                    in_game=0,
                    names=["John"]
                ),
                SessionPlayerSummary(
                    session_id=session.id,
                    player_id=player2.id,
                    buy_in_sum=10000,
                    cash_out_sum=10000,
                    net=0,
                    in_game=0,
                    names=["John Smith"]
                )
            ])

            db.commit()

            # Search for "John" should find both
            service = PlayerMergeServiceV2(db)
            result = service.find_potential_duplicates(
                game_id=str(game.id),
                verified_name="John"
            )

            # Should find players with "John" in name
            player_ids = [m['player_id'] for m in result['potential_matches']]
            assert str(player1.id) in player_ids
            assert str(player2.id) in player_ids

            # Check match scores
            matches_by_id = {m['player_id']: m for m in result['potential_matches']}
            player1_match = matches_by_id[str(player1.id)]
            player2_match = matches_by_id[str(player2.id)]

            # Both get high scores because both have "John" in session names
            # player1 has exact display name match (100) + exact session match (80) = capped at 100
            # player2 has contains display name match (60) + exact session match (80) = capped at 100
            assert player1_match['match_score'] == 100
            assert player2_match['match_score'] == 100

    def test_fuzzy_matching_session_names(self):
        """Test fuzzy matching using session names."""
        with SessionLocal() as db:
            game = self.create_test_game(db)
            session = self.create_test_session(db, game.id)

            # Player with different display name but matching session name
            player = Player(display_name="Player123", external_id=None)

            db.add(player)
            db.flush()

            db.add(GamePlayer(game_id=game.id, player_id=player.id))

            db.add(SessionPlayerSummary(
                session_id=session.id,
                player_id=player.id,
                buy_in_sum=10000,
                cash_out_sum=10000,
                net=0,
                in_game=0,
                names=["John Smith", "JSmith"]  # Session names match
            ))

            db.commit()

            # Search should find player via session name match
            service = PlayerMergeServiceV2(db)
            result = service.find_potential_duplicates(
                game_id=str(game.id),
                verified_name="John Smith"
            )

            # Should find player via session name
            player_ids = [m['player_id'] for m in result['potential_matches']]
            assert str(player.id) in player_ids

            # Should mention session name in match reasons
            match = result['potential_matches'][0]
            assert match['match_score'] >= 80  # Exact session name match

    def test_game_player_link_preservation(self):
        """Test that GamePlayer links are properly merged with date preservation."""
        with SessionLocal() as db:
            game = self.create_test_game(db)
            session = self.create_test_session(db, game.id)

            target = Player(display_name="John", external_id=None)
            source = Player(display_name="J Smith", external_id=None)

            db.add_all([target, source])
            db.flush()

            # Create game links with different dates
            earlier_date = datetime(2023, 1, 1, tzinfo=timezone.utc)
            later_date = datetime(2023, 6, 1, tzinfo=timezone.utc)

            db.add_all([
                GamePlayer(game_id=game.id, player_id=target.id, joined_at=later_date),
                GamePlayer(game_id=game.id, player_id=source.id, joined_at=earlier_date)
            ])

            db.add(SessionPlayerSummary(
                session_id=session.id,
                player_id=target.id,
                buy_in_sum=10000,
                cash_out_sum=10000,
                net=0,
                in_game=0,
                names=["John"]
            ))

            db.commit()

            # Merge players
            service = PlayerMergeServiceV2(db)
            service.merge_players(
                target_player_id=str(target.id),
                source_player_ids=[str(source.id)],
                verified_name="John Smith"
            )

            db.commit()

            # Verify GamePlayer link uses earlier date
            game_link = db.query(GamePlayer).filter(
                GamePlayer.game_id == game.id,
                GamePlayer.player_id == target.id
            ).first()

            assert game_link is not None
            assert game_link.joined_at == earlier_date