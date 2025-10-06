"""
Unit tests for LiveGameToSessionMapper

Tests the conversion logic from live game data to session format,
with special attention to dollar→cent conversion and data integrity.
"""

import pytest
from decimal import Decimal
from datetime import datetime, timezone
from uuid import uuid4

from services.live_game_to_session_mapper import LiveGameToSessionMapper
from domain.live_game.entities import LiveGame, LiveGameParticipant
from domain.live_game.value_objects import LiveGameId, ParticipantId, JoinCode
from domain.poker.value_objects import GameId, PlayerId
from domain.identity.value_objects import UserId


class TestLiveGameToSessionMapper:
    """Test suite for LiveGameToSessionMapper"""

    def test_dollars_to_cents_conversion(self):
        """Test accurate dollar to cent conversion"""
        mapper = LiveGameToSessionMapper()

        # Standard amounts
        assert mapper._dollars_to_cents(Decimal('10.50')) == 1050
        assert mapper._dollars_to_cents(Decimal('100.00')) == 10000
        assert mapper._dollars_to_cents(Decimal('0.01')) == 1
        assert mapper._dollars_to_cents(Decimal('0.00')) == 0

        # Edge cases
        assert mapper._dollars_to_cents(Decimal('0.99')) == 99
        assert mapper._dollars_to_cents(Decimal('1000.00')) == 100000
        assert mapper._dollars_to_cents(Decimal('0.50')) == 50

        # None handling
        assert mapper._dollars_to_cents(None) == 0

    def test_map_simple_live_game(self):
        """Test mapping a simple live game with one participant"""
        # Create live game
        live_game = LiveGame(
            id=LiveGameId(str(uuid4())),
            game_id=GameId(str(uuid4())),
            join_code=JoinCode('TEST'),
            created_by_user_id=UserId(str(uuid4())),
            status='closed',
            started_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            closed_at=datetime(2025, 1, 1, 18, 0, 0, tzinfo=timezone.utc),
            min_buy_in=Decimal('10.00'),
            max_buy_in=None,
            small_blind=None,
            big_blind=None
        )

        # Create participant
        user_id = UserId(str(uuid4()))
        participant = LiveGameParticipant(
            id=ParticipantId(str(uuid4())),
            live_game_id=live_game.id,
            user_id=user_id,
            display_name='Alice',
            player_id=None,
            joined_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        )

        # Create transaction stats
        transaction_stats = {
            str(participant.id): {
                'total_buy_ins': Decimal('100.00'),
                'total_cash_outs': Decimal('150.00'),
                'net_result': Decimal('50.00'),
                'chips_on_table': Decimal('0.00')
            }
        }

        # Map to session data
        session_data = LiveGameToSessionMapper.map_live_game_to_session_data(
            live_game, [participant], transaction_stats
        )

        # Verify structure
        assert session_data['sessionType'] == 'live'
        assert session_data['sessionName'] == 'Live Game TEST'
        assert session_data['sessionId'] == f"live_TEST_{int(live_game.started_at.timestamp())}"

        # Verify player data
        assert len(session_data['playersInfos']) == 1
        player_info = session_data['playersInfos'][0]

        assert player_info['id'] == str(user_id)
        assert player_info['name'] == 'Alice'
        assert player_info['validated_name'] == 'Alice'
        assert player_info['buyInSum'] == 10000  # $100.00 → 10000¢
        assert player_info['buyOutSum'] == 15000  # $150.00 → 15000¢
        assert player_info['inGame'] == 0  # $0.00 → 0¢
        assert player_info['net'] == 5000  # $50.00 → 5000¢
        assert player_info['names'] == ['Alice']

        # Verify metadata
        assert session_data['meta']['source'] == 'live_game'
        assert session_data['meta']['join_code'] == 'TEST'
        assert session_data['meta']['participant_count'] == 1

    def test_map_multiple_participants(self):
        """Test mapping a live game with multiple participants"""
        live_game = LiveGame(
            id=LiveGameId(str(uuid4())),
            game_id=GameId(str(uuid4())),
            join_code=JoinCode('MULT'),
            created_by_user_id=UserId(str(uuid4())),
            status='closed',
            started_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            closed_at=datetime(2025, 1, 1, 18, 0, 0, tzinfo=timezone.utc),
            min_buy_in=Decimal('10.00'),
            max_buy_in=None,
            small_blind=None,
            big_blind=None
        )

        # Create participants with different stats
        participant1 = LiveGameParticipant(
            id=ParticipantId(str(uuid4())),
            live_game_id=live_game.id,
            user_id=UserId(str(uuid4())),
            display_name='Alice',
            player_id=None,
            joined_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        )

        participant2 = LiveGameParticipant(
            id=ParticipantId(str(uuid4())),
            live_game_id=live_game.id,
            user_id=UserId(str(uuid4())),
            display_name='Bob',
            player_id=None,
            joined_at=datetime(2025, 1, 1, 12, 30, 0, tzinfo=timezone.utc)
        )

        participant3 = LiveGameParticipant(
            id=ParticipantId(str(uuid4())),
            live_game_id=live_game.id,
            user_id=UserId(str(uuid4())),
            display_name='Charlie',
            player_id=None,
            joined_at=datetime(2025, 1, 1, 13, 0, 0, tzinfo=timezone.utc)
        )

        # Create transaction stats
        transaction_stats = {
            str(participant1.id): {
                'total_buy_ins': Decimal('100.00'),
                'total_cash_outs': Decimal('150.00'),
                'net_result': Decimal('50.00'),
                'chips_on_table': Decimal('0.00')
            },
            str(participant2.id): {
                'total_buy_ins': Decimal('100.00'),
                'total_cash_outs': Decimal('75.00'),
                'net_result': Decimal('-25.00'),
                'chips_on_table': Decimal('0.00')
            },
            str(participant3.id): {
                'total_buy_ins': Decimal('100.00'),
                'total_cash_outs': Decimal('75.00'),
                'net_result': Decimal('-25.00'),
                'chips_on_table': Decimal('0.00')
            }
        }

        # Map to session data
        session_data = LiveGameToSessionMapper.map_live_game_to_session_data(
            live_game,
            [participant1, participant2, participant3],
            transaction_stats
        )

        # Verify all participants mapped
        assert len(session_data['playersInfos']) == 3

        # Verify Alice (winner)
        alice = next(p for p in session_data['playersInfos'] if p['name'] == 'Alice')
        assert alice['buyInSum'] == 10000
        assert alice['buyOutSum'] == 15000
        assert alice['net'] == 5000

        # Verify Bob (loser)
        bob = next(p for p in session_data['playersInfos'] if p['name'] == 'Bob')
        assert bob['buyInSum'] == 10000
        assert bob['buyOutSum'] == 7500
        assert bob['net'] == -2500

        # Verify Charlie (loser)
        charlie = next(p for p in session_data['playersInfos'] if p['name'] == 'Charlie')
        assert charlie['buyInSum'] == 10000
        assert charlie['buyOutSum'] == 7500
        assert charlie['net'] == -2500

        # Verify zero-sum (total net should be 0)
        total_net = sum(p['net'] for p in session_data['playersInfos'])
        assert total_net == 0  # 5000 + (-2500) + (-2500) = 0

    def test_map_with_fractional_cents(self):
        """Test that fractional cents are handled correctly"""
        live_game = LiveGame(
            id=LiveGameId(str(uuid4())),
            game_id=GameId(str(uuid4())),
            join_code=JoinCode('FRAC'),
            created_by_user_id=UserId(str(uuid4())),
            status='closed',
            started_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            closed_at=datetime(2025, 1, 1, 18, 0, 0, tzinfo=timezone.utc),
            min_buy_in=Decimal('10.00'),
            max_buy_in=None,
            small_blind=None,
            big_blind=None
        )

        participant = LiveGameParticipant(
            id=ParticipantId(str(uuid4())),
            live_game_id=live_game.id,
            user_id=UserId(str(uuid4())),
            display_name='Test User',
            player_id=None,
            joined_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        )

        # Test fractional dollar amounts
        transaction_stats = {
            str(participant.id): {
                'total_buy_ins': Decimal('50.50'),
                'total_cash_outs': Decimal('75.25'),
                'net_result': Decimal('24.75'),
                'chips_on_table': Decimal('0.00')
            }
        }

        session_data = LiveGameToSessionMapper.map_live_game_to_session_data(
            live_game, [participant], transaction_stats
        )

        player_info = session_data['playersInfos'][0]
        assert player_info['buyInSum'] == 5050  # $50.50 → 5050¢
        assert player_info['buyOutSum'] == 7525  # $75.25 → 7525¢
        assert player_info['net'] == 2475  # $24.75 → 2475¢

    def test_error_on_non_closed_game(self):
        """Test that mapping fails if game is not closed"""
        live_game = LiveGame(
            id=LiveGameId(str(uuid4())),
            game_id=GameId(str(uuid4())),
            join_code=JoinCode('OPEN'),
            created_by_user_id=UserId(str(uuid4())),
            status='active',  # Not closed!
            started_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            closed_at=None,
            min_buy_in=Decimal('10.00'),
            max_buy_in=None,
            small_blind=None,
            big_blind=None
        )

        participant = LiveGameParticipant(
            id=ParticipantId(str(uuid4())),
            live_game_id=live_game.id,
            user_id=UserId(str(uuid4())),
            display_name='Test',
            player_id=None,
            joined_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        )

        transaction_stats = {
            str(participant.id): {
                'total_buy_ins': Decimal('100.00'),
                'total_cash_outs': Decimal('100.00'),
                'net_result': Decimal('0.00'),
                'chips_on_table': Decimal('0.00')
            }
        }

        with pytest.raises(ValueError, match="non-closed live game"):
            LiveGameToSessionMapper.map_live_game_to_session_data(
                live_game, [participant], transaction_stats
            )

    def test_error_on_no_participants(self):
        """Test that mapping fails if there are no participants"""
        live_game = LiveGame(
            id=LiveGameId(str(uuid4())),
            game_id=GameId(str(uuid4())),
            join_code=JoinCode('NONE'),
            created_by_user_id=UserId(str(uuid4())),
            status='closed',
            started_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            closed_at=datetime(2025, 1, 1, 18, 0, 0, tzinfo=timezone.utc),
            min_buy_in=Decimal('10.00'),
            max_buy_in=None,
            small_blind=None,
            big_blind=None
        )

        with pytest.raises(ValueError, match="no participants"):
            LiveGameToSessionMapper.map_live_game_to_session_data(
                live_game, [], {}
            )

    def test_get_session_timestamp(self):
        """Test session timestamp selection logic"""
        mapper = LiveGameToSessionMapper()

        # With closed_at
        live_game_closed = LiveGame(
            id=LiveGameId(str(uuid4())),
            game_id=GameId(str(uuid4())),
            join_code=JoinCode('TIME'),
            created_by_user_id=UserId(str(uuid4())),
            status='closed',
            started_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            closed_at=datetime(2025, 1, 1, 18, 0, 0, tzinfo=timezone.utc),
            min_buy_in=Decimal('10.00'),
            max_buy_in=None,
            small_blind=None,
            big_blind=None
        )

        timestamp = mapper.get_session_timestamp(live_game_closed)
        assert timestamp == live_game_closed.closed_at

        # Without closed_at (fallback to started_at)
        live_game_active = LiveGame(
            id=LiveGameId(str(uuid4())),
            game_id=GameId(str(uuid4())),
            join_code=JoinCode('TIME'),
            created_by_user_id=UserId(str(uuid4())),
            status='active',
            started_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            closed_at=None,
            min_buy_in=Decimal('10.00'),
            max_buy_in=None,
            small_blind=None,
            big_blind=None
        )

        timestamp = mapper.get_session_timestamp(live_game_active)
        assert timestamp == live_game_active.started_at

    def test_map_with_claimed_player_identity(self):
        """Test that participants with claimed player identities use the claimed player's external_id and name"""
        live_game = LiveGame(
            id=LiveGameId(str(uuid4())),
            game_id=GameId(str(uuid4())),
            join_code=JoinCode('CLAM'),
            created_by_user_id=UserId(str(uuid4())),
            status='closed',
            started_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            closed_at=datetime(2025, 1, 1, 18, 0, 0, tzinfo=timezone.utc),
            min_buy_in=Decimal('10.00'),
            max_buy_in=None,
            small_blind=None,
            big_blind=None
        )

        # Create participant WITH claimed player identity
        user_id = UserId(str(uuid4()))
        player_id = PlayerId(str(uuid4()))
        participant_claimed = LiveGameParticipant(
            id=ParticipantId(str(uuid4())),
            live_game_id=live_game.id,
            user_id=user_id,
            display_name='Eric Dunbar',  # Their user account name
            player_id=player_id,  # Has claimed a player
            joined_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            claimed_player_external_id='existing-player-123',  # Claimed player's external_id
            claimed_player_name='Eric'  # Claimed player's name
        )

        # Create participant WITHOUT claimed player identity (for comparison)
        participant_unclaimed = LiveGameParticipant(
            id=ParticipantId(str(uuid4())),
            live_game_id=live_game.id,
            user_id=UserId(str(uuid4())),
            display_name='Bob',
            player_id=None,  # No claimed player
            joined_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            claimed_player_external_id=None,
            claimed_player_name=None
        )

        # Create transaction stats
        transaction_stats = {
            str(participant_claimed.id): {
                'total_buy_ins': Decimal('100.00'),
                'total_cash_outs': Decimal('120.00'),
                'net_result': Decimal('20.00'),
                'chips_on_table': Decimal('0.00')
            },
            str(participant_unclaimed.id): {
                'total_buy_ins': Decimal('100.00'),
                'total_cash_outs': Decimal('80.00'),
                'net_result': Decimal('-20.00'),
                'chips_on_table': Decimal('0.00')
            }
        }

        # Map to session data
        session_data = LiveGameToSessionMapper.map_live_game_to_session_data(
            live_game,
            [participant_claimed, participant_unclaimed],
            transaction_stats
        )

        # Verify we have 2 players
        assert len(session_data['playersInfos']) == 2

        # Find the claimed participant's player info
        claimed_player_info = next(p for p in session_data['playersInfos'] if 'Eric' in p['name'])

        # CRITICAL: Should use claimed player's external_id, NOT user_id
        assert claimed_player_info['id'] == 'existing-player-123'
        assert claimed_player_info['name'] == 'Eric'
        assert claimed_player_info['validated_name'] == 'Eric'
        assert claimed_player_info['names'] == ['Eric']
        assert claimed_player_info['buyInSum'] == 10000
        assert claimed_player_info['buyOutSum'] == 12000
        assert claimed_player_info['net'] == 2000

        # Find the unclaimed participant's player info
        unclaimed_player_info = next(p for p in session_data['playersInfos'] if p['name'] == 'Bob')

        # Should use user_id as external_id (fallback behavior)
        assert unclaimed_player_info['id'] == str(participant_unclaimed.user_id)
        assert unclaimed_player_info['name'] == 'Bob'
        assert unclaimed_player_info['validated_name'] == 'Bob'
        assert unclaimed_player_info['names'] == ['Bob']
        assert unclaimed_player_info['buyInSum'] == 10000
        assert unclaimed_player_info['buyOutSum'] == 8000
        assert unclaimed_player_info['net'] == -2000
