"""
ATLAS Risk Engine

Controls whether a paper-trading decision is allowed
to proceed.

This engine does NOT place orders.
"""

from dataclasses import dataclass

from atlas.models.action import Action
from atlas.models.decision_result import DecisionResult


@dataclass(slots=True)
class RiskResult:
    """Result returned by the Risk Engine."""

    approved: bool
    reason: str
    max_position_nok: float
    requested_amount_nok: float


class RiskEngine:
    """
    Risk controls for ATLAS paper trading.

    v0.1 rules:
    - Maximum 20% of equity in a new position.
    - HOLD is never executed.
    - BUY requires sufficient cash.
    - SELL requires an existing position.
    - No real orders are ever placed.
    """

    MAX_POSITION_PERCENT = 20.0

    def evaluate(
        self,
        decision: DecisionResult,
        total_equity_nok: float,
        cash_nok: float,
        requested_amount_nok: float,
        position_exists: bool = False,
    ) -> RiskResult:

        total_equity_nok = float(total_equity_nok)
        cash_nok = float(cash_nok)
        requested_amount_nok = float(requested_amount_nok)

        if total_equity_nok <= 0:
            return RiskResult(
                approved=False,
                reason="Invalid total equity.",
                max_position_nok=0.0,
                requested_amount_nok=requested_amount_nok,
            )

        max_position_nok = (
            total_equity_nok
            * self.MAX_POSITION_PERCENT
            / 100.0
        )

        if decision.action == Action.HOLD:
            return RiskResult(
                approved=False,
                reason="HOLD decision - no trade required.",
                max_position_nok=round(max_position_nok, 2),
                requested_amount_nok=round(requested_amount_nok, 2),
            )

        if decision.action == Action.BUY:

            if requested_amount_nok <= 0:
                return RiskResult(
                    approved=False,
                    reason="BUY amount must be greater than zero.",
                    max_position_nok=round(max_position_nok, 2),
                    requested_amount_nok=round(requested_amount_nok, 2),
                )

            if requested_amount_nok > cash_nok:
                return RiskResult(
                    approved=False,
                    reason="Insufficient cash.",
                    max_position_nok=round(max_position_nok, 2),
                    requested_amount_nok=round(requested_amount_nok, 2),
                )

            if requested_amount_nok > max_position_nok:
                return RiskResult(
                    approved=False,
                    reason=(
                        "Requested position exceeds "
                        "the 20% risk limit."
                    ),
                    max_position_nok=round(max_position_nok, 2),
                    requested_amount_nok=round(requested_amount_nok, 2),
                )

            return RiskResult(
                approved=True,
                reason="BUY approved by Risk Engine.",
                max_position_nok=round(max_position_nok, 2),
                requested_amount_nok=round(requested_amount_nok, 2),
            )

        if decision.action == Action.SELL:

            if not position_exists:
                return RiskResult(
                    approved=False,
                    reason="SELL rejected - no open position.",
                    max_position_nok=round(max_position_nok, 2),
                    requested_amount_nok=round(requested_amount_nok, 2),
                )

            return RiskResult(
                approved=True,
                reason="SELL approved by Risk Engine.",
                max_position_nok=round(max_position_nok, 2),
                requested_amount_nok=round(requested_amount_nok, 2),
            )

        return RiskResult(
            approved=False,
            reason="Unknown trading action.",
            max_position_nok=round(max_position_nok, 2),
            requested_amount_nok=round(requested_amount_nok, 2),
        )
