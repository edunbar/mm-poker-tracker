"""
Live Game domain service.

This module provides the core business logic for managing real-time live poker
game sessions, including game creation, participant management, transaction
handling, and game closure with reconciliation.
"""

from typing import Optional, List, Dict, Any
from decimal import Decimal

from domain.identity.value_objects import UserId
from domain.poker.value_objects import GameId, PlayerId
from domain.live_game.entities import (
    LiveGame, LiveGameParticipant, LiveGameTransaction
)
from domain.live_game.value_objects import (
    LiveGameId, ParticipantId, TransactionId, JoinCode
)
from domain.live_game.repositories import (
    LiveGameRepository, ParticipantRepository, TransactionRepository
)
from domain.live_game.join_code_generator import create_unique_join_code
from domain.live_game.exceptions import (
    LiveGameError,
    LiveGameNotFoundError,
    LiveGameAlreadyClosedError,
    ActiveLiveGameExistsError,
    InvalidJoinCodeError,
    ParticipantAlreadyJoinedError,
    ParticipantNotFoundError,
    InvalidBuyInAmountError,
    InvalidCashOutAmountError,
    TransactionNotFoundError,
    TransactionNotPendingError,
    GameNotBalancedError,
    PlayersStillActiveError
)


class LiveGameService:
    """
    Domain service for managing live poker game sessions.

    This service encapsulates the business logic for real-time poker game
    tracking, coordinating between multiple repositories to enforce business
    rules and maintain data integrity.

    Business Rules:
    - Only one active live game per parent game at a time
    - Participants can only join once per live game
    - Buy-ins must respect min/max limits
    - Cash-outs mean LEAVING the table (players can only cash out ONCE)
    - After cash-out, chips_on_table = $0 (player has left)
    - Games must be balanced (buy-ins = cash-outs) before closing
    - No players can have chips on table when closing
    - Transactions require approval workflow

    Attributes:
        live_game_repo: Repository for live game persistence
        participant_repo: Repository for participant persistence
        transaction_repo: Repository for transaction persistence
    """

    def __init__(
        self,
        live_game_repo: LiveGameRepository,
        participant_repo: ParticipantRepository,
        transaction_repo: TransactionRepository
    ):
        """
        Initialize the live game service.

        Args:
            live_game_repo: Repository for live game operations
            participant_repo: Repository for participant operations
            transaction_repo: Repository for transaction operations
        """
        self.live_game_repo = live_game_repo
        self.participant_repo = participant_repo
        self.transaction_repo = transaction_repo

    # ==========================================================================
    # LIVE GAME MANAGEMENT
    # ==========================================================================

    def create_live_game(
        self,
        game_id: GameId,
        created_by_user_id: UserId,
        small_blind: Optional[Decimal] = None,
        big_blind: Optional[Decimal] = None,
        min_buy_in: Decimal = Decimal('10.00'),
        max_buy_in: Optional[Decimal] = None
    ) -> LiveGame:
        """
        Create a new live game session.

        Enforces the business rule that only one active live game can exist
        per parent game at a time. Generates a unique 4-character join code.

        Args:
            game_id: Parent game identifier
            created_by_user_id: User creating the live game
            small_blind: Optional small blind amount
            big_blind: Optional big blind amount
            min_buy_in: Minimum buy-in amount (default $10)
            max_buy_in: Optional maximum buy-in amount

        Returns:
            Created LiveGame entity with generated join code

        Raises:
            ActiveLiveGameExistsError: If an active live game already exists

        Example:
            >>> live_game = service.create_live_game(
            ...     game_id=GameId('game-uuid'),
            ...     created_by_user_id=UserId('user-uuid'),
            ...     min_buy_in=Decimal('20.00'),
            ...     max_buy_in=Decimal('100.00')
            ... )
            >>> print(f"Join code: {live_game.join_code}")
        """
        # Check if active live game already exists
        existing = self.live_game_repo.get_active_by_game_id(game_id)
        if existing:
            raise ActiveLiveGameExistsError(existing.join_code.value)

        # Generate unique join code
        join_code = create_unique_join_code(
            self.live_game_repo.join_code_exists
        )

        # Create live game
        live_game = LiveGame.create_new(
            game_id=game_id,
            created_by_user_id=created_by_user_id,
            join_code=join_code,
            small_blind=small_blind,
            big_blind=big_blind,
            min_buy_in=min_buy_in,
            max_buy_in=max_buy_in
        )

        return self.live_game_repo.create(live_game)

    def get_live_game_by_join_code(self, join_code_str: str) -> LiveGame:
        """
        Get live game by join code.

        Args:
            join_code_str: The 4-character join code

        Returns:
            Active LiveGame entity

        Raises:
            InvalidJoinCodeError: If join code format is invalid or game not found
            LiveGameAlreadyClosedError: If game exists but is closed
        """
        try:
            join_code = JoinCode(join_code_str)
        except ValueError:
            raise InvalidJoinCodeError(join_code_str)

        live_game = self.live_game_repo.get_by_join_code(join_code)
        if not live_game:
            raise LiveGameNotFoundError(join_code_str)

        if not live_game.is_active():
            raise LiveGameAlreadyClosedError()

        return live_game

    def get_active_live_game(self, game_id: GameId) -> Optional[LiveGame]:
        """
        Get active live game for a parent game.

        Args:
            game_id: Parent game identifier

        Returns:
            Active LiveGame if exists, None otherwise
        """
        return self.live_game_repo.get_active_by_game_id(game_id)

    # ==========================================================================
    # PARTICIPANT MANAGEMENT
    # ==========================================================================

    def join_live_game(
        self,
        live_game_id: LiveGameId,
        user_id: UserId,
        display_name: str,
        player_id: Optional['PlayerId'] = None
    ) -> LiveGameParticipant:
        """
        Join a live game as a participant.

        Args:
            live_game_id: Live game to join
            user_id: User joining the game
            display_name: Display name for this participant
            player_id: Optional poker player identity to link (for claimed identities)

        Returns:
            Created LiveGameParticipant entity

        Raises:
            LiveGameNotFoundError: If live game doesn't exist
            LiveGameAlreadyClosedError: If live game is closed
            ParticipantAlreadyJoinedError: If user already joined
        """
        # Check live game exists and is active
        live_game = self.live_game_repo.get_by_id(live_game_id)
        if not live_game:
            raise LiveGameNotFoundError(str(live_game_id))

        if not live_game.is_active():
            raise LiveGameAlreadyClosedError()

        # Check if already joined
        existing = self.participant_repo.get_by_user_and_live_game(
            user_id, live_game_id
        )
        if existing:
            raise ParticipantAlreadyJoinedError()

        # Create participant (with optional player_id link)
        participant = LiveGameParticipant.create_new(
            live_game_id=live_game_id,
            user_id=user_id,
            display_name=display_name,
            player_id=player_id
        )

        return self.participant_repo.create(participant)

    def get_participants(self, live_game_id: LiveGameId) -> List[Dict]:
        """
        Get all participants with their current statistics.

        Args:
            live_game_id: Live game identifier

        Returns:
            List of participant dictionaries with stats:
            [
                {
                    'participant_id': str,
                    'user_id': str,
                    'display_name': str,
                    'joined_at': str (ISO format),
                    'stats': {
                        'total_buy_ins': Decimal,
                        'total_cash_outs': Decimal,
                        'net_result': Decimal,
                        'chips_on_table': Decimal
                    }
                }
            ]
        """
        participants = self.participant_repo.get_by_live_game(live_game_id)

        result = []
        for participant in participants:
            stats = self.transaction_repo.calculate_participant_stats(participant.id)
            result.append({
                'participant_id': str(participant.id),
                'user_id': str(participant.user_id),
                'display_name': participant.display_name,
                'joined_at': participant.joined_at.isoformat(),
                'stats': stats
            })

        return result

    # ==========================================================================
    # TRANSACTION MANAGEMENT
    # ==========================================================================

    def request_buy_in(
        self,
        live_game_id: LiveGameId,
        user_id: UserId,
        amount: Decimal
    ) -> LiveGameTransaction:
        """
        Request a buy-in (creates pending transaction).

        Args:
            live_game_id: Live game identifier
            user_id: User requesting buy-in
            amount: Buy-in amount

        Returns:
            Created LiveGameTransaction with status='pending'

        Raises:
            LiveGameNotFoundError: If live game doesn't exist
            LiveGameAlreadyClosedError: If live game is closed
            ParticipantNotFoundError: If user hasn't joined
            InvalidBuyInAmountError: If amount is outside min/max limits
        """
        # Get live game and validate
        live_game = self.live_game_repo.get_by_id(live_game_id)
        if not live_game:
            raise LiveGameNotFoundError(str(live_game_id))

        if not live_game.is_active():
            raise LiveGameAlreadyClosedError()

        # Validate amount
        if amount < live_game.min_buy_in:
            raise InvalidBuyInAmountError(amount, live_game.min_buy_in, live_game.max_buy_in)

        if live_game.max_buy_in and amount > live_game.max_buy_in:
            raise InvalidBuyInAmountError(amount, live_game.min_buy_in, live_game.max_buy_in)

        # Get participant
        participant = self.participant_repo.get_by_user_and_live_game(
            user_id, live_game_id
        )
        if not participant:
            raise ParticipantNotFoundError()

        # Create transaction
        transaction = LiveGameTransaction.create_buy_in(
            live_game_id=live_game_id,
            participant_id=participant.id,
            user_id=user_id,
            amount=amount
        )

        return self.transaction_repo.create(transaction)

    def request_cash_out(
        self,
        live_game_id: LiveGameId,
        user_id: UserId,
        amount: Decimal
    ) -> LiveGameTransaction:
        """
        Request a cash-out (creates pending transaction).

        Players count their actual chips at the table and request that amount.
        Admin verifies the physical chip count before approving the transaction.
        This allows for wins/losses during gameplay that aren't tracked by the system.

        IMPORTANT: Cash-out means LEAVING the table!
        - Players can only cash out ONCE (they leave when cashing out)
        - After cashing out, chips_on_table = $0

        Args:
            live_game_id: Live game identifier
            user_id: User requesting cash-out
            amount: Cash-out amount (total chips player is leaving with)

        Returns:
            Created LiveGameTransaction with status='pending'

        Raises:
            LiveGameNotFoundError: If live game doesn't exist
            LiveGameAlreadyClosedError: If live game is closed
            ParticipantNotFoundError: If user hasn't joined
            LiveGameError: If player has already cashed out
            ValueError: If amount is negative
        """
        # Get live game and validate
        live_game = self.live_game_repo.get_by_id(live_game_id)
        if not live_game:
            raise LiveGameNotFoundError(str(live_game_id))

        if not live_game.is_active():
            raise LiveGameAlreadyClosedError()

        # Get participant
        participant = self.participant_repo.get_by_user_and_live_game(
            user_id, live_game_id
        )
        if not participant:
            raise ParticipantNotFoundError()

        # Check if already cashed out (players can only cash out once!)
        stats = self.transaction_repo.calculate_participant_stats(participant.id)
        if stats['has_cashed_out']:
            raise LiveGameError("You have already cashed out from this game. You cannot cash out twice.")

        # Validate amount is non-negative (allow $0 for busted players)
        if amount < Decimal('0'):
            raise ValueError(f"Cash-out amount cannot be negative (got ${amount})")

        # Create transaction
        # Note: We don't validate against calculated chip count because:
        # 1. Players count actual physical chips
        # 2. Chips won/lost during play aren't tracked by transactions
        # 3. Admin verifies actual chip count before approving
        # 4. Cash-out represents TOTAL chips leaving with (not partial withdrawal)
        transaction = LiveGameTransaction.create_cash_out(
            live_game_id=live_game_id,
            participant_id=participant.id,
            user_id=user_id,
            amount=amount
        )

        return self.transaction_repo.create(transaction)

    def approve_transaction(
        self,
        transaction_id: TransactionId,
        approved_by_user_id: UserId
    ) -> LiveGameTransaction:
        """
        Approve a pending transaction.

        Args:
            transaction_id: Transaction to approve
            approved_by_user_id: User approving the transaction

        Returns:
            Updated LiveGameTransaction with status='approved'

        Raises:
            TransactionNotFoundError: If transaction doesn't exist
            TransactionNotPendingError: If transaction is not pending
        """
        # Get transaction
        transaction = self.transaction_repo.get_by_id(transaction_id)
        if not transaction:
            raise TransactionNotFoundError()

        if not transaction.is_pending():
            raise TransactionNotPendingError()

        # Approve
        transaction.approve(approved_by_user_id)

        return self.transaction_repo.update(transaction)

    def reject_transaction(
        self,
        transaction_id: TransactionId,
        rejected_by_user_id: UserId,
        reason: str
    ) -> LiveGameTransaction:
        """
        Reject a pending transaction.

        Args:
            transaction_id: Transaction to reject
            rejected_by_user_id: User rejecting the transaction
            reason: Reason for rejection

        Returns:
            Updated LiveGameTransaction with status='rejected'

        Raises:
            TransactionNotFoundError: If transaction doesn't exist
            TransactionNotPendingError: If transaction is not pending
        """
        # Get transaction
        transaction = self.transaction_repo.get_by_id(transaction_id)
        if not transaction:
            raise TransactionNotFoundError()

        if not transaction.is_pending():
            raise TransactionNotPendingError()

        # Reject
        transaction.reject(rejected_by_user_id, reason)

        return self.transaction_repo.update(transaction)

    def edit_transaction_amount(
        self,
        transaction_id: TransactionId,
        new_amount: Decimal,
        edited_by_user_id: UserId,
        reason: str
    ) -> LiveGameTransaction:
        """
        Edit transaction amount (preserves original for audit trail).

        Args:
            transaction_id: Transaction to edit
            new_amount: New transaction amount
            edited_by_user_id: User making the edit
            reason: Reason for the edit

        Returns:
            Updated LiveGameTransaction with preserved original_amount

        Raises:
            TransactionNotFoundError: If transaction doesn't exist
        """
        # Get transaction
        transaction = self.transaction_repo.get_by_id(transaction_id)
        if not transaction:
            raise TransactionNotFoundError()

        # Edit
        transaction.edit_amount(new_amount, edited_by_user_id, reason)

        return self.transaction_repo.update(transaction)

    def get_pending_transactions(self, live_game_id: LiveGameId) -> List[LiveGameTransaction]:
        """
        Get all pending transactions for a live game.

        Args:
            live_game_id: Live game identifier

        Returns:
            List of pending LiveGameTransaction entities
        """
        return self.transaction_repo.get_pending_by_live_game(live_game_id)

    # ==========================================================================
    # GAME CLOSURE
    # ==========================================================================

    def close_live_game(self, live_game_id: LiveGameId) -> LiveGame:
        """
        Close a live game with full validation.

        Enforces business rules:
        - All players must cash out (no chips on table)
        - Game must be balanced (total buy-ins = total cash-outs)

        Args:
            live_game_id: Live game to close

        Returns:
            Updated LiveGame with status='closed'

        Raises:
            LiveGameNotFoundError: If live game doesn't exist
            LiveGameAlreadyClosedError: If live game is already closed
            PlayersStillActiveError: If any players have chips on table
            GameNotBalancedError: If buy-ins don't match cash-outs
        """
        # Get live game
        live_game = self.live_game_repo.get_by_id(live_game_id)
        if not live_game:
            raise LiveGameNotFoundError(str(live_game_id))

        if not live_game.is_active():
            raise LiveGameAlreadyClosedError()

        # Get all participants
        participants = self.participant_repo.get_by_live_game(live_game_id)

        # Check if any players still have chips
        active_players = []
        for participant in participants:
            stats = self.transaction_repo.calculate_participant_stats(participant.id)
            if stats['chips_on_table'] > Decimal('0'):
                active_players.append(participant.display_name)

        if active_players:
            raise PlayersStillActiveError(len(active_players))

        # Calculate totals
        total_buy_ins = Decimal('0')
        total_cash_outs = Decimal('0')

        for participant in participants:
            stats = self.transaction_repo.calculate_participant_stats(participant.id)
            total_buy_ins += stats['total_buy_ins']
            total_cash_outs += stats['total_cash_outs']

        # Check if balanced
        if total_buy_ins != total_cash_outs:
            raise GameNotBalancedError(total_buy_ins, total_cash_outs)

        # Close game
        live_game.close()

        return self.live_game_repo.update(live_game)

    def create_session_from_live_game(
        self,
        live_game_id: LiveGameId,
        db_session  # SQLAlchemy session for atomicity
    ) -> Dict[str, Any]:
        """
        Create a ledger session from closed live game data.

        This method converts a closed live game into a session record in the
        parent game's ledger, preserving all buy-in and cash-out data. It must
        be called within the same database transaction as close_live_game to
        ensure atomicity.

        Args:
            live_game_id: Live game identifier
            db_session: SQLAlchemy session (must be the same transaction as close)

        Returns:
            Dictionary with session creation results:
            {
                'success': bool,
                'session_id': str (external_id),
                'game_number': int,
                'players_processed': int,
                'live_game_id': str,
                'join_code': str
            }

        Raises:
            LiveGameNotFoundError: If live game doesn't exist
            ValueError: If live game is not closed or session creation fails

        Example:
            >>> db = SessionLocal()
            >>> try:
            >>>     # Close game
            >>>     live_game = service.close_live_game(live_game_id)
            >>>     # Create session (same transaction)
            >>>     result = service.create_session_from_live_game(live_game_id, db)
            >>>     db.commit()  # Commit both operations together
            >>> except Exception as e:
            >>>     db.rollback()  # Rollback both on failure
            >>>     raise
        """
        import logging
        from services.live_game_to_session_mapper import LiveGameToSessionMapper
        from services.session_ingestion_service import ingest_session

        log = logging.getLogger(__name__)

        # Get live game
        live_game = self.live_game_repo.get_by_id(live_game_id)
        if not live_game:
            raise LiveGameNotFoundError(str(live_game_id))

        if live_game.status != 'closed':
            raise ValueError(f"Cannot create session from non-closed live game (status: {live_game.status})")

        # Get participants and stats
        participants = self.participant_repo.get_by_live_game(live_game_id)

        # Build transaction stats dict
        transaction_stats = {}
        for participant in participants:
            stats = self.transaction_repo.calculate_participant_stats(participant.id)
            transaction_stats[str(participant.id)] = stats

        # Map live game data to session format
        session_data = LiveGameToSessionMapper.map_live_game_to_session_data(
            live_game, participants, transaction_stats
        )

        log.info(
            f"Creating session from live game {live_game.join_code.value}: "
            f"{len(participants)} participants"
        )

        # Get parent game details for ingestion
        from db.models import Game as GameModel
        from sqlalchemy import select

        game = db_session.execute(
            select(GameModel).where(GameModel.id == str(live_game.game_id))
        ).scalar_one_or_none()

        if not game:
            raise ValueError(f"Parent game not found: {live_game.game_id}")

        # Note: We cannot use ingest_session directly because it creates its own
        # database session and transaction. Instead, we need to call the internal
        # upsert logic directly to use the same transaction.

        from services.session_ingestion_service import (
            _upsert_db_for_session,
            _write_audit,
            _compute_next_game_number
        )

        # Get session timestamp
        session_timestamp = LiveGameToSessionMapper.get_session_timestamp(live_game)

        # Prepare validated players data
        validated_players = session_data['playersInfos']

        # Compute game number
        game_number = _compute_next_game_number(db_session, str(game.id))

        # Upsert session using existing ingestion logic
        # This runs in the same transaction as the live game closure
        sess_id, affected_rows = _upsert_db_for_session(
            db=db_session,
            game=game,
            session_external_id=session_data['sessionId'],
            when=session_timestamp,
            payload_json=session_data,
            validated_players=validated_players,
            game_number_for_meta=game_number,
            manual_game_number=None,
            session_type='live',
            session_name=session_data['sessionName'],
            ledger_csv_content=None
        )

        # Write audit log
        _write_audit(
            db=db_session,
            game=game,
            session_id=sess_id,
            admin_code='live_game_auto',
            action="CREATE_SESSION_FROM_LIVE_GAME",
            target="sessions",
            payload_before=None,
            payload_after={
                "live_game_id": str(live_game.id),
                "join_code": live_game.join_code.value,
                "session_external_id": session_data['sessionId'],
                "game_number": game_number,
                "players_count": len(validated_players),
            }
        )

        log.info(
            f"Successfully created session {sess_id} from live game {live_game.join_code.value}: "
            f"game_number={game_number}, players={affected_rows}"
        )

        return {
            'success': True,
            'session_id': session_data['sessionId'],  # External ID
            'game_number': game_number,
            'players_processed': affected_rows,
            'live_game_id': str(live_game.id),
            'join_code': live_game.join_code.value
        }

    def get_game_summary(self, live_game_id: LiveGameId) -> Dict:
        """
        Get complete game summary for reconciliation.

        Args:
            live_game_id: Live game identifier

        Returns:
            Dictionary with game summary:
            {
                'live_game_id': str,
                'status': str,
                'started_at': str (ISO),
                'closed_at': str (ISO) or None,
                'total_buy_ins': float,
                'total_cash_outs': float,
                'difference': float,
                'is_balanced': bool,
                'participants': [
                    {
                        'display_name': str,
                        'stats': {...}
                    }
                ]
            }

        Raises:
            LiveGameNotFoundError: If live game doesn't exist
        """
        live_game = self.live_game_repo.get_by_id(live_game_id)
        if not live_game:
            raise LiveGameNotFoundError(str(live_game_id))

        participants = self.participant_repo.get_by_live_game(live_game_id)

        participant_summaries = []
        total_buy_ins = Decimal('0')
        total_cash_outs = Decimal('0')

        for participant in participants:
            stats = self.transaction_repo.calculate_participant_stats(participant.id)
            participant_summaries.append({
                'display_name': participant.display_name,
                'stats': stats
            })
            total_buy_ins += stats['total_buy_ins']
            total_cash_outs += stats['total_cash_outs']

        return {
            'live_game_id': str(live_game.id),
            'status': live_game.status,
            'started_at': live_game.started_at.isoformat(),
            'closed_at': live_game.closed_at.isoformat() if live_game.closed_at else None,
            'total_buy_ins': float(total_buy_ins),
            'total_cash_outs': float(total_cash_outs),
            'difference': float(total_buy_ins - total_cash_outs),
            'is_balanced': total_buy_ins == total_cash_outs,
            'participants': participant_summaries
        }
