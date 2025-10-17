"""
Integration tests for Live Game Service layer.

Tests the complete Live Game workflow including:
- Game creation and validation
- Participant management
- Transaction lifecycle (buy-in/cash-out)
- Permission checks
- Game closure
"""

import pytest
from decimal import Decimal
from uuid import uuid4

from domain.live_game import LiveGameService, LiveGamePermissionService
from domain.live_game.value_objects import LiveGameId, ParticipantId, TransactionId
from domain.live_game.exceptions import (
    ActiveLiveGameExistsError,
    InvalidJoinCodeError,
    LiveGameNotFoundError,
    LiveGameAlreadyClosedError,
    ParticipantAlreadyJoinedError,
    ParticipantNotFoundError,
    InvalidBuyInAmountError,
    InvalidCashOutAmountError,
    TransactionNotFoundError,
    TransactionNotPendingError,
    UnauthorizedApprovalError,
    GameNotBalancedError,
    PlayersStillActiveError
)
from domain.identity.value_objects import UserId
from domain.poker.value_objects import GameId
from infrastructure.persistence.sqlalchemy import (
    SQLAlchemyLiveGameRepository,
    SQLAlchemyParticipantRepository,
    SQLAlchemyTransactionRepository
)
from db.models import Game as GameModel, User as UserModel


@pytest.fixture
def test_user_id(db_session):
    """Create a test user in the database"""
    user = UserModel(
        id=str(uuid4()),
        email=f"test_{uuid4()}@example.com",
        password_hash="hashed_password",
        display_name="Test User"
    )
    db_session.add(user)
    db_session.commit()
    return UserId(user.id)


@pytest.fixture
def test_game_id(db_session, test_user_id):
    """Create a test game in the database"""
    game = GameModel(
        id=str(uuid4()),
        public_code=f"TEST{uuid4().hex[:4]}",  # Unique public code
        admin_code=f"ADMIN_{uuid4()}",  # Unique admin code
        owner_user_id=str(test_user_id)
    )
    db_session.add(game)
    db_session.commit()
    return GameId(game.id)


@pytest.fixture
def live_game_service(db_session):
    """Create LiveGameService with all dependencies"""
    live_game_repo = SQLAlchemyLiveGameRepository(db_session)
    participant_repo = SQLAlchemyParticipantRepository(db_session)
    transaction_repo = SQLAlchemyTransactionRepository(db_session)

    return LiveGameService(
        live_game_repo=live_game_repo,
        participant_repo=participant_repo,
        transaction_repo=transaction_repo
    )


@pytest.fixture
def permission_service(db_session):
    """Create LiveGamePermissionService"""
    live_game_repo = SQLAlchemyLiveGameRepository(db_session)
    return LiveGamePermissionService(live_game_repo=live_game_repo)


# ============================================================================
# Game Creation Tests
# ============================================================================

def test_create_live_game_success(live_game_service, test_game_id, test_user_id, db_session):
    """Successfully create a live game with valid parameters"""
    live_game = live_game_service.create_live_game(
        game_id=test_game_id,
        created_by_user_id=test_user_id,
        min_buy_in=Decimal('10.00')
    )

    assert live_game.id is not None
    assert live_game.game_id == test_game_id
    assert live_game.created_by_user_id == test_user_id
    assert live_game.status == 'active'
    assert len(live_game.join_code.value) == 4
    assert live_game.min_buy_in == Decimal('10.00')
    assert live_game.max_buy_in is None
    assert live_game.small_blind is None
    assert live_game.big_blind is None


def test_create_live_game_with_all_options(live_game_service, test_game_id, test_user_id, db_session):
    """Create live game with all optional parameters"""
    live_game = live_game_service.create_live_game(
        game_id=test_game_id,
        created_by_user_id=test_user_id,
        small_blind=Decimal('0.50'),
        big_blind=Decimal('1.00'),
        min_buy_in=Decimal('10.00'),
        max_buy_in=Decimal('100.00')
    )

    assert live_game.small_blind == Decimal('0.50')
    assert live_game.big_blind == Decimal('1.00')
    assert live_game.min_buy_in == Decimal('10.00')
    assert live_game.max_buy_in == Decimal('100.00')


