"""
Repository interfaces for live game domain.

These abstract repositories define the contract for persisting live game entities
following the repository pattern in Domain-Driven Design.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict
from decimal import Decimal

from domain.identity.value_objects import UserId
from domain.poker.value_objects import GameId
from .entities import LiveGame, LiveGameParticipant, LiveGameTransaction
from .value_objects import LiveGameId, ParticipantId, TransactionId, JoinCode


class LiveGameRepository(ABC):
    """
    Repository interface for live game persistence.

    Manages the lifecycle of LiveGame entities including creation,
    retrieval, and status updates.
    """

    @abstractmethod
    def get_by_id(self, live_game_id: LiveGameId) -> Optional[LiveGame]:
        """
        Retrieve a live game by its ID.

        Args:
            live_game_id: The live game identifier

        Returns:
            LiveGame if found, None otherwise

        Raises:
            RepositoryError: If retrieval fails
        """
        pass

    @abstractmethod
    def get_by_join_code(self, join_code: JoinCode) -> Optional[LiveGame]:
        """
        Retrieve a live game by its join code.

        Args:
            join_code: The 4-character join code

        Returns:
            LiveGame if found, None otherwise

        Raises:
            RepositoryError: If retrieval fails
        """
        pass

    @abstractmethod
    def get_active_by_game_id(self, game_id: GameId) -> Optional[LiveGame]:
        """
        Get the currently active live game for a parent game.

        Business rule: Only one active live game per parent game at a time.

        Args:
            game_id: The parent game identifier

        Returns:
            Active LiveGame if exists, None otherwise

        Raises:
            RepositoryError: If retrieval fails
        """
        pass

    @abstractmethod
    def create(self, live_game: LiveGame) -> LiveGame:
        """
        Create a new live game.

        Args:
            live_game: The live game to create

        Returns:
            Created LiveGame with ID populated

        Raises:
            RepositoryError: If creation fails
        """
        pass

    @abstractmethod
    def update(self, live_game: LiveGame) -> LiveGame:
        """
        Update an existing live game.

        Args:
            live_game: The live game with updated values

        Returns:
            Updated LiveGame

        Raises:
            RepositoryError: If update fails or live game not found
        """
        pass

    @abstractmethod
    def join_code_exists(self, join_code_str: str) -> bool:
        """
        Check if a join code already exists.

        Used during join code generation to ensure uniqueness.

        Args:
            join_code_str: The join code string to check

        Returns:
            True if code exists, False otherwise

        Raises:
            RepositoryError: If check fails
        """
        pass


class ParticipantRepository(ABC):
    """
    Repository interface for live game participant persistence.

    Manages participants who have joined live game sessions.
    """

    @abstractmethod
    def get_by_id(self, participant_id: ParticipantId) -> Optional[LiveGameParticipant]:
        """
        Retrieve a participant by ID.

        Args:
            participant_id: The participant identifier

        Returns:
            LiveGameParticipant if found, None otherwise

        Raises:
            RepositoryError: If retrieval fails
        """
        pass

    @abstractmethod
    def get_by_user_and_live_game(
        self,
        user_id: UserId,
        live_game_id: LiveGameId
    ) -> Optional[LiveGameParticipant]:
        """
        Get a participant by user and live game.

        Used to check if a user has already joined a live game.

        Args:
            user_id: The user identifier
            live_game_id: The live game identifier

        Returns:
            LiveGameParticipant if found, None otherwise

        Raises:
            RepositoryError: If retrieval fails
        """
        pass

    @abstractmethod
    def get_by_live_game(self, live_game_id: LiveGameId) -> List[LiveGameParticipant]:
        """
        Get all participants in a live game.

        Args:
            live_game_id: The live game identifier

        Returns:
            List of LiveGameParticipant (may be empty)

        Raises:
            RepositoryError: If retrieval fails
        """
        pass

    @abstractmethod
    def create(self, participant: LiveGameParticipant) -> LiveGameParticipant:
        """
        Add a participant to a live game.

        Args:
            participant: The participant to create

        Returns:
            Created LiveGameParticipant with ID populated

        Raises:
            RepositoryError: If creation fails
        """
        pass


class TransactionRepository(ABC):
    """
    Repository interface for live game transaction persistence.

    Manages buy-in and cash-out transactions with approval workflow.
    """

    @abstractmethod
    def get_by_id(self, transaction_id: TransactionId) -> Optional[LiveGameTransaction]:
        """
        Retrieve a transaction by ID.

        Args:
            transaction_id: The transaction identifier

        Returns:
            LiveGameTransaction if found, None otherwise

        Raises:
            RepositoryError: If retrieval fails
        """
        pass

    @abstractmethod
    def get_by_live_game(self, live_game_id: LiveGameId) -> List[LiveGameTransaction]:
        """
        Get all transactions for a live game.

        Args:
            live_game_id: The live game identifier

        Returns:
            List of LiveGameTransaction (may be empty)

        Raises:
            RepositoryError: If retrieval fails
        """
        pass

    @abstractmethod
    def get_pending_by_live_game(self, live_game_id: LiveGameId) -> List[LiveGameTransaction]:
        """
        Get pending transactions for a live game.

        Args:
            live_game_id: The live game identifier

        Returns:
            List of pending LiveGameTransaction (may be empty)

        Raises:
            RepositoryError: If retrieval fails
        """
        pass

    @abstractmethod
    def get_by_participant(self, participant_id: ParticipantId) -> List[LiveGameTransaction]:
        """
        Get all transactions for a participant.

        Args:
            participant_id: The participant identifier

        Returns:
            List of LiveGameTransaction (may be empty)

        Raises:
            RepositoryError: If retrieval fails
        """
        pass

    @abstractmethod
    def get_approved_by_participant(self, participant_id: ParticipantId) -> List[LiveGameTransaction]:
        """
        Get approved transactions for a participant.

        Args:
            participant_id: The participant identifier

        Returns:
            List of approved LiveGameTransaction (may be empty)

        Raises:
            RepositoryError: If retrieval fails
        """
        pass

    @abstractmethod
    def create(self, transaction: LiveGameTransaction) -> LiveGameTransaction:
        """
        Create a new transaction.

        Args:
            transaction: The transaction to create

        Returns:
            Created LiveGameTransaction with ID populated

        Raises:
            RepositoryError: If creation fails
        """
        pass

    @abstractmethod
    def update(self, transaction: LiveGameTransaction) -> LiveGameTransaction:
        """
        Update an existing transaction.

        Args:
            transaction: The transaction with updated values

        Returns:
            Updated LiveGameTransaction

        Raises:
            RepositoryError: If update fails or transaction not found
        """
        pass

    @abstractmethod
    def calculate_participant_stats(self, participant_id: ParticipantId) -> Dict[str, Decimal]:
        """
        Calculate financial statistics for a participant.

        Only includes APPROVED transactions in calculations.

        IMPORTANT: Cash-out means LEAVING the table!
        - If player has cashed out → chips_on_table = $0 (they left!)
        - If player still playing → chips_on_table = total_buy_ins (estimate)

        Args:
            participant_id: The participant identifier

        Returns:
            Dictionary with keys:
            - 'total_buy_ins': Sum of approved buy-in amounts
            - 'total_cash_outs': Sum of approved cash-out amounts
            - 'net_result': total_cash_outs - total_buy_ins
            - 'chips_on_table': $0 if cashed out, else total_buy_ins
            - 'buy_in_count': Number of approved buy-ins
            - 'cash_out_count': Number of approved cash-outs
            - 'has_cashed_out': True if player has cashed out (left table)

        Raises:
            RepositoryError: If calculation fails

        Example:
            >>> stats = repo.calculate_participant_stats(participant_id)
            >>> print(f"Net: ${stats['net_result']}")
            Net: $-25.00
            >>> if stats['has_cashed_out']:
            ...     print("Player left the table")
        """
        pass
