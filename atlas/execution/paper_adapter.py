"""Paper trading execution adapter bridging DecisionExecutionService to
the existing PaperTrading accounting services.

This adapter performs the USD->NOK conversion and delegates to
PortfolioService and TradingService to preserve legacy accounting.
"""

from atlas.execution.models import ExecutionResult, ExecutionStatus, ExecutionRequest
from atlas.models.action import Action
from atlas.services.portfolio_service import PortfolioService
from atlas.trading.trading_service import TradingService
from atlas.services.exchange_rate_service import ExchangeRateService
from atlas.algorithms.position_exit import PositionContext, PositionAction, PositionExitEngine


class PaperTradingExecutionAdapter:
    """Adapter that executes DecisionExecutionService requests in the
    paper-trading accounting layer.

    It intentionally does not re-run risk logic. The DecisionExecutionService
    must only call this adapter after a RiskManager approval has been applied.
    """

    def __init__(
        self,
        portfolio: PortfolioService,
        trading: TradingService | None,
        exchange_service: ExchangeRateService,
        accumulation_drop_pct: float = 2.0,
    ) -> None:
        self.portfolio = portfolio
        self.trading = trading or TradingService()
        self.portfolio.restore_from_trades(self.trading._history)
        # Keep a reference to ExchangeRateService and fetch rate at execute-time.
        self.exchange_service = exchange_service
        self.position_exit_engine = PositionExitEngine(
            accumulation_drop_pct=accumulation_drop_pct,
        )

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        # Validate adapter inputs at this boundary:
        if request.price is None:
            raise ValueError("Paper trading adapter requires a price_usd")

        price_usd = float(request.price)

        # Fetch USD/NOK at execution time; allow ExchangeRateService errors to propagate.
        exchange = self.exchange_service.get_rate("USD", "NOK")
        usd_nok = float(exchange.rate)
        if usd_nok <= 0.0:
            raise RuntimeError("Invalid USD/NOK rate from ExchangeRateService")

        # Convert execution quantity (units) and price_usd to NOK amount
        # according to the required adapter responsibility.
        if request.action is Action.BUY:
            existing_position = self.portfolio._positions.get(request.symbol)

            current_position = 0.0
            accumulation_price = None

            if existing_position is not None:
                current_position = existing_position.quantity
                accumulation_price = existing_position.last_buy_price_usd

            position_context = PositionContext(
                current_position=current_position,
                entry_price=accumulation_price,
                current_price=price_usd,
                peak_price=(
                    existing_position.average_price_usd
                    if existing_position is not None
                    else None
                ),
                confidence=1.0,
                risk_score=0.0,
            )

            position_decision = self.position_exit_engine.decide(
                Action.BUY,
                position_context,
            )

            if position_decision.action is PositionAction.HOLD:
                return None

            if position_decision.action is not PositionAction.ENTER:
                raise RuntimeError(
                    f"Unexpected position action for BUY: {position_decision.action}"
                )

            amount_nok = request.quantity * price_usd * usd_nok

            position = self.portfolio.buy(
                symbol=request.symbol,
                amount_nok=amount_nok,
                price_usd=price_usd,
                usd_nok=usd_nok,
            )

            self.trading.record_buy(
                symbol=request.symbol,
                quantity=request.quantity,
                price_usd=price_usd,
                amount_nok=amount_nok,
                reason="ExecutionAdapter: paper BUY",
                analysis_snapshot_id=request.analysis_snapshot_id,
            )
            return ExecutionResult(
                status=ExecutionStatus.SIMULATED,
                symbol=request.symbol,
                action=request.action,
                quantity=request.quantity,
                message="paper BUY executed",
            )

        if request.action is Action.SELL:
            # For SELL we must respect PortfolioService.sell contract.
            result = self.portfolio.sell(
                symbol=request.symbol,
                price_usd=price_usd,
                usd_nok=usd_nok,
                quantity=request.quantity,
            )

            self.trading.record_sell(
                symbol=request.symbol,
                quantity=result["quantity"],
                price_usd=price_usd,
                amount_nok=result["sale_value_nok"],
                realized_pnl_nok=result["realized_pnl_nok"],
                reason="ExecutionAdapter: paper SELL",
                analysis_snapshot_id=request.analysis_snapshot_id,
            )

            return ExecutionResult(
                status=ExecutionStatus.SIMULATED,
                symbol=request.symbol,
                action=request.action,
                quantity=result["quantity"],
                message="paper SELL executed",
            )

        raise ValueError("unsupported execution action")