def test_create_live_game_when_active_exists(live_game_service, test_game_id, test_user_id, db_session):
    """Cannot create second live game when one is already active"""
    # Create first live game
    first_game = live_game_service.create_live_game(
        game_id=test_game_id,
        created_by_user_id=test_user_id,
        min_buy_in=Decimal('10.00')
    )

    # Try to create second - should fail
    with pytest.raises(ActiveLiveGameExistsError) as exc_info:
        live_game_service.create_live_game(
            game_id=test_game_id,
            created_by_user_id=test_user_id,
            min_buy_in=Decimal('20.00')
        )

    assert first_game.join_code.value in str(exc_info.value)


def test_create_second_live_game_after_first_closed(live_game_service, test_game_id, test_user_id, db_session):
    """Can create new live game after previous one is closed"""
    # Create and close first game
    first_game = live_game_service.create_live_game(
        game_id=test_game_id,
        created_by_user_id=test_user_id,
        min_buy_in=Decimal('10.00')
    )

    # Manually close it (bypass validation for test)
    live_game_repo = SQLAlchemyLiveGameRepository(db_session)
    first_game_entity = live_game_repo.get_by_id(first_game.id)
    first_game_entity.close()
    live_game_repo.update(first_game_entity)
    db_session.commit()

    # Create second game - should succeed
    second_game = live_game_service.create_live_game(
        game_id=test_game_id,
        created_by_user_id=test_user_id,
        min_buy_in=Decimal('20.00')
    )

    assert second_game.id != first_game.id
    assert second_game.join_code.value != first_game.join_code.value


# ============================================================================
# Participant Management Tests
# ============================================================================

def test_join_live_game_success(live_game_service, test_game_id, test_user_id, db_session):
    """User successfully joins a live game"""
    live_game = live_game_service.create_live_game(
        game_id=test_game_id,
        created_by_user_id=test_user_id,
        min_buy_in=Decimal('10.00')
    )

    participant = live_game_service.join_live_game(
        live_game_id=live_game.id,
        user_id=test_user_id,
        display_name="Test Player"
    )

    assert participant.id is not None
    assert participant.live_game_id == live_game.id
    assert participant.user_id == test_user_id
    assert participant.display_name == "Test Player"
    assert participant.joined_at is not None


def test_join_live_game_twice(live_game_service, test_game_id, test_user_id, db_session):
    """Cannot join the same live game twice with same user"""
    live_game = live_game_service.create_live_game(
        game_id=test_game_id,
        created_by_user_id=test_user_id,
        min_buy_in=Decimal('10.00')
    )

    # First join succeeds
    live_game_service.join_live_game(
        live_game_id=live_game.id,
        user_id=test_user_id,
        display_name="Test Player"
    )

    # Second join fails
    with pytest.raises(ParticipantAlreadyJoinedError):
        live_game_service.join_live_game(
            live_game_id=live_game.id,
            user_id=test_user_id,
            display_name="Test Player"
        )


def test_join_closed_game(live_game_service, test_game_id, test_user_id, db_session):
    """Cannot join a closed live game"""
    live_game = live_game_service.create_live_game(
        game_id=test_game_id,
        created_by_user_id=test_user_id,
        min_buy_in=Decimal('10.00')
    )

    # Close the game
    live_game_repo = SQLAlchemyLiveGameRepository(db_session)
    game_entity = live_game_repo.get_by_id(live_game.id)
    game_entity.close()
    live_game_repo.update(game_entity)
    db_session.commit()

    # Try to join
    with pytest.raises(LiveGameAlreadyClosedError):
        live_game_service.join_live_game(
            live_game_id=live_game.id,
            user_id=test_user_id,
            display_name="Test Player"
        )


# ============================================================================
# Buy-In Tests
# ============================================================================

def test_buy_in_success(live_game_service, test_game_id, test_user_id, db_session):
    """Successfully request a buy-in"""
    live_game = live_game_service.create_live_game(
        game_id=test_game_id,
        created_by_user_id=test_user_id,
        min_buy_in=Decimal('10.00'),
        max_buy_in=Decimal('100.00')
    )

    live_game_service.join_live_game(
        live_game_id=live_game.id,
        user_id=test_user_id,
        display_name="Test Player"
    )

    transaction = live_game_service.request_buy_in(
        live_game_id=live_game.id,
        user_id=test_user_id,
        amount=Decimal('50.00')
    )

    assert transaction.id is not None
    assert transaction.live_game_id == live_game.id
    assert transaction.user_id == test_user_id
    assert transaction.transaction_type == 'buy_in'
    assert transaction.amount == Decimal('50.00')
    assert transaction.status == 'pending'


