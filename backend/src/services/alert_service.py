"""
Alert Service.

Business logic for payment alert management with on-demand violation computation.
"""

from datetime import datetime, timezone
from typing import List
from uuid import uuid4
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.orm.attributes import flag_modified
import logging

from db.models import Game, Player
from domain.alerts.value_objects import (
    AlertRule,
    PlayerViolation,
    PlayerAlertStatus,
    GameAlertStatus
)
from domain.poker.value_objects import GameId
from infrastructure.persistence.sqlalchemy.payment_repository import SQLAlchemyPaymentBalanceRepository
from services.audit_middleware import audit_context

logger = logging.getLogger(__name__)


class AlertService:
    """
    Service for managing payment alert rules and computing violation status.

    This service handles CRUD operations on alert rules stored in Game.alert_settings
    and computes violations on-demand from existing PaymentBalance data.
    """

    def __init__(self, db_session: DBSession):
        """
        Initialize the alert service.

        Args:
            db_session: SQLAlchemy database session

        Raises:
            ValueError: If db_session is None
        """
        if db_session is None:
            raise ValueError("db_session is required")

        self._db_session = db_session
        self._balance_repo = SQLAlchemyPaymentBalanceRepository(db_session)

    def get_alert_rules(self, game_id: str) -> List[AlertRule]:
        """
        Get all alert rules for a game.

        Args:
            game_id: Game identifier

        Returns:
            List of AlertRule objects

        Raises:
            ValueError: If game not found
        """
        game = self._db_session.query(Game).filter(Game.id == game_id).first()
        if not game:
            raise ValueError(f"Game {game_id} not found")

        rules_data = game.alert_settings.get('rules', [])
        return [AlertRule.from_dict(r) for r in rules_data]

    def create_alert_rule(
        self,
        game_id: str,
        rule_type: str,
        threshold_value: int,
        admin_code: str
    ) -> AlertRule:
        """
        Create a new alert rule (admin only).

        Args:
            game_id: Game identifier
            rule_type: 'amount_threshold' or 'days_overdue'
            threshold_value: Threshold in cents (for amount) or days
            admin_code: Admin authentication code

        Returns:
            Created AlertRule

        Raises:
            ValueError: If game not found or invalid parameters
            PermissionError: If invalid admin code
        """
        game = self._db_session.query(Game).filter(Game.id == game_id).first()
        if not game:
            raise ValueError("Game not found")

        if game.admin_code != admin_code:
            raise PermissionError("Invalid admin code")

        # Create rule with validation
        new_rule = AlertRule(
            id=str(uuid4()),
            rule_type=rule_type,
            threshold_value=threshold_value,
            is_active=True
        )

        # Add to JSON array with audit logging
        with audit_context(
            operation_type="alert_rule_create",
            game_id=game_id,
            actor_kind="admin_code",
            actor_id=admin_code[:8] + "..."
        ):
            settings = game.alert_settings.copy() if game.alert_settings else {}

            if 'rules' not in settings:
                settings['rules'] = []

            settings['rules'].append(new_rule.to_dict())

            game.alert_settings = settings
            flag_modified(game, 'alert_settings')
            # Caller commits

        logger.info(f"Created alert rule {new_rule.id} for game {game_id}: {rule_type} @ {threshold_value}")

        return new_rule

    def update_alert_rule(
        self,
        game_id: str,
        rule_id: str,
        threshold_value: int,
        is_active: bool,
        admin_code: str
    ) -> AlertRule:
        """
        Update an existing alert rule's threshold and active status (admin only).

        Args:
            game_id: Game identifier
            rule_id: Rule identifier
            threshold_value: New threshold value
            is_active: Whether rule is active
            admin_code: Admin authentication code

        Returns:
            Updated AlertRule

        Raises:
            ValueError: If game or rule not found
            PermissionError: If invalid admin code
        """
        game = self._db_session.query(Game).filter(Game.id == game_id).first()
        if not game:
            raise ValueError("Game not found")

        if game.admin_code != admin_code:
            raise PermissionError("Invalid admin code")

        with audit_context(
            operation_type="alert_rule_update",
            game_id=game_id,
            actor_kind="admin_code",
            actor_id=admin_code[:8] + "..."
        ):
            settings = game.alert_settings.copy() if game.alert_settings else {}
            rules = settings.get('rules', [])

            updated_rule_dict = None
            for rule_dict in rules:
                if rule_dict['id'] == rule_id:
                    rule_dict['threshold_value'] = threshold_value
                    rule_dict['is_active'] = is_active
                    updated_rule_dict = rule_dict
                    break

            if not updated_rule_dict:
                raise ValueError(f"Rule {rule_id} not found")

            settings['rules'] = rules
            game.alert_settings = settings
            flag_modified(game, 'alert_settings')
            # Caller commits

        logger.info(f"Updated alert rule {rule_id} for game {game_id}: threshold={threshold_value}, active={is_active}")

        return AlertRule.from_dict(updated_rule_dict)

    def delete_alert_rule(
        self,
        game_id: str,
        rule_id: str,
        admin_code: str
    ) -> bool:
        """
        Delete an alert rule (admin only).

        Args:
            game_id: Game identifier
            rule_id: Rule identifier
            admin_code: Admin authentication code

        Returns:
            True if rule was deleted, False if not found

        Raises:
            ValueError: If game not found
            PermissionError: If invalid admin code
        """
        game = self._db_session.query(Game).filter(Game.id == game_id).first()
        if not game:
            raise ValueError("Game not found")

        if game.admin_code != admin_code:
            raise PermissionError("Invalid admin code")

        with audit_context(
            operation_type="alert_rule_delete",
            game_id=game_id,
            actor_kind="admin_code",
            actor_id=admin_code[:8] + "..."
        ):
            settings = game.alert_settings.copy() if game.alert_settings else {}
            rules = settings.get('rules', [])

            original_count = len(rules)
            filtered_rules = [r for r in rules if r['id'] != rule_id]

            if len(filtered_rules) == original_count:
                return False  # Rule not found

            settings['rules'] = filtered_rules
            game.alert_settings = settings
            flag_modified(game, 'alert_settings')
            # Caller commits

        logger.info(f"Deleted alert rule {rule_id} for game {game_id}")

        return True

    def compute_alert_status(self, game_id: str) -> GameAlertStatus:
        """
        Compute alert violations on-demand from current player balances.

        This method evaluates all active alert rules against current player balances
        and returns aggregated violation status. No data is cached or persisted.

        CRITICAL: Uses balance_negative_since for days_overdue calculation.
        FAIL FAST: Raises ValueError if invariants violated.

        Args:
            game_id: Game identifier

        Returns:
            GameAlertStatus with all violations

        Raises:
            ValueError: If game not found or invariants violated
        """
        # Get active rules
        rules = [r for r in self.get_alert_rules(game_id) if r.is_active]

        # Get all player balances
        domain_game_id = GameId(game_id)
        balances = self._balance_repo.get_all_balances_for_game(domain_game_id)

        player_alerts = []

        for balance in balances:
            # CRITICAL: Only alert for players who OWE money (negative balance)
            # balance.balance is a Money object, access .amount for cents
            if balance.balance.amount >= 0:
                continue  # Skip players who are owed money or settled

            amount_owed_cents = abs(balance.balance.amount)

            # FAIL FAST: Use new field (no fallback)
            # This will raise ValueError if balance is negative but balance_negative_since is NULL
            try:
                days_overdue = balance.days_balance_negative(datetime.now(timezone.utc))
            except ValueError as e:
                # CRITICAL: This should never happen due to constraints
                logger.error(
                    f"INVARIANT VIOLATION in alert service: {e}",
                    extra={
                        "game_id": game_id,
                        "player_id": str(balance.player_id),
                        "balance_cents": balance.balance.amount
                    }
                )
                raise  # FAIL FAST - re-raise immediately

            violations = []

            # Check each active rule
            for rule in rules:
                if rule.rule_type == 'amount_threshold':
                    if amount_owed_cents > rule.threshold_value:
                        violations.append(PlayerViolation(
                            rule_id=rule.id,
                            rule_type='amount_threshold',
                            current_value=amount_owed_cents,
                            threshold_value=rule.threshold_value
                        ))

                elif rule.rule_type == 'days_overdue':
                    # Use days_balance_negative (how long balance has been negative)
                    if days_overdue is not None and days_overdue > rule.threshold_value:
                        violations.append(PlayerViolation(
                            rule_id=rule.id,
                            rule_type='days_overdue',
                            current_value=days_overdue,
                            threshold_value=rule.threshold_value
                        ))

            # Only create alert status if player has violations
            if violations:
                player_name = self._get_player_name(str(balance.player_id))
                player_alerts.append(PlayerAlertStatus(
                    player_id=str(balance.player_id),
                    player_name=player_name,
                    violations=violations,
                    total_amount_owed=amount_owed_cents,  # Keep in cents
                    days_since_last_payment=days_overdue  # Now represents days balance negative
                ))

        logger.debug(f"Computed alert status for game {game_id}: {len(player_alerts)} players with violations")

        return GameAlertStatus(
            game_id=game_id,
            player_alerts=player_alerts,
            active_rules=rules
        )

    def _get_player_name(self, player_id: str) -> str:
        """
        Helper method to get player display name.

        Args:
            player_id: Player identifier

        Returns:
            Player display name or "Unknown" if not found
        """
        player = self._db_session.query(Player).filter(Player.id == player_id).first()
        return player.display_name if player else "Unknown"
