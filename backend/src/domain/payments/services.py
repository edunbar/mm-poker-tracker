"""
Payment domain services.

Domain services that implement complex business logic for payment processing.
"""

from typing import List, Tuple
from decimal import Decimal

from .entities import PlayerBalance, SettlementSuggestion
from ..poker.value_objects import Money


class SettlementOptimizer:
    """
    Domain service for optimizing debt settlements.

    Uses debt minimization algorithm to minimize the number of transactions
    needed to settle all balances.
    """

    @staticmethod
    def calculate_optimal_settlements(balances: List[PlayerBalance]) -> List[SettlementSuggestion]:
        """
        Calculate optimal payment suggestions to minimize transactions.

        Args:
            balances: List of player balances

        Returns:
            List of settlement suggestions
        """
        # Convert to creditors (owed money) and debtors (owe money)
        creditors = []
        debtors = []

        for balance in balances:
            net_position = balance.net_position
            if net_position.is_positive():
                creditors.append((balance, net_position))
            elif not net_position.is_zero():
                debtors.append((balance, net_position))

        # Sort creditors by amount owed (desc), debtors by debt (asc)
        creditors.sort(key=lambda x: x[1].amount, reverse=True)
        debtors.sort(key=lambda x: x[1].amount)

        suggestions = []

        # Debt minimization algorithm
        while creditors and debtors:
            creditor_balance, creditor_amount = creditors[0]
            debtor_balance, debtor_amount = debtors[0]

            # Amount to transfer is minimum of what's owed and what's due
            transfer_amount = min(creditor_amount, Money(str(abs(debtor_amount.amount))))

            if transfer_amount >= Money("0.01"):  # Only suggest payments of 1 cent or more
                suggestions.append(SettlementSuggestion(
                    payer_id=debtor_balance.player_id,
                    payer_name=f"Player {debtor_balance.player_id}",  # Will be filled by service
                    recipient_id=creditor_balance.player_id,
                    recipient_name=f"Player {creditor_balance.player_id}",  # Will be filled by service
                    amount=transfer_amount
                ))

            # Update amounts
            creditor_amount = creditor_amount - transfer_amount
            debtor_amount = debtor_amount + transfer_amount

            # Update the tuples in the lists
            creditors[0] = (creditor_balance, creditor_amount)
            debtors[0] = (debtor_balance, debtor_amount)

            # Remove players who are now settled (less than 1 cent remaining)
            if creditor_amount < Money("0.01"):
                creditors.pop(0)
            if debtor_amount > Money("-0.01"):
                debtors.pop(0)

        return suggestions

    @staticmethod
    def validate_settlement_balance(suggestions: List[SettlementSuggestion]) -> bool:
        """
        Validate that the settlement suggestions balance out.

        Args:
            suggestions: List of settlement suggestions

        Returns:
            True if settlements balance, False otherwise
        """
        total_in = Money.zero()
        total_out = Money.zero()

        for suggestion in suggestions:
            total_out = total_out + suggestion.amount  # Money flowing out from payers
            total_in = total_in + suggestion.amount    # Money flowing in to recipients

        # Should balance (within rounding errors)
        difference = abs((total_in - total_out).amount)
        return difference < Decimal("0.01")


class PaymentValidator:
    """Domain service for validating payment operations."""

    @staticmethod
    def validate_payment_transaction(
        payer_balance: PlayerBalance,
        recipient_balance: PlayerBalance,
        payment_amount: Money
    ) -> List[str]:
        """
        Validate a payment transaction.

        Args:
            payer_balance: Payer's current balance
            recipient_balance: Recipient's current balance
            payment_amount: Amount being paid

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        if not payment_amount.is_positive():
            errors.append("Payment amount must be positive")

        if payer_balance.player_id == recipient_balance.player_id:
            errors.append("Cannot pay yourself")

        if payer_balance.game_id != recipient_balance.game_id:
            errors.append("Players must be in the same game")

        # Check if payment makes sense given current balances
        payer_net = payer_balance.net_position
        if payer_net.is_positive() and payment_amount > payer_net:
            errors.append(
                f"Payment amount ${payment_amount.amount} exceeds what payer owes "
                f"(${abs(payer_net.amount)})"
            )

        return errors

    @staticmethod
    def suggest_payment_amount(payer_balance: PlayerBalance, recipient_balance: PlayerBalance) -> Money:
        """
        Suggest an appropriate payment amount between two players.

        Args:
            payer_balance: Payer's balance
            recipient_balance: Recipient's balance

        Returns:
            Suggested payment amount
        """
        payer_net = payer_balance.net_position
        recipient_net = recipient_balance.net_position

        # If payer owes money and recipient is owed money
        if not payer_net.is_positive() and recipient_net.is_positive():
            # Suggest the minimum of what's owed and what's due
            return min(Money(str(abs(payer_net.amount))), recipient_net)

        # Otherwise suggest zero (no payment needed)
        return Money.zero()