def test_buy_in_below_minimum(live_game_service, test_game_id, test_user_id, db_session):
    """Cannot buy in below minimum amount"""
    live_game = live_game_service.create_live_game(
        game_id=test_game_id,
        created_by_user_id=test_user_id,
        min_buy_in=Decimal('10.00')
    )

    live_game_service.join_live_game(
        live_game_id=live_game.id,
        user_id=test_user_id,
        display_name="Test Player"
    )

    with pytest.raises(InvalidBuyInAmountError) as exc_info:
        live_game_service.request_buy_in(
            live_game_id=live_game.id,
            user_id=test_user_id,
            amount=Decimal('5.00')
        )

    assert "at least $10.00" in str(exc_info.value)


def test_buy_in_above_maximum(live_game_service, test_game_id, test_user_id, db_session):
    """Cannot buy in above maximum amount"""
    live_game = live_game_service.create_live_game(
        game_id=test_game_id,
        created_by_user_id=test_user_id,
        min_buy_in=Decimal('10.00'),
        max_buy_in=Decimal('100.00')
    )

    live_game_service.join_live_game(
        live_game_id=live_game.id,
        user_id=test_user_id,
        display_name="Test Player"
    )

    with pytest.raises(InvalidBuyInAmountError) as exc_info:
        live_game_service.request_buy_in(
            live_game_id=live_game.id,
            user_id=test_user_id,
            amount=Decimal('150.00')
        )

    assert "$150.00" in str(exc_info.value) and "$100.00" in str(exc_info.value)


def test_buy_in_without_joining(live_game_service, test_game_id, test_user_id, db_session):
    """Cannot request buy-in without joining first"""
    live_game = live_game_service.create_live_game(
        game_id=test_game_id,
        created_by_user_id=test_user_id,
        min_buy_in=Decimal('10.00')
    )

    with pytest.raises(ParticipantNotFoundError):
        live_game_service.request_buy_in(
            live_game_id=live_game.id,
            user_id=test_user_id,
            amount=Decimal('50.00')
        )


# ============================================================================
# Cash-Out Tests
# ============================================================================

def test_cash_out_success(live_game_service, test_game_id, test_user_id, db_session):
    """Successfully request a cash-out"""
    live_game = live_game_service.create_live_game(
        game_id=test_game_id,
        created_by_user_id=test_user_id,
        min_buy_in=Decimal('10.00')
    )

    live_game_service.join_live_game(
        live_game_id=live_game.id,
        user_id=test_user_id,
        display_name="Test Player"
    )

    # Buy-in and approve
    buy_in = live_game_service.request_buy_in(
        live_game_id=live_game.id,
        user_id=test_user_id,
        amount=Decimal('100.00')
    )

    live_game_service.approve_transaction(
        transaction_id=buy_in.id,
        approved_by_user_id=test_user_id
    )

    db_session.commit()

    # Cash-out
    transaction = live_game_service.request_cash_out(
        live_game_id=live_game.id,
        user_id=test_user_id,
        amount=Decimal('75.00')
    )

    assert transaction.transaction_type == 'cash_out'
    assert transaction.amount == Decimal('75.00')
    assert transaction.status == 'pending'


