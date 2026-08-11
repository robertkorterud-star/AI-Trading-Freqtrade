"""
ATLAS Trading Runtime

Connects ATLAS configuration and trading execution.

No live orders are placed.
"""

from atlas.core.config import AtlasConfig
from atlas.models.decision_result import DecisionResult
from atlas.trading.trading_controller import TradingController


class TradingRuntime:
    """
    Controls whether ATLAS is allowed to execute
    a trading decision.
    """

    def __init__(
        self,
        config: AtlasConfig,
        controller: TradingController,
    ):
        self.config = config
        self.controller = controller

    def execute(
        self,
        decision: DecisionResult,
        price_usd: float,
        usd_nok: float,
        amount_nok: float = 1000.0,
    ):
        if not self.config.paper_trading:
            return {
                "executed": False,
                "action": decision.action.value,
                "symbol": decision.symbol,
                "reason": "Paper trading is disabled.",
            }

        if self.config.trading_mode == "advisor":
            return {
                "executed": False,
                "action": decision.action.value,
                "symbol": decision.symbol,
                "reason": "Trading mode is advisor.",
            }

        if amount_nok > self.config.capital_limit:
            return {
                "executed": False,
                "action": decision.action.value,
                "symbol": decision.symbol,
                "reason": "Requested amount exceeds capital limit.",
            }

        return self.controller.process(
            decision=decision,
            price_usd=price_usd,
            usd_nok=usd_nok,
            amount_nok=amount_nok,
        )
