"""
ATLAS Trading Controller

Controls when a trading decision may be sent
to the Paper Trading Engine.

No live orders are placed.
"""

from atlas.models.action import Action
from atlas.models.decision_result import DecisionResult
from atlas.trading.paper_trading_engine import PaperTradingEngine


class TradingController:
    """
    Controls paper-trading execution.

    Prevents the same BUY or SELL decision from
    being executed repeatedly on dashboard refreshes.
    """

    def __init__(self, trader: PaperTradingEngine):
        self.trader = trader
        self._last_actions: dict[str, Action] = {}

    def process(
        self,
        decision: DecisionResult,
        price_usd: float,
        usd_nok: float,
        amount_nok: float = 1000.0,
    ):
        """
        Process one investment decision.

        The same action for the same symbol is only
        executed once until the action changes.
        """

        last_action = self._last_actions.get(
            decision.symbol
        )

        if last_action == decision.action:
            return {
                "executed": False,
                "action": decision.action.value,
                "symbol": decision.symbol,
                "reason": "Decision already executed.",
            }

        if decision.action == Action.HOLD:
            return {
                "executed": False,
                "action": "HOLD",
                "symbol": decision.symbol,
                "reason": "HOLD - no trade executed.",
            }

        result = self.trader.execute(
            decision=decision,
            price_usd=price_usd,
            usd_nok=usd_nok,
            amount_nok=amount_nok,
        )

        if result["executed"]:
            self._last_actions[
                decision.symbol
            ] = decision.action

        return result
