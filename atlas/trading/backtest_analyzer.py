"""Read-only performance analysis for modern ATLAS backtest executions."""

from dataclasses import dataclass

from atlas.trading.trade_journal import TradeJournal
from atlas.trading.trading_cost_model import TradingCostModel


@dataclass(frozen=True, slots=True)
class BacktestAnalysis:
    """Aggregate execution economics from a dry-run trade journal."""

    execution_count: int
    completed_exit_count: int
    turnover: float
    gross_pnl: float
    actual_fees: float
    estimated_spread_slippage: float
    net_pnl: float
    net_expectancy: float


class BacktestAnalyzer:
    """Analyze modern dry-run executions without affecting trading decisions."""

    def __init__(
        self,
        cost_model: TradingCostModel | None = None,
    ) -> None:
        self.cost_model = cost_model or TradingCostModel()

    def analyze(self, journal: TradeJournal) -> BacktestAnalysis:
        executions = [
            record
            for record in journal.records
            if record.quantity > 0.0
            and record.action in {"enter", "reduce", "exit"}
        ]

        completed_exits = [
            record
            for record in executions
            if record.action in {"reduce", "exit"}
        ]

        turnover = sum(
            record.quantity * record.price
            for record in executions
        )

        actual_fees = sum(
            record.fee
            for record in executions
        )

        # PaperPortfolio realized_pnl includes the exit-side fee.
        # Add it back to recover gross market P&L before direct costs.
        gross_pnl = sum(
            record.realized_pnl + record.fee
            for record in completed_exits
        )

        spread_slippage_rate = (
            self.cost_model.spread_bps / 20_000.0
            + self.cost_model.slippage_bps / 10_000.0
        )

        estimated_spread_slippage = (
            turnover * spread_slippage_rate
        )

        net_pnl = (
            gross_pnl
            - actual_fees
            - estimated_spread_slippage
        )

        completed_exit_count = len(completed_exits)
        net_expectancy = (
            net_pnl / completed_exit_count
            if completed_exit_count
            else 0.0
        )

        return BacktestAnalysis(
            execution_count=len(executions),
            completed_exit_count=completed_exit_count,
            turnover=turnover,
            gross_pnl=gross_pnl,
            actual_fees=actual_fees,
            estimated_spread_slippage=estimated_spread_slippage,
            net_pnl=net_pnl,
            net_expectancy=net_expectancy,
        )