def test_cash_out_after_winning(live_game_service, test_game_id, test_user_id, db_session):
    """Player can cash out more than buy-in amount (winning scenario)

    CRITICAL: After cash-out is approved, chips_on_table = $0 (player left!)
    """
    live_game = live_game_service.create_live_game(
        game_id=test_game_id,
        created_by_user_id=test_user_id,
        min_buy_in=Decimal('10.00')
    )

    participant = live_game_service.join_live_game(
        live_game_id=live_game.id,
        user_id=test_user_id,
        display_name="Test Player"
    )

    # Buy-in and approve
    buy_in = live_game_service.request_buy_in(
        live_game_id=live_game.id,
        user_id=test_user_id,
        amount=Decimal('100.00')
    )

    live_game_service.approve_transaction(
        transaction_id=buy_in.id,
        approved_by_user_id=test_user_id
    )

    db_session.commit()

    # Before cash-out: player has $100 on table
    participants = live_game_service.get_participants(live_game.id)
    assert participants[0]['stats']['chips_on_table'] == Decimal('100.00')
    assert participants[0]['stats']['has_cashed_out'] is False

    # Player wins chips and cashes out more than buy-in
    # This is now allowed - admin verifies actual chip count
    cash_out = live_game_service.request_cash_out(
        live_game_id=live_game.id,
        user_id=test_user_id,
        amount=Decimal('390.00')  # Won $290
    )

    assert cash_out.transaction_type == 'cash_out'
    assert cash_out.amount == Decimal('390.00')
    assert cash_out.status == 'pending'

    # Approve cash-out
    live_game_service.approve_transaction(
        transaction_id=cash_out.id,
        approved_by_user_id=test_user_id
    )

    db_session.commit()

    # CRITICAL: After cash-out, chips_on_table = $0 (player left!)
    participants = live_game_service.get_participants(live_game.id)
    assert participants[0]['stats']['chips_on_table'] == Decimal('0.00')
    assert participants[0]['stats']['total_buy_ins'] == Decimal('100.00')
    assert participants[0]['stats']['total_cash_outs'] == Decimal('390.00')
    assert participants[0]['stats']['net_result'] == Decimal('290.00')  # $390 - $100
    assert participants[0]['stats']['has_cashed_out'] is True


def test_cash_out_after_losing(live_game_service, test_game_id, test_user_id, db_session):
    """Player can cash out less than buy-in amount (losing scenario)

    CRITICAL: After cash-out is approved, chips_on_table = $0 (player left!)
    """
    live_game = live_game_service.create_live_game(
        game_id=test_game_id,
        created_by_user_id=test_user_id,
        min_buy_in=Decimal('10.00')
    )

    live_game_service.join_live_game(
        live_game_id=live_game.id,
        user_id=test_user_id,
        display_name="Test Player"
    )

    # Buy-in and approve
    buy_in = live_game_service.request_buy_in(
        live_game_id=live_game.id,
        user_id=test_user_id,
        amount=Decimal('200.00')
    )

    live_game_service.approve_transaction(
        transaction_id=buy_in.id,
        approved_by_user_id=test_user_id
    )

    db_session.commit()

    # Player loses chips and cashes out less than buy-in
    # This reflects actual chip count after losses
    cash_out = live_game_service.request_cash_out(
        live_game_id=live_game.id,
        user_id=test_user_id,
        amount=Decimal('10.00')  # Lost $190
    )

    assert cash_out.transaction_type == 'cash_out'
    assert cash_out.amount == Decimal('10.00')
    assert cash_out.status == 'pending'

    # Approve cash-out
    live_game_service.approve_transaction(
        transaction_id=cash_out.id,
        approved_by_user_id=test_user_id
    )

    db_session.commit()

    # CRITICAL: After cash-out, chips_on_table = $0 (player left!)
    participants = live_game_service.get_participants(live_game.id)
    assert participants[0]['stats']['chips_on_table'] == Decimal('0.00')
    assert participants[0]['stats']['total_buy_ins'] == Decimal('200.00')
    assert participants[0]['stats']['total_cash_outs'] == Decimal('10.00')
    assert participants[0]['stats']['net_result'] == Decimal('-190.00')  # $10 - $200
    assert participants[0]['stats']['has_cashed_out'] is True


def test_cash_out_zero_allowed(live_game_service, test_game_id, test_user_id, db_session):
    """Can cash out $0 (busted player scenario)"""
    live_game = live_game_service.create_live_game(
        game_id=test_game_id,
        created_by_user_id=test_user_id,
        min_buy_in=Decimal('10.00')
    )

    live_game_service.join_live_game(
        live_game_id=live_game.id,
        user_id=test_user_id,
        display_name="Test Player"
    )

    # Player busted out, cashes out $0
    cash_out = live_game_service.request_cash_out(
        live_game_id=live_game.id,
        user_id=test_user_id,
        amount=Decimal('0.00')
    )

    assert cash_out.amount == Decimal('0.00')
    assert cash_out.status == 'pending'


