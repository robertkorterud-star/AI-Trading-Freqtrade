"""
ATLAS Paper Trading Engine

Connects DecisionEngine, RiskEngine, PortfolioService
and TradingService.

No live orders are placed.
"""

from atlas.models.action import Action
from atlas.models.decision_result import DecisionResult
from atlas.risk.risk_engine import RiskEngine
from atlas.services.portfolio_service import PortfolioService
from atlas.trading.trading_cost_model import TradingCostModel
from atlas.trading.trading_service import TradingService


class PaperTradingEngine:
    """
    Executes approved paper trades.

    Flow:

        Decision
            ↓
        Expected Return / Cost Gate
            ↓
        RiskEngine
            ↓
        PaperTradingEngine
            ├── PortfolioService
            └── TradingService
    """

    def __init__(
        self,
        portfolio: PortfolioService,
        risk: RiskEngine,
        trading: TradingService | None = None,
        cost_model: TradingCostModel | None = None,
    ):
        self.portfolio = portfolio
        self.risk = risk
        self.trading = trading or TradingService()
        self.cost_model = cost_model or TradingCostModel()

    def execute(
        self,
        decision: DecisionResult,
        price_usd: float,
        usd_nok: float,
        amount_nok: float = 1000.0,
    ):
        """
        Evaluate and execute a paper trade.

        BUY:
            amount_nok determines how much cash to invest.
            A non-zero expected return must cover estimated
            round-trip direct trading costs.

        SELL:
            The complete existing position is sold.

        HOLD:
            Nothing happens.
        """

        if (
            decision.action == Action.BUY
            and decision.expected_return != 0.0
        ):
            net_return = self.cost_model.net_return(
                decision.expected_return
            )

            if net_return <= 0.0:
                return {
                    "executed": False,
                    "action": decision.action.value,
                    "symbol": decision.symbol,
                    "reason": (
                        "BUY blocked: expected return does not "
                        "cover estimated round-trip trading costs."
                    ),
                    "expected_return": decision.expected_return,
                    "estimated_round_trip_cost": (
                        self.cost_model.round_trip_cost_rate
                    ),
                    "net_expected_return": net_return,
                }

        portfolio = self.portfolio.as_dict(usd_nok)

        position_exists = any(
            position["symbol"] == decision.symbol
            for position in portfolio["positions"]
        )

        risk_result = self.risk.evaluate(
            decision=decision,
            total_equity_nok=portfolio[
                "total_equity_nok"
            ],
            cash_nok=portfolio[
                "cash_nok"
            ],
            requested_amount_nok=amount_nok,
            position_exists=position_exists,
        )

        if not risk_result.approved:
            return {
                "executed": False,
                "action": decision.action.value,
                "symbol": decision.symbol,
                "reason": risk_result.reason,
                "risk": risk_result,
            }

        # ---------------------------------------------
        # BUY
        # ---------------------------------------------

        if decision.action == Action.BUY:

            position = self.portfolio.buy(
                symbol=decision.symbol,
                amount_nok=amount_nok,
                price_usd=price_usd,
                usd_nok=usd_nok,
            )

            trade_record = self.trading.record_buy(
                symbol=decision.symbol,
                quantity=position.quantity,
                price_usd=price_usd,
                amount_nok=amount_nok,
                reason="AI BUY approved.",
            )

            return {
                "executed": True,
                "action": "BUY",
                "symbol": decision.symbol,
                "quantity": position.quantity,
                "price_usd": price_usd,
                "amount_nok": amount_nok,
                "reason": "Paper BUY executed.",
                "trade": trade_record.as_dict(),
                "risk": risk_result,
            }

        # ---------------------------------------------
        # SELL
        # ---------------------------------------------

        if decision.action == Action.SELL:

            trade = self.portfolio.sell(
                symbol=decision.symbol,
                price_usd=price_usd,
                usd_nok=usd_nok,
            )

            trade_record = self.trading.record_sell(
                symbol=decision.symbol,
                quantity=trade["quantity"],
                price_usd=price_usd,
                amount_nok=trade["sale_value_nok"],
                realized_pnl_nok=trade[
                    "realized_pnl_nok"
                ],
                reason="AI SELL approved.",
            )

            return {
                "executed": True,
                "action": "SELL",
                "symbol": decision.symbol,
                "quantity": trade[
                    "quantity"
                ],
                "sale_value_nok": trade[
                    "sale_value_nok"
                ],
                "realized_pnl_nok": trade[
                    "realized_pnl_nok"
                ],
                "reason": "Paper SELL executed.",
                "trade": trade_record.as_dict(),
                "risk": risk_result,
            }

        # ---------------------------------------------
        # HOLD
        # ---------------------------------------------

        return {
            "executed": False,
            "action": "HOLD",
            "symbol": decision.symbol,
            "reason": "HOLD - no trade executed.",
            "risk": risk_result,
        }
