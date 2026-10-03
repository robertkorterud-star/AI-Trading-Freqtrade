"""
ATLAS Dry-Run Trader

Executes ATLAS decisions against a virtual portfolio.

This module deliberately performs no live exchange operations.
"""

from dataclasses import dataclass

from atlas.algorithms.position_exit import (
    PositionAction,
    PositionContext,
    PositionExitEngine,
)
from atlas.models.action import Action
from atlas.risk.risk_engine import RiskEngine

from atlas.trading.paper_portfolio import PaperPortfolio
from atlas.trading.trade_journal import TradeJournal
from atlas.trading.trading_cost_model import TradingCostModel


@dataclass(frozen=True)
class DryRunResult:
    """Result of one dry-run decision."""

    symbol: str
    action: PositionAction
    quantity: float
    price: float
    target_position: float
    realized_pnl: float
    equity: float
    reason: str
    executed: bool = True


class DryRunTrader:
    """
    Simulated execution layer for ATLAS.

    The trader receives an upstream BUY/SELL/HOLD decision,
    passes it through the PositionExitEngine and executes the
    resulting position change against a paper portfolio.
    """

    def __init__(
        self,
        portfolio: PaperPortfolio | None = None,
        journal: TradeJournal | None = None,
        position_engine: PositionExitEngine | None = None,
        risk_engine: RiskEngine | None = None,
        cost_model: TradingCostModel | None = None,
        max_position_value: float = 10_000.0,
    ):
        if max_position_value <= 0.0:
            raise ValueError(
                "max_position_value must be greater than zero"
            )

        self.portfolio = portfolio or PaperPortfolio()
        self.journal = journal or TradeJournal()
        self.position_engine = (
            position_engine or PositionExitEngine()
        )
        self.risk_engine = risk_engine or RiskEngine()
        self.cost_model = cost_model or TradingCostModel(
            fee_rate=self.portfolio.fee_rate
        )
        self.max_position_value = max_position_value

    def process_signal(
        self,
        symbol: str,
        action: Action,
        price: float,
        confidence: float,
        risk_score: float = 0.0,
        reason: str = "",
        expected_return: float | None = None,
    ) -> DryRunResult:
        """
        Process one ATLAS decision.

        ``expected_return`` is an optional gross decimal return estimate,
        e.g. 0.01 for +1%. When supplied for a BUY, the trade is blocked
        if estimated direct round-trip costs would consume the expected
        return. The cost model is a decision gate only; actual paper
        trading fees remain applied by PaperPortfolio exactly once.

        Quantity is derived from the target portfolio fraction and
        current market price.
        """

        if price <= 0.0:
            raise ValueError("price must be greater than zero")

        if expected_return is not None and not isinstance(
            expected_return, (int, float)
        ):
            raise TypeError("expected_return must be a number or None")

        # DecisionCore uses its own DecisionAction enum while the
        # execution/risk layer uses atlas.models.action.Action.
        # Normalize the upstream decision at this boundary.
        action_value = getattr(action, "value", action)

        if isinstance(action_value, str):
            normalized_action = action_value.strip().upper()
            action = Action(normalized_action)

        current = self.portfolio.positions.get(symbol)

        current_position = 0.0

        if current is not None:
            current_position = min(
                1.0,
                (current.quantity * price)
                / self.max_position_value,
            )

        portfolio_equity = self.portfolio.equity(
            {symbol: price}
        )

        # Expected-return gate applies to new BUY decisions only.
        # Exits must remain available even when the expected future
        # return is no longer attractive.
        if action is Action.BUY and expected_return is not None:
            net_return = self.cost_model.net_return(
                float(expected_return)
            )

            if net_return <= 0.0:
                blocked = self.position_engine.decide(
                    Action.HOLD,
                    PositionContext(
                        current_position=current_position,
                        entry_price=(
                            current.average_price
                            if current is not None
                            else None
                        ),
                        current_price=price,
                        peak_price=(
                            current.average_price
                            if current is not None
                            else None
                        ),
                        confidence=confidence,
                        risk_score=risk_score,
                    ),
                )

                equity = self.portfolio.equity(
                    {symbol: price}
                )

                return DryRunResult(
                    symbol=symbol,
                    action=blocked.action,
                    quantity=0.0,
                    price=price,
                    target_position=blocked.target_position,
                    realized_pnl=0.0,
                    equity=equity,
                    reason=(
                        "Trading cost blocked: expected gross return "
                        f"{float(expected_return):.2%} is below estimated "
                        f"round-trip costs "
                        f"{self.cost_model.round_trip_cost_rate:.2%}"
                    ),
                    executed=False,
                )

        # RiskEngine must evaluate the actual order value,
        # not the configured maximum position size.
        if action is Action.BUY:
            requested_amount = max(
                0.0,
                min(
                    self.max_position_value,
                    self.portfolio.cash,
                ),
            )
        elif action is Action.SELL and current is not None:
            requested_amount = max(
                0.0,
                current.quantity * price,
            )
        else:
            requested_amount = 0.0

        context = PositionContext(
            current_position=current_position,
            entry_price=(
                current.average_price
                if current is not None
                else None
            ),
            current_price=price,
            peak_price=(
                current.average_price
                if current is not None
                else None
            ),
            confidence=confidence,
            risk_score=risk_score,
        )

        position_decision = self.position_engine.decide(
            action,
            context,
        )

        risk_action = (
            Action.SELL
            if position_decision.action is PositionAction.EXIT
            else action
        )
        risk_requested_amount = (
            current.quantity * price
            if (
                risk_action is Action.SELL
                and current is not None
            )
            else requested_amount
        )

        risk_result = self.risk_engine.evaluate(
            decision=type(
                "DryRunDecision",
                (),
                {
                    "symbol": symbol,
                    "action": risk_action,
                },
            )(),
            total_equity_nok=portfolio_equity,
            cash_nok=self.portfolio.cash,
            requested_amount_nok=risk_requested_amount,
            position_exists=current is not None,
        )

        if not risk_result.approved:
            blocked = self.position_engine.decide(
                Action.HOLD,
                context,
            )

            equity = self.portfolio.equity(
                {symbol: price}
            )

            return DryRunResult(
                symbol=symbol,
                action=blocked.action,
                quantity=0.0,
                price=price,
                target_position=blocked.target_position,
                realized_pnl=0.0,
                equity=equity,
                reason=f"Risk blocked: {risk_result.reason}",
                executed=False,
            )

        context = PositionContext(
            current_position=current_position,
            entry_price=(
                current.average_price
                if current is not None
                else None
            ),
            current_price=price,
            peak_price=(
                current.average_price
                if current is not None
                else None
            ),
            confidence=confidence,
            risk_score=risk_score,
        )

        decision = self.position_engine.decide(
            action,
            context,
        )

        current_quantity = (
            current.quantity
            if current is not None
            else 0.0
        )

        target_quantity = (
            decision.target_position
            * self.max_position_value
            / price
        )

        quantity = 0.0
        realized_pnl = 0.0

        if decision.action is PositionAction.ENTER:
            quantity = max(
                0.0,
                target_quantity - current_quantity,
            )

            if quantity > 0.0:
                self.portfolio.buy(
                    symbol,
                    price,
                    quantity,
                )

        elif decision.action is PositionAction.REDUCE:
            quantity = max(
                0.0,
                current_quantity - target_quantity,
            )

            if quantity > 0.0:
                realized_pnl = self.portfolio.sell(
                    symbol,
                    price,
                    quantity,
                )

        elif decision.action is PositionAction.EXIT:
            quantity = current_quantity

            if quantity > 0.0:
                realized_pnl = self.portfolio.sell(
                    symbol,
                    price,
                    quantity,
                )

        equity = self.portfolio.equity(
            {symbol: price}
        )

        fee = 0.0

        if decision.action in {
            PositionAction.ENTER,
            PositionAction.REDUCE,
            PositionAction.EXIT,
        }:
            fee = (
                quantity
                * price
                * self.portfolio.fee_rate
            )

        self.journal.record(
            symbol=symbol,
            action=decision.action.value,
            quantity=quantity,
            price=price,
            fee=fee,
            realized_pnl=realized_pnl,
            reason=reason or decision.reason,
            confidence=confidence,
            risk_score=risk_score,
            equity_after=equity,
        )

        return DryRunResult(
            symbol=symbol,
            action=decision.action,
            quantity=quantity,
            price=price,
            target_position=decision.target_position,
            realized_pnl=realized_pnl,
            equity=equity,
            reason=decision.reason,
        )
