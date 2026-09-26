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
    ) -> None:
        self.portfolio = portfolio
        self.trading = trading or TradingService()
        persisted_trades = self.trading.history()
        if persisted_trades:
            self._restore_latest_valid_history(persisted_trades)
        # Keep a reference to ExchangeRateService and fetch rate at execute-time.
        self.exchange_service = exchange_service

    def _restore_latest_valid_history(self, persisted_trades):
        """Restore the newest valid paper-account period from trade history.

        Legacy/corrupt trades remain in TradingService for audit history. If
        the full ledger cannot describe a valid current account, progressively
        discard only the oldest replay inputs until the newest valid suffix can
        be reconstructed.
        """

        def value(trade, key):
            if isinstance(trade, dict):
                return trade[key]
            return getattr(trade, key)

        ordered_trades = sorted(
            persisted_trades,
            key=lambda trade: value(trade, "timestamp"),
        )

        for start in range(len(ordered_trades)):
            try:
                self.portfolio.restore_from_trades(
                    ordered_trades[start:]
                )
            except (KeyError, TypeError, ValueError):
                continue

            snapshot = self.portfolio.as_dict(1.0)
            if snapshot["cash_nok"] >= -1e-9:
                return

        self.portfolio.reset()

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
            amount_nok = request.quantity * price_usd * usd_nok
            portfolio_state = self.portfolio.snapshot_state()

            position = self.portfolio.buy(
                symbol=request.symbol,
                amount_nok=amount_nok,
                price_usd=price_usd,
                usd_nok=usd_nok,
            )

            try:
                self.trading.record_buy(
                    symbol=request.symbol,
                    quantity=request.quantity,
                    price_usd=price_usd,
                    amount_nok=amount_nok,
                    reason="ExecutionAdapter: paper BUY",
                    analysis_snapshot_id=request.analysis_snapshot_id,
                )
            except Exception:
                self.portfolio.restore_state(portfolio_state)
                raise

            return ExecutionResult(
                status=ExecutionStatus.SIMULATED,
                symbol=request.symbol,
                action=request.action,
                quantity=request.quantity,
                message="paper BUY executed",
            )

        if request.action is Action.SELL:
            # For SELL we must respect PortfolioService.sell contract.
            portfolio_state = self.portfolio.snapshot_state()
            result = self.portfolio.sell(
                symbol=request.symbol,
                price_usd=price_usd,
                usd_nok=usd_nok,
                quantity=request.quantity,
            )

            try:
                self.trading.record_sell(
                    symbol=request.symbol,
                    quantity=result["quantity"],
                    price_usd=price_usd,
                    amount_nok=result["sale_value_nok"],
                    realized_pnl_nok=result["realized_pnl_nok"],
                    reason="ExecutionAdapter: paper SELL",
                    analysis_snapshot_id=request.analysis_snapshot_id,
                )
            except Exception:
                self.portfolio.restore_state(portfolio_state)
                raise

            return ExecutionResult(
                status=ExecutionStatus.SIMULATED,
                symbol=request.symbol,
                action=request.action,
                quantity=result["quantity"],
                message="paper SELL executed",
            )

        raise ValueError("unsupported execution action")
