"""
Domain entities for the player domain.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Set
from uuid import uuid4

from .value_objects import (
    PlayerId, ExternalId, PlayerName, MatchScore,
    MatchReason, SessionStats
)


@dataclass
class PlayerSession:
    """Represents a player's participation in a session."""
    session_id: str
    session_external_id: str
    stats: SessionStats
    names_used: List[str]

    def __post_init__(self):
        if not self.session_id:
            raise ValueError("session_id is required")
        if not isinstance(self.names_used, list):
            raise ValueError("names_used must be a list")


@dataclass
class PlayerIdentity:
    """
    Aggregate root for player identity.

    Represents a player across multiple sessions and games,
    with verified identity and name history.
    """
    player_id: PlayerId
    display_name: PlayerName
    external_id: Optional[ExternalId] = None
    sessions: List[PlayerSession] = field(default_factory=list)

    def is_verified(self) -> bool:
        """Returns True if player has a verified external ID."""
        return self.external_id is not None

    def session_count(self) -> int:
        """Returns number of sessions this player has participated in."""
        return len(self.sessions)

    def all_names_used(self) -> Set[str]:
        """Returns set of all names this player has used across sessions."""
        names = {self.display_name.value}
        for session in self.sessions:
            names.update(session.names_used)
        return names

    def has_session(self, session_id: str) -> bool:
        """Returns True if player participated in the given session."""
        return any(s.session_id == session_id for s in self.sessions)

    def update_display_name(self, new_name: PlayerName) -> None:
        """Update the player's display name."""
        self.display_name = new_name

    def verify_identity(self, external_id: ExternalId) -> None:
        """Verify player identity with an external ID."""
        if self.external_id and self.external_id != external_id:
            raise ValueError(
                f"Player already verified with different external_id: {self.external_id}"
            )
        self.external_id = external_id

    def add_session(self, session: PlayerSession) -> None:
        """Add a session to this player's history."""
        if self.has_session(session.session_id):
            raise ValueError(f"Player already has session {session.session_id}")
        self.sessions.append(session)

    def merge_session(self, session: PlayerSession) -> None:
        """
        Merge session data if player already has this session.
        Combines stats and names.
        """
        existing_idx = next(
            (i for i, s in enumerate(self.sessions) if s.session_id == session.session_id),
            None
        )

        if existing_idx is None:
            self.add_session(session)
            return

        existing = self.sessions[existing_idx]

        # Merge stats
        merged_stats = SessionStats(
            buy_in=existing.stats.buy_in + session.stats.buy_in,
            cash_out=existing.stats.cash_out + session.stats.cash_out,
            net=existing.stats.net + session.stats.net,
            in_game=existing.stats.in_game + session.stats.in_game
        )

        # Merge names (unique)
        merged_names = list(set(existing.names_used + session.names_used))

        # Replace session
        self.sessions[existing_idx] = PlayerSession(
            session_id=session.session_id,
            session_external_id=session.session_external_id,
            stats=merged_stats,
            names_used=merged_names
        )


@dataclass
class MergeCandidate:
    """
    Represents a potential duplicate player match.

    Contains similarity information and matching reasons
    to help decide if two players should be merged.
    """
    player_identity: PlayerIdentity
    match_score: MatchScore
    match_reasons: List[MatchReason]

    def __post_init__(self):
        if not self.match_reasons:
            raise ValueError("MergeCandidate must have at least one match reason")

    def is_strong_candidate(self) -> bool:
        """Returns True if this is a strong merge candidate (score >= 80)."""
        return self.match_score.is_strong_match()

    def is_moderate_candidate(self) -> bool:
        """Returns True if this is a moderate merge candidate (score 50-79)."""
        return self.match_score.is_moderate_match()

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            'player_id': str(self.player_identity.player_id),
            'display_name': str(self.player_identity.display_name),
            'external_id': str(self.player_identity.external_id) if self.player_identity.external_id else None,
            'is_verified': self.player_identity.is_verified(),
            'session_count': self.player_identity.session_count(),
            'session_names': list(self.player_identity.all_names_used()),
            'match_score': int(self.match_score),
            'match_reasons': [r.description for r in self.match_reasons]
        }


@dataclass
class MergeOperation:
    """
    Represents a player merge operation.

    Tracks the merge of source players into a target player,
    including audit information.
    """
    operation_id: str
    target_player_id: PlayerId
    source_player_ids: List[PlayerId]
    verified_name: PlayerName
    new_external_id: Optional[ExternalId] = None

    def __post_init__(self):
        if not self.source_player_ids:
            raise ValueError("Must have at least one source player to merge")
        if self.target_player_id in self.source_player_ids:
            raise ValueError("Target player cannot be in source players list")

    @classmethod
    def create_new(
        cls,
        target_player_id: PlayerId,
        source_player_ids: List[PlayerId],
        verified_name: PlayerName,
        new_external_id: Optional[ExternalId] = None
    ) -> MergeOperation:
        """Factory method to create a new merge operation with generated ID."""
        return cls(
            operation_id=str(uuid4()),
            target_player_id=target_player_id,
            source_player_ids=source_player_ids,
            verified_name=verified_name,
            new_external_id=new_external_id
        )

    def player_count(self) -> int:
        """Returns total number of players involved (target + sources)."""
        return 1 + len(self.source_player_ids)


@dataclass
class MergeResult:
    """Result of a merge operation."""
    operation: MergeOperation
    merged_player: PlayerIdentity
    sessions_merged: int

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            'message': 'Players merged successfully',
            'operation_id': self.operation.operation_id,
            'target_player_id': str(self.operation.target_player_id),
            'merged_player_count': len(self.operation.source_player_ids),
            'merged_sessions': self.sessions_merged,
            'verified_name': str(self.operation.verified_name),
            'external_id': str(self.operation.new_external_id) if self.operation.new_external_id else None,
            'final_display_name': str(self.merged_player.display_name),
            'all_names_used': list(self.merged_player.all_names_used())
        }