def test_cash_out_negative_rejected(live_game_service, test_game_id, test_user_id, db_session):
    """Cannot cash out negative amounts"""
    live_game = live_game_service.create_live_game(
        game_id=test_game_id,
        created_by_user_id=test_user_id,
        min_buy_in=Decimal('10.00')
    )

    live_game_service.join_live_game(
        live_game_id=live_game.id,
        user_id=test_user_id,
        display_name="Test Player"
    )

    # Try to cash out negative
    with pytest.raises(ValueError, match="cannot be negative"):
        live_game_service.request_cash_out(
            live_game_id=live_game.id,
            user_id=test_user_id,
            amount=Decimal('-10.00')
        )


def test_cannot_cash_out_twice(live_game_service, test_game_id, test_user_id, db_session):
    """Cannot cash out twice - player already left the table!"""
    from domain.live_game.exceptions import LiveGameError

    live_game = live_game_service.create_live_game(
        game_id=test_game_id,
        created_by_user_id=test_user_id,
        min_buy_in=Decimal('10.00')
    )

    live_game_service.join_live_game(
        live_game_id=live_game.id,
        user_id=test_user_id,
        display_name="Test Player"
    )

    # Buy-in and approve
    buy_in = live_game_service.request_buy_in(
        live_game_id=live_game.id,
        user_id=test_user_id,
        amount=Decimal('100.00')
    )

    live_game_service.approve_transaction(
        transaction_id=buy_in.id,
        approved_by_user_id=test_user_id
    )

    db_session.commit()

    # First cash-out
    cash_out = live_game_service.request_cash_out(
        live_game_id=live_game.id,
        user_id=test_user_id,
        amount=Decimal('75.00')
    )

    live_game_service.approve_transaction(
        transaction_id=cash_out.id,
        approved_by_user_id=test_user_id
    )

    db_session.commit()

    # Try to cash out again - should fail!
    with pytest.raises(LiveGameError, match="already cashed out"):
        live_game_service.request_cash_out(
            live_game_id=live_game.id,
            user_id=test_user_id,
            amount=Decimal('10.00')
        )


# ============================================================================
# Transaction Lifecycle Tests
# ============================================================================

def test_approve_transaction_updates_balance(live_game_service, test_game_id, test_user_id, db_session):
    """Approving transaction updates participant balance"""
    live_game = live_game_service.create_live_game(
        game_id=test_game_id,
        created_by_user_id=test_user_id,
        min_buy_in=Decimal('10.00')
    )

    participant = live_game_service.join_live_game(
        live_game_id=live_game.id,
        user_id=test_user_id,
        display_name="Test Player"
    )

    # Request buy-in
    transaction = live_game_service.request_buy_in(
        live_game_id=live_game.id,
        user_id=test_user_id,
        amount=Decimal('100.00')
    )

    # Approve
    approved = live_game_service.approve_transaction(
        transaction_id=transaction.id,
        approved_by_user_id=test_user_id
    )

    assert approved.status == 'approved'
    assert approved.approved_by_user_id == test_user_id
    assert approved.approved_at is not None

    # Check participant stats
    participants = live_game_service.get_participants(live_game.id)
    assert len(participants) == 1
    assert participants[0]['stats']['chips_on_table'] == Decimal('100.00')
    assert participants[0]['stats']['total_buy_ins'] == Decimal('100.00')


def test_reject_transaction(live_game_service, test_game_id, test_user_id, db_session):
    """Rejecting transaction sets status and reason"""
    live_game = live_game_service.create_live_game(
        game_id=test_game_id,
        created_by_user_id=test_user_id,
        min_buy_in=Decimal('10.00')
    )

    live_game_service.join_live_game(
        live_game_id=live_game.id,
        user_id=test_user_id,
        display_name="Test Player"
    )

    transaction = live_game_service.request_buy_in(
        live_game_id=live_game.id,
        user_id=test_user_id,
        amount=Decimal('50.00')
    )

    # Reject
    rejected = live_game_service.reject_transaction(
        transaction_id=transaction.id,
        rejected_by_user_id=test_user_id,
        reason="Incorrect amount"
    )

    assert rejected.status == 'rejected'
    assert rejected.approved_by_user_id == test_user_id  # Uses same field for rejections
    assert rejected.notes == "Incorrect amount"  # Rejection reason stored in notes


