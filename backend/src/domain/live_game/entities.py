"""
Domain entities for live game feature.

This module defines the core domain entities for real-time live poker game tracking,
including LiveGame (the game session), LiveGameParticipant (players in the session),
and LiveGameTransaction (buy-ins and cash-outs).
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from domain.identity.value_objects import UserId
from domain.poker.value_objects import GameId, PlayerId
from .value_objects import LiveGameId, ParticipantId, TransactionId, JoinCode


@dataclass
class LiveGame:
    """
    Domain entity for a live poker game session.

    A LiveGame represents an active poker game where users can join and log
    their buy-ins and cash-outs in real-time. Each live game belongs to a
    parent Game and has a unique join code for easy access.

    Business Rules:
    - Only one active live game per parent game at a time
    - Live games can be closed by the creator
    - Join codes are unique across all active games

    Attributes:
        id: Unique identifier (None for new entities)
        game_id: Parent game this live session belongs to
        created_by_user_id: User who created the live game
        join_code: 4-character code for joining
        status: 'active' or 'closed'
        small_blind: Optional small blind amount
        big_blind: Optional big blind amount
        min_buy_in: Minimum buy-in amount (default $10)
        max_buy_in: Optional maximum buy-in amount
        started_at: When the live game was created
        closed_at: When the live game was closed (None if active)
    """
    id: Optional[LiveGameId]
    game_id: GameId
    created_by_user_id: UserId
    join_code: JoinCode
    status: str  # 'active' or 'closed'
    small_blind: Optional[Decimal]
    big_blind: Optional[Decimal]
    min_buy_in: Decimal
    max_buy_in: Optional[Decimal]
    started_at: datetime
    closed_at: Optional[datetime]

    @staticmethod
    def create_new(
        game_id: GameId,
        created_by_user_id: UserId,
        join_code: JoinCode,
        small_blind: Optional[Decimal] = None,
        big_blind: Optional[Decimal] = None,
        min_buy_in: Decimal = Decimal('10.00'),
        max_buy_in: Optional[Decimal] = None
    ) -> 'LiveGame':
        """
        Factory method to create a new active live game.

        Args:
            game_id: Parent game identifier
            created_by_user_id: User creating the game
            join_code: Unique join code
            small_blind: Optional small blind amount
            big_blind: Optional big blind amount
            min_buy_in: Minimum buy-in (default $10)
            max_buy_in: Optional maximum buy-in

        Returns:
            New LiveGame entity with status='active'
        """
        return LiveGame(
            id=None,
            game_id=game_id,
            created_by_user_id=created_by_user_id,
            join_code=join_code,
            status='active',
            small_blind=small_blind,
            big_blind=big_blind,
            min_buy_in=min_buy_in,
            max_buy_in=max_buy_in,
            started_at=datetime.now(timezone.utc).replace(tzinfo=None),
            closed_at=None
        )

    def close(self) -> None:
        """
        Close the live game session.

        Sets status to 'closed' and records the closed timestamp.
        Once closed, no new participants or transactions can be added.
        """
        self.status = 'closed'
        self.closed_at = datetime.now(timezone.utc).replace(tzinfo=None)

    def is_active(self) -> bool:
        """
        Check if the live game is still active.

        Returns:
            True if status is 'active', False otherwise
        """
        return self.status == 'active'

    def to_dict(self) -> dict:
        """Convert entity to dictionary for serialization."""
        return {
            'id': str(self.id) if self.id else None,
            'game_id': str(self.game_id),
            'created_by_user_id': str(self.created_by_user_id),
            'join_code': str(self.join_code),
            'status': self.status,
            'small_blind': float(self.small_blind) if self.small_blind else None,
            'big_blind': float(self.big_blind) if self.big_blind else None,
            'min_buy_in': float(self.min_buy_in),
            'max_buy_in': float(self.max_buy_in) if self.max_buy_in else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'closed_at': self.closed_at.isoformat() if self.closed_at else None,
        }


@dataclass
class LiveGameParticipant:
    """
    Player participating in a live game session.

    Represents a user who has joined a live game. Each participant can
    log buy-ins and cash-outs during the session.

    Business Rules:
    - Each user can only join a live game once
    - Display name is captured at join time (may differ from user account name)
    - Can optionally be linked to a poker player identity via player_id

    Attributes:
        id: Unique identifier (None for new entities)
        live_game_id: Live game this participant belongs to
        user_id: User account identifier
        display_name: Name displayed in the game
        player_id: Optional link to poker player identity (for claimed identities)
        joined_at: When the participant joined
        claimed_player_external_id: Enriched data from Player table (external_id)
        claimed_player_name: Enriched data from Player table (display_name)
    """
    id: Optional[ParticipantId]
    live_game_id: LiveGameId
    user_id: UserId
    display_name: str
    player_id: Optional[PlayerId]
    joined_at: datetime
    # Enriched fields from joined Player table (populated by repository)
    claimed_player_external_id: Optional[str] = None
    claimed_player_name: Optional[str] = None

    @staticmethod
    def create_new(
        live_game_id: LiveGameId,
        user_id: UserId,
        display_name: str,
        player_id: Optional[PlayerId] = None
    ) -> 'LiveGameParticipant':
        """
        Factory method to create a new participant.

        Args:
            live_game_id: Live game to join
            user_id: User joining the game
            display_name: Display name for this participant
            player_id: Optional poker player identity to link to

        Returns:
            New LiveGameParticipant entity
        """
        return LiveGameParticipant(
            id=None,
            live_game_id=live_game_id,
            user_id=user_id,
            display_name=display_name,
            player_id=player_id,
            joined_at=datetime.now(timezone.utc).replace(tzinfo=None)
        )

    def to_dict(self) -> dict:
        """Convert entity to dictionary for serialization."""
        return {
            'id': str(self.id) if self.id else None,
            'live_game_id': str(self.live_game_id),
            'user_id': str(self.user_id),
            'display_name': self.display_name,
            'player_id': str(self.player_id) if self.player_id else None,
            'joined_at': self.joined_at.isoformat() if self.joined_at else None,
            'claimed_player_external_id': self.claimed_player_external_id,
            'claimed_player_name': self.claimed_player_name,
        }


@dataclass
class LiveGameTransaction:
    """
    Buy-in or cash-out transaction in a live game.

    Represents a monetary transaction logged by a participant. Transactions
    start as 'pending' and can be approved, rejected, or edited by the
    game admin.

    Business Rules:
    - Transactions start as 'pending' status
    - Only game admin can approve/reject transactions
    - Editing preserves original amount for audit trail
    - Transaction types: 'buy_in' or 'cash_out'

    Attributes:
        id: Unique identifier (None for new entities)
        live_game_id: Live game this transaction belongs to
        participant_id: Participant who logged the transaction
        user_id: User identifier (denormalized for queries)
        transaction_type: 'buy_in' or 'cash_out'
        amount: Current transaction amount
        status: 'pending', 'approved', or 'rejected'
        created_at: When transaction was created
        approved_by_user_id: Admin who approved/rejected (None if pending)
        approved_at: When approved/rejected (None if pending)
        notes: Optional notes (used for rejection reasons or edit history)
        original_amount: Original amount if edited (None if not edited)
        edited_at: When amount was last edited (None if not edited)
        edited_by_user_id: Admin who edited (None if not edited)
    """
    id: Optional[TransactionId]
    live_game_id: LiveGameId
    participant_id: ParticipantId
    user_id: UserId
    transaction_type: str  # 'buy_in' or 'cash_out'
    amount: Decimal
    status: str  # 'pending', 'approved', 'rejected'
    created_at: datetime
    approved_by_user_id: Optional[UserId]
    approved_at: Optional[datetime]
    notes: Optional[str]
    original_amount: Optional[Decimal]
    edited_at: Optional[datetime]
    edited_by_user_id: Optional[UserId]

    @staticmethod
    def create_buy_in(
        live_game_id: LiveGameId,
        participant_id: ParticipantId,
        user_id: UserId,
        amount: Decimal
    ) -> 'LiveGameTransaction':
        """
        Factory method to create a buy-in transaction.

        Args:
            live_game_id: Live game identifier
            participant_id: Participant logging the buy-in
            user_id: User identifier
            amount: Buy-in amount in dollars

        Returns:
            New LiveGameTransaction with type='buy_in' and status='pending'
        """
        return LiveGameTransaction(
            id=None,
            live_game_id=live_game_id,
            participant_id=participant_id,
            user_id=user_id,
            transaction_type='buy_in',
            amount=amount,
            status='pending',
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            approved_by_user_id=None,
            approved_at=None,
            notes=None,
            original_amount=None,
            edited_at=None,
            edited_by_user_id=None
        )

    @staticmethod
    def create_cash_out(
        live_game_id: LiveGameId,
        participant_id: ParticipantId,
        user_id: UserId,
        amount: Decimal
    ) -> 'LiveGameTransaction':
        """
        Factory method to create a cash-out transaction.

        Args:
            live_game_id: Live game identifier
            participant_id: Participant logging the cash-out
            user_id: User identifier
            amount: Cash-out amount in dollars

        Returns:
            New LiveGameTransaction with type='cash_out' and status='pending'
        """
        return LiveGameTransaction(
            id=None,
            live_game_id=live_game_id,
            participant_id=participant_id,
            user_id=user_id,
            transaction_type='cash_out',
            amount=amount,
            status='pending',
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            approved_by_user_id=None,
            approved_at=None,
            notes=None,
            original_amount=None,
            edited_at=None,
            edited_by_user_id=None
        )

    def approve(self, approved_by_user_id: UserId) -> None:
        """
        Approve the transaction.

        Args:
            approved_by_user_id: Admin approving the transaction
        """
        self.status = 'approved'
        self.approved_by_user_id = approved_by_user_id
        self.approved_at = datetime.now(timezone.utc).replace(tzinfo=None)

    def reject(self, rejected_by_user_id: UserId, reason: str) -> None:
        """
        Reject the transaction.

        Args:
            rejected_by_user_id: Admin rejecting the transaction
            reason: Reason for rejection
        """
        self.status = 'rejected'
        self.approved_by_user_id = rejected_by_user_id
        self.approved_at = datetime.now(timezone.utc).replace(tzinfo=None)
        self.notes = reason

    def edit_amount(self, new_amount: Decimal, edited_by_user_id: UserId, reason: str) -> None:
        """
        Edit the transaction amount, preserving the original.

        Args:
            new_amount: New transaction amount
            edited_by_user_id: Admin making the edit
            reason: Reason for the edit
        """
        if self.original_amount is None:
            self.original_amount = self.amount
        self.amount = new_amount
        self.edited_at = datetime.now(timezone.utc).replace(tzinfo=None)
        self.edited_by_user_id = edited_by_user_id
        self.notes = f"{self.notes or ''}\nEdited: {reason}".strip()

    def is_pending(self) -> bool:
        """Check if transaction is pending approval."""
        return self.status == 'pending'

    def is_approved(self) -> bool:
        """Check if transaction is approved."""
        return self.status == 'approved'

    def is_rejected(self) -> bool:
        """Check if transaction is rejected."""
        return self.status == 'rejected'

    def to_dict(self) -> dict:
        """Convert entity to dictionary for serialization."""
        return {
            'id': str(self.id) if self.id else None,
            'live_game_id': str(self.live_game_id),
            'participant_id': str(self.participant_id),
            'user_id': str(self.user_id),
            'transaction_type': self.transaction_type,
            'amount': float(self.amount),
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'approved_by_user_id': str(self.approved_by_user_id) if self.approved_by_user_id else None,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'notes': self.notes,
            'original_amount': float(self.original_amount) if self.original_amount else None,
            'edited_at': self.edited_at.isoformat() if self.edited_at else None,
            'edited_by_user_id': str(self.edited_by_user_id) if self.edited_by_user_id else None,
        }
