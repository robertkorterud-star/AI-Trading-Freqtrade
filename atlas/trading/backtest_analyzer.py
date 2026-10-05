"""Read-only performance analysis for modern ATLAS backtest executions."""

from dataclasses import dataclass

from atlas.trading.trade_journal import TradeJournal
from atlas.trading.trading_cost_model import TradingCostModel


@dataclass(frozen=True, slots=True)
class BacktestAnalysis:
    """Aggregate execution economics from a dry-run trade journal."""

    execution_count: int
    completed_exit_count: int
    realized_exit_count: int
    completed_trade_count: int
    wins: int
    losses: int
    win_rate: float
    profit_factor: float
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

    def analyze(
        self,
        journal: TradeJournal,
        *,
        cost_multiplier: float = 1.0,
    ) -> BacktestAnalysis:
        if cost_multiplier <= 0.0:
            raise ValueError("cost_multiplier must be greater than zero")
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

        actual_fees = (
            sum(
                record.fee
                for record in executions
            )
            * cost_multiplier
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
            turnover
            * spread_slippage_rate
            * cost_multiplier
        )

        net_pnl = (
            gross_pnl
            - actual_fees
            - estimated_spread_slippage
        )

        realized_exit_count = len(completed_exits)

        # Reconstruct completed position lifecycles from executed quantities.
        # Action labels alone are insufficient because an EXIT may be
        # quantity-limited and therefore leave part of a position open.
        open_quantities: dict[str, float] = {}
        lifecycle_net_pnl: dict[str, float] = {}
        completed_trade_net_pnl: list[float] = []

        for record in executions:
            symbol = record.symbol
            open_quantity = open_quantities.get(symbol, 0.0)
            notional = record.quantity * record.price
            spread_slippage = (
                notional
                * spread_slippage_rate
                * cost_multiplier
            )

            if record.action == "enter":
                if open_quantity <= 1e-12:
                    lifecycle_net_pnl[symbol] = 0.0

                open_quantities[symbol] = (
                    open_quantity + record.quantity
                )
                lifecycle_net_pnl[symbol] = (
                    lifecycle_net_pnl.get(symbol, 0.0)
                    - record.fee * cost_multiplier
                    - spread_slippage
                )
                continue

            # PaperPortfolio realized_pnl already contains the exit-side fee,
            # so adding the fee back recovers gross market P&L before costs.
            lifecycle_net_pnl[symbol] = (
                lifecycle_net_pnl.get(symbol, 0.0)
                + record.realized_pnl
                + record.fee
                - record.fee * cost_multiplier
                - spread_slippage
            )

            remaining = max(
                0.0,
                open_quantity - record.quantity,
            )

            if open_quantity > 1e-12 and remaining <= 1e-12:
                completed_trade_net_pnl.append(
                    lifecycle_net_pnl.pop(symbol, 0.0)
                )

            open_quantities[symbol] = remaining

        completed_trade_count = len(completed_trade_net_pnl)

        wins = sum(
            pnl > 0.0
            for pnl in completed_trade_net_pnl
        )
        losses = sum(
            pnl < 0.0
            for pnl in completed_trade_net_pnl
        )
        win_rate = (
            wins / completed_trade_count
            if completed_trade_count
            else 0.0
        )

        gross_profit = sum(
            pnl
            for pnl in completed_trade_net_pnl
            if pnl > 0.0
        )
        gross_loss = -sum(
            pnl
            for pnl in completed_trade_net_pnl
            if pnl < 0.0
        )
        profit_factor = (
            gross_profit / gross_loss
            if gross_loss > 0.0
            else float("inf") if gross_profit > 0.0 else 0.0
        )

        # Backward-compatible alias for the original realized-exit metric.
        completed_exit_count = realized_exit_count

        net_expectancy = (
            sum(completed_trade_net_pnl) / completed_trade_count
            if completed_trade_count
            else 0.0
        )

        return BacktestAnalysis(
            execution_count=len(executions),
            completed_exit_count=completed_exit_count,
            realized_exit_count=realized_exit_count,
            completed_trade_count=completed_trade_count,
            wins=wins,
            losses=losses,
            win_rate=win_rate,
            profit_factor=profit_factor,
            turnover=turnover,
            gross_pnl=gross_pnl,
            actual_fees=actual_fees,
            estimated_spread_slippage=estimated_spread_slippage,
            net_pnl=net_pnl,
            net_expectancy=net_expectancy,
        )