def test_cannot_approve_rejected_transaction(live_game_service, test_game_id, test_user_id, db_session):
    """Cannot approve a transaction that was already rejected"""
    live_game = live_game_service.create_live_game(
        game_id=test_game_id,
        created_by_user_id=test_user_id,
        min_buy_in=Decimal('10.00')
    )

    live_game_service.join_live_game(
        live_game_id=live_game.id,
        user_id=test_user_id,
        display_name="Test Player"
    )

    transaction = live_game_service.request_buy_in(
        live_game_id=live_game.id,
        user_id=test_user_id,
        amount=Decimal('50.00')
    )

    # Reject first
    live_game_service.reject_transaction(
        transaction_id=transaction.id,
        rejected_by_user_id=test_user_id,
        reason="Test"
    )

    # Try to approve
    with pytest.raises(TransactionNotPendingError):
        live_game_service.approve_transaction(
            transaction_id=transaction.id,
            approved_by_user_id=test_user_id
        )


# ============================================================================
# Game Closure Tests
# ============================================================================

def test_close_game_players_still_active(live_game_service, test_game_id, test_user_id, db_session):
    """Cannot close game if players still have chips"""
    live_game = live_game_service.create_live_game(
        game_id=test_game_id,
        created_by_user_id=test_user_id,
        min_buy_in=Decimal('10.00')
    )

    live_game_service.join_live_game(
        live_game_id=live_game.id,
        user_id=test_user_id,
        display_name="Test Player"
    )

    # Buy-in and approve (player has chips)
    transaction = live_game_service.request_buy_in(
        live_game_id=live_game.id,
        user_id=test_user_id,
        amount=Decimal('100.00')
    )

    live_game_service.approve_transaction(
        transaction_id=transaction.id,
        approved_by_user_id=test_user_id
    )

    db_session.commit()

    # Try to close
    with pytest.raises(PlayersStillActiveError) as exc_info:
        live_game_service.close_live_game(live_game.id)

    assert "1 player(s) still have chips" in str(exc_info.value)


def test_close_game_success(live_game_service, test_game_id, test_user_id, db_session):
    """Successfully close a balanced game"""
    live_game = live_game_service.create_live_game(
        game_id=test_game_id,
        created_by_user_id=test_user_id,
        min_buy_in=Decimal('10.00')
    )

    live_game_service.join_live_game(
        live_game_id=live_game.id,
        user_id=test_user_id,
        display_name="Test Player"
    )

    # Buy-in, approve, cash-out, approve
    buy_in = live_game_service.request_buy_in(
        live_game_id=live_game.id,
        user_id=test_user_id,
        amount=Decimal('100.00')
    )

    live_game_service.approve_transaction(
        transaction_id=buy_in.id,
        approved_by_user_id=test_user_id
    )

    db_session.commit()

    cash_out = live_game_service.request_cash_out(
        live_game_id=live_game.id,
        user_id=test_user_id,
        amount=Decimal('100.00')
    )

    live_game_service.approve_transaction(
        transaction_id=cash_out.id,
        approved_by_user_id=test_user_id
    )

    db_session.commit()

    # Close game
    closed_game = live_game_service.close_live_game(live_game.id)

    assert closed_game.status == 'closed'
    assert closed_game.closed_at is not None


def test_close_already_closed_game(live_game_service, test_game_id, test_user_id, db_session):
    """Cannot close a game that's already closed"""
    live_game = live_game_service.create_live_game(
        game_id=test_game_id,
        created_by_user_id=test_user_id,
        min_buy_in=Decimal('10.00')
    )

    # Manually close
    live_game_repo = SQLAlchemyLiveGameRepository(db_session)
    game_entity = live_game_repo.get_by_id(live_game.id)
    game_entity.close()
    live_game_repo.update(game_entity)
    db_session.commit()

    # Try to close again
    with pytest.raises(LiveGameAlreadyClosedError):
        live_game_service.close_live_game(live_game.id)
