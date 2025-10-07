"""
Structured audit logging for payment operations.

CRITICAL: All balance state transitions must be logged for audit trail.
This logger provides payment-grade structured logging with immutable audit records.
"""

import logging
import json
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


class PaymentAuditLogger:
    """
    Structured logger for payment audit trail.

    All logs are JSON-formatted for structured log aggregation and analysis.
    These logs are immutable audit records and should never be suppressed.
    """

    @staticmethod
    def log_balance_transition(
        game_id: str,
        player_id: str,
        old_balance_cents: int,
        new_balance_cents: int,
        old_negative_since: Optional[datetime],
        new_negative_since: Optional[datetime],
        transition_type: str,
        payment_id: Optional[str] = None
    ) -> None:
        """
        Log balance state transition for audit trail.

        CRITICAL: These logs are immutable audit records. Do not suppress.

        Args:
            game_id: Game identifier
            player_id: Player identifier
            old_balance_cents: Balance before transition (in cents)
            new_balance_cents: Balance after transition (in cents)
            old_negative_since: Previous balance_negative_since timestamp
            new_negative_since: New balance_negative_since timestamp
            transition_type: Type of transition (became_negative, still_negative, became_positive, still_positive)
            payment_id: Optional payment transaction ID that triggered this transition

        Transition types:
            - became_negative: Balance crossed from >=0 to <0
            - still_negative: Balance remained negative (timestamp preserved)
            - became_positive: Balance crossed from <0 to >=0 (settled up)
            - still_positive: Balance remained non-negative
        """
        log_entry = {
            "event": "balance_state_transition",
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "game_id": game_id,
            "player_id": player_id,
            "payment_id": payment_id,
            "old_balance_cents": old_balance_cents,
            "new_balance_cents": new_balance_cents,
            "old_balance_negative_since": old_negative_since.isoformat() if old_negative_since else None,
            "new_balance_negative_since": new_negative_since.isoformat() if new_negative_since else None,
            "transition_type": transition_type,
            "balance_change_cents": new_balance_cents - old_balance_cents
        }

        # Log as JSON for structured log aggregation
        logger.info(json.dumps(log_entry))

    @staticmethod
    def log_invariant_violation(
        game_id: str,
        player_id: str,
        balance_cents: int,
        balance_negative_since: Optional[datetime],
        violation_description: str
    ) -> None:
        """
        Log invariant violation (CRITICAL ERROR).

        This should trigger alerts in production monitoring.

        Args:
            game_id: Game identifier
            player_id: Player identifier
            balance_cents: Current balance in cents
            balance_negative_since: Current timestamp value
            violation_description: Description of the invariant violation
        """
        log_entry = {
            "event": "INVARIANT_VIOLATION",
            "severity": "CRITICAL",
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "game_id": game_id,
            "player_id": player_id,
            "balance_cents": balance_cents,
            "balance_negative_since": balance_negative_since.isoformat() if balance_negative_since else None,
            "violation_description": violation_description
        }

        logger.error(json.dumps(log_entry))

    @staticmethod
    def log_state_transition_error(
        game_id: str,
        player_id: str,
        error_message: str,
        error_type: str
    ) -> None:
        """
        Log error during state transition processing.

        Args:
            game_id: Game identifier
            player_id: Player identifier
            error_message: Error message
            error_type: Type of error (e.g., SQLAlchemyError, ValueError)
        """
        log_entry = {
            "event": "state_transition_error",
            "severity": "ERROR",
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "game_id": game_id,
            "player_id": player_id,
            "error_message": error_message,
            "error_type": error_type
        }

        logger.error(json.dumps(log_entry))
