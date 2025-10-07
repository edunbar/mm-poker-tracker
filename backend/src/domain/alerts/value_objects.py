"""
Value objects for the alert domain.

These value objects encapsulate data and enforce business rules for alert operations.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import List, Literal, Optional


@dataclass(frozen=True)
class AlertRule:
    """
    Value object representing an alert rule configuration.

    Rules are stored in Game.alert_settings JSON and define when to trigger alerts
    for players with outstanding balances.
    """

    id: str
    rule_type: Literal['amount_threshold', 'days_overdue']
    threshold_value: int  # cents for amount_threshold, days for days_overdue
    is_active: bool = True

    def __post_init__(self) -> None:
        """Validate alert rule data."""
        if self.rule_type not in ['amount_threshold', 'days_overdue']:
            raise ValueError(f"Invalid rule_type: {self.rule_type}. Must be 'amount_threshold' or 'days_overdue'")

        if not isinstance(self.threshold_value, int) or self.threshold_value <= 0:
            raise ValueError(f"Threshold value must be a positive integer, got: {self.threshold_value}")

        if not isinstance(self.is_active, bool):
            raise ValueError(f"is_active must be a boolean, got: {self.is_active}")

    def to_dict(self) -> dict:
        """Convert to dictionary format for JSON storage."""
        return {
            'id': self.id,
            'rule_type': self.rule_type,
            'threshold_value': self.threshold_value,
            'is_active': self.is_active
        }

    @classmethod
    def from_dict(cls, data: dict) -> AlertRule:
        """Create AlertRule from dictionary."""
        return cls(
            id=data['id'],
            rule_type=data['rule_type'],
            threshold_value=data['threshold_value'],
            is_active=data.get('is_active', True)
        )


@dataclass(frozen=True)
class PlayerViolation:
    """
    Value object representing a single rule violation for a player.

    Captures the specific rule violated, current value, and threshold.
    """

    rule_id: str
    rule_type: str
    current_value: int  # cents for amount, days for time
    threshold_value: int  # cents for amount, days for time

    def __post_init__(self) -> None:
        """Validate violation data and coerce to integers."""
        # Coerce to int if float or Decimal (frozen dataclass requires object.__setattr__)
        if isinstance(self.current_value, (int, float, Decimal)):
            object.__setattr__(self, 'current_value', int(self.current_value))
        else:
            raise ValueError(f"current_value must be numeric, got: {type(self.current_value)}")

        if self.current_value < 0:
            raise ValueError(f"current_value must be non-negative, got: {self.current_value}")

        if isinstance(self.threshold_value, (int, float, Decimal)):
            object.__setattr__(self, 'threshold_value', int(self.threshold_value))
        else:
            raise ValueError(f"threshold_value must be numeric, got: {type(self.threshold_value)}")

        if self.threshold_value <= 0:
            raise ValueError(f"threshold_value must be positive, got: {self.threshold_value}")

    def severity_score(self) -> int:
        """
        Calculate how much over threshold this violation is.

        Used for sorting violations by severity.

        Returns:
            Integer representing how far over the threshold (0 or positive)
        """
        return max(0, self.current_value - self.threshold_value)

    def to_dict(self) -> dict:
        """Convert to dictionary format for API responses."""
        return {
            'rule_id': self.rule_id,
            'rule_type': self.rule_type,
            'current_value': self.current_value,
            'threshold_value': self.threshold_value,
            'severity_score': self.severity_score()
        }


@dataclass(frozen=True)
class PlayerAlertStatus:
    """
    Value object representing the alert status for a single player.

    Aggregates all violations for a player with their balance information.
    """

    player_id: str
    player_name: str
    violations: List[PlayerViolation]
    total_amount_owed: int  # cents (CRITICAL: keep in cents, convert to dollars in API)
    days_since_last_payment: Optional[int]

    def __post_init__(self) -> None:
        """Validate player alert status data and coerce to integers."""
        if not isinstance(self.violations, list):
            raise TypeError("violations must be a list")

        for violation in self.violations:
            if not isinstance(violation, PlayerViolation):
                raise TypeError("All violations must be PlayerViolation instances")

        # Coerce total_amount_owed to int if float or Decimal
        if isinstance(self.total_amount_owed, (int, float, Decimal)):
            object.__setattr__(self, 'total_amount_owed', int(self.total_amount_owed))
        else:
            raise ValueError(f"total_amount_owed must be numeric, got: {type(self.total_amount_owed)}")

        if self.total_amount_owed < 0:
            raise ValueError(f"total_amount_owed must be non-negative, got: {self.total_amount_owed}")

    def has_violations(self) -> bool:
        """Check if this player has any violations."""
        return len(self.violations) > 0

    def violation_count(self) -> int:
        """Get the number of violations."""
        return len(self.violations)

    def to_dict(self) -> dict:
        """Convert to dictionary format for API responses."""
        return {
            'player_id': self.player_id,
            'player_name': self.player_name,
            'violations': [v.to_dict() for v in self.violations],
            'total_amount_owed': self.total_amount_owed,  # Keep in cents
            'days_since_last_payment': self.days_since_last_payment,
            'violation_count': self.violation_count()
        }


@dataclass(frozen=True)
class GameAlertStatus:
    """
    Value object representing the complete alert status for a game.

    Aggregates all player alerts and active rules for the game.
    """

    game_id: str
    player_alerts: List[PlayerAlertStatus]
    active_rules: List[AlertRule]

    def __post_init__(self) -> None:
        """Validate game alert status data."""
        if not isinstance(self.player_alerts, list):
            raise TypeError("player_alerts must be a list")

        for alert in self.player_alerts:
            if not isinstance(alert, PlayerAlertStatus):
                raise TypeError("All player_alerts must be PlayerAlertStatus instances")

        if not isinstance(self.active_rules, list):
            raise TypeError("active_rules must be a list")

        for rule in self.active_rules:
            if not isinstance(rule, AlertRule):
                raise TypeError("All active_rules must be AlertRule instances")

    def total_violations(self) -> int:
        """Get total count of all violations across all players."""
        return sum(p.violation_count() for p in self.player_alerts)

    def players_with_violations(self) -> int:
        """Get count of players who have violations."""
        return len(self.player_alerts)

    def to_dict(self) -> dict:
        """Convert to dictionary format for API responses."""
        return {
            'game_id': self.game_id,
            'player_alerts': [p.to_dict() for p in self.player_alerts],
            'active_rules': [r.to_dict() for r in self.active_rules],
            'total_violations': self.total_violations(),
            'players_with_violations': self.players_with_violations()
        }
