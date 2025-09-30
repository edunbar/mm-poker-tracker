"""
Domain services for player management.
"""

from typing import List, Optional
from .entities import PlayerIdentity, MergeCandidate, MergeOperation, MergeResult
from .value_objects import PlayerName, MatchScore, MatchReason, ExternalId, PlayerId


class PlayerMatchingService:
    """
    Domain service for finding potential duplicate players.

    Uses fuzzy matching on names to identify candidates for merging.
    """

    @staticmethod
    def calculate_similarity(str1: str, str2: str) -> float:
        """
        Calculate string similarity using character overlap.
        Returns a value between 0 and 1.
        """
        if not str1 or not str2:
            return 0.0

        # Use set intersection for simple similarity
        set1 = set(str1.lower())
        set2 = set(str2.lower())

        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))

        if union == 0:
            return 0.0

        return intersection / union

    @staticmethod
    def find_matches(
        verified_name: PlayerName,
        candidates: List[PlayerIdentity]
    ) -> List[MergeCandidate]:
        """
        Find potential matches for a verified name among candidate players.

        Args:
            verified_name: The name to match against
            candidates: List of player identities to check

        Returns:
            List of MergeCandidate objects sorted by match score (highest first)
        """
        verified_name_norm = verified_name.normalized()
        matches = []

        for candidate in candidates:
            match_score = 0
            reasons = []

            # Check display name similarity
            if candidate.display_name:
                display_name_norm = candidate.display_name.normalized()

                # Exact match (high score)
                if display_name_norm == verified_name_norm:
                    match_score += 100
                    reasons.append(MatchReason("Exact display name match", 100))
                # Contains match
                elif (verified_name_norm in display_name_norm or
                      display_name_norm in verified_name_norm):
                    match_score += 60
                    reasons.append(MatchReason("Display name contains match", 60))
                # Similar (character overlap)
                else:
                    similarity = PlayerMatchingService.calculate_similarity(
                        display_name_norm, verified_name_norm
                    )
                    if similarity > 0.6:
                        match_score += 40
                        reasons.append(
                            MatchReason(f"Similar display name ({similarity:.1%})", 40)
                        )

            # Check session names for matches
            all_session_names = candidate.all_names_used()
            best_session_match_score = 0
            best_session_match_reason = None

            for session_name in all_session_names:
                session_name_norm = session_name.lower().strip()

                if session_name_norm == verified_name_norm:
                    best_session_match_score = 80
                    best_session_match_reason = MatchReason("Exact session name match", 80)
                    break
                elif (verified_name_norm in session_name_norm or
                      session_name_norm in verified_name_norm):
                    if best_session_match_score < 50:
                        best_session_match_score = 50
                        best_session_match_reason = MatchReason("Session name contains match", 50)
                else:
                    similarity = PlayerMatchingService.calculate_similarity(
                        session_name_norm, verified_name_norm
                    )
                    if similarity > 0.7 and best_session_match_score < 30:
                        best_session_match_score = 30
                        best_session_match_reason = MatchReason(
                            f"Similar session name ({similarity:.1%})", 30
                        )

            if best_session_match_reason:
                match_score += best_session_match_score
                reasons.append(best_session_match_reason)

            # Only include matches with score above threshold
            if match_score >= 30 and reasons:
                # Cap score at 100
                final_score = min(match_score, 100)
                matches.append(MergeCandidate(
                    player_identity=candidate,
                    match_score=MatchScore(final_score),
                    match_reasons=reasons
                ))

        # Sort by match score (highest first)
        matches.sort(key=lambda m: int(m.match_score), reverse=True)
        return matches


class PlayerMergeService:
    """
    Domain service for merging player identities.

    Handles the business logic of combining multiple player records.
    """

    @staticmethod
    def prepare_merge(
        target_player: PlayerIdentity,
        source_players: List[PlayerIdentity],
        verified_name: PlayerName,
        new_external_id: Optional[ExternalId] = None
    ) -> MergeOperation:
        """
        Prepare a merge operation with validation.

        Args:
            target_player: The player to merge into
            source_players: Players to be merged and deleted
            verified_name: The verified name for the merged player
            new_external_id: Optional external ID to assign

        Returns:
            MergeOperation ready to execute

        Raises:
            ValueError: If merge is invalid
        """
        if not source_players:
            raise ValueError("Must provide at least one source player to merge")

        # Validate no duplicate players
        all_player_ids = [target_player.player_id] + [p.player_id for p in source_players]
        if len(all_player_ids) != len(set(str(pid) for pid in all_player_ids)):
            raise ValueError("Cannot merge a player with itself")

        # Check for verified conflicts if assigning new external_id
        if new_external_id:
            for player in [target_player] + source_players:
                if (player.external_id and
                    player.external_id != new_external_id):
                    # Allow merge if one of the source players has the desired external_id
                    has_match = any(
                        p.external_id == new_external_id
                        for p in source_players
                    )
                    if not has_match:
                        raise ValueError(
                            f"Cannot assign external_id '{new_external_id}' - "
                            f"conflicts with existing external_id '{player.external_id}'"
                        )

        return MergeOperation.create_new(
            target_player_id=target_player.player_id,
            source_player_ids=[p.player_id for p in source_players],
            verified_name=verified_name,
            new_external_id=new_external_id
        )

    @staticmethod
    def execute_merge(
        operation: MergeOperation,
        target_player: PlayerIdentity,
        source_players: List[PlayerIdentity]
    ) -> MergeResult:
        """
        Execute a player merge operation.

        Combines all source players into the target player.

        Args:
            operation: The merge operation to execute
            target_player: The player to merge into (will be modified)
            source_players: Players to merge from

        Returns:
            MergeResult with the merged player and statistics
        """
        sessions_merged = 0

        # Update target player's display name
        target_player.update_display_name(operation.verified_name)

        # Determine which external_id to use
        final_external_id = operation.new_external_id

        # If no new external_id specified, inherit from sources or keep target's
        if not final_external_id:
            if not target_player.external_id:
                # Find first source with external_id
                for source in source_players:
                    if source.external_id:
                        final_external_id = source.external_id
                        break
            else:
                final_external_id = target_player.external_id

        # Apply external_id if we have one
        if final_external_id:
            target_player.verify_identity(final_external_id)

        # Merge all sessions from source players
        for source_player in source_players:
            for session in source_player.sessions:
                target_player.merge_session(session)
                sessions_merged += 1

        return MergeResult(
            operation=operation,
            merged_player=target_player,
            sessions_merged=sessions_merged
        )