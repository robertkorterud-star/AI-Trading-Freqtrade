"""
ATLAS Regime × Strategy Backtest Research.

Attributes actual strategy trade returns to the market regime
that was present when the trade was opened.

Research-only. No live trading decisions.
"""

from dataclasses import dataclass

from atlas.trading.historical_market_data import (
    HistoricalMarketData,
)
from atlas.trading.indicator_engine import (
    IndicatorEngine,
)
from atlas.trading.market_regime import (
    MarketRegimeAnalyzer,
)
from atlas.trading.trend_following_backtest import (
    TrendFollowingBacktester,
)
from atlas.trading.mean_reversion_backtest import (
    MeanReversionBacktester,
)
from atlas.trading.momentum_backtest import (
    MomentumBacktester,
)


@dataclass(frozen=True, slots=True)
class RegimeTradeResult:
    strategy_name: str
    regime: str
    trade_count: int
    winning_trades: int
    losing_trades: int
    total_return_percent: float
    average_trade_return_percent: float


@dataclass(frozen=True, slots=True)
class RegimeStrategyBacktestSummary:
    results: tuple[RegimeTradeResult, ...]

    @property
    def regimes(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    result.regime
                    for result in self.results
                }
            )
        )

    @property
    def strategies(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    result.strategy_name
                    for result in self.results
                }
            )
        )

    def winner_for_regime(
        self,
        regime: str,
    ) -> str | None:

        candidates = [
            result
            for result in self.results
            if result.regime == regime
            and result.trade_count > 0
        ]

        if not candidates:
            return None

        return max(
            candidates,
            key=lambda result: (
                result.total_return_percent,
                result.average_trade_return_percent,
                -result.losing_trades,
            ),
        ).strategy_name


class RegimeStrategyBacktestResearch:
    """
    Attribute actual strategy trades to entry regimes.

    Each strategy is evaluated with its existing backtester.
    Strategy-specific trade attribution is then mapped to the
    market regime present at the relevant trade entry.
    """

    def __init__(
        self,
        transaction_cost_percent: float = 0.1,
        slippage_percent: float = 0.05,
    ):
        self.transaction_cost_percent = (
            transaction_cost_percent
        )
        self.slippage_percent = (
            slippage_percent
        )

        self.indicator_engine = IndicatorEngine()
        self.regime_analyzer = MarketRegimeAnalyzer()

    def _regimes(
        self,
        data: HistoricalMarketData,
    ) -> list[str]:

        regimes = []

        candles = []

        for bar in data.bars:
            candles.append(
                {
                    "open": bar.open,
                    "high": bar.high,
                    "low": bar.low,
                    "close": bar.close,
                    "volume": bar.volume,
                }
            )

            indicators = (
                self.indicator_engine.calculate(
                    candles
                )
            )

            regime = self.regime_analyzer.analyze(
                indicators
            )

            regimes.append(regime.regime)

        return regimes

    def run(
        self,
        data: HistoricalMarketData,
        *,
        evaluation_start_index: int = 0,
    ) -> RegimeStrategyBacktestSummary:

        if (
            evaluation_start_index < 0
            or evaluation_start_index > len(data)
        ):
            raise ValueError(
                "evaluation_start_index must be between "
                "0 and len(data)."
            )

        regimes = self._regimes(data)

        results = []

        strategy_backtests = [
            (
                "Trend Following",
                TrendFollowingBacktester(
                    transaction_cost_percent=(
                        self.transaction_cost_percent
                    ),
                    slippage_percent=(
                        self.slippage_percent
                    ),
                ).run(data),
            ),
            (
                "Mean Reversion",
                MeanReversionBacktester().run(data),
            ),
            (
                "Momentum",
                MomentumBacktester().run(data),
            ),
        ]

        for strategy_name, backtest in strategy_backtests:

            grouped: dict[str, list[float]] = {}

            trades = getattr(
                backtest,
                "trades",
                (),
            )

            for trade in trades:

                entry_index = getattr(
                    trade,
                    "entry_index",
                    None,
                )

                if entry_index is None:
                    continue

                if (
                    entry_index < 0
                    or entry_index >= len(regimes)
                ):
                    continue

                if entry_index < evaluation_start_index:
                    continue

                regime = regimes[entry_index]

                grouped.setdefault(
                    regime,
                    [],
                ).append(
                    trade.return_percent
                )

            if not grouped:
                continue

            for regime, returns in sorted(
                grouped.items()
            ):

                winning = sum(
                    value > 0.0
                    for value in returns
                )

                losing = sum(
                    value <= 0.0
                    for value in returns
                )

                total = sum(returns)

                results.append(
                    RegimeTradeResult(
                        strategy_name=strategy_name,
                        regime=regime,
                        trade_count=len(returns),
                        winning_trades=winning,
                        losing_trades=losing,
                        total_return_percent=round(
                            total,
                            10,
                        ),
                        average_trade_return_percent=round(
                            total / len(returns),
                            10,
                        ),
                    )
                )

        return RegimeStrategyBacktestSummary(
            results=tuple(results)
        )


def format_regime_strategy_backtest(
    summary: RegimeStrategyBacktestSummary,
) -> str:

    lines = [
        "ATLAS REGIME × STRATEGY BACKTEST",
        "=================================",
        "",
    ]

    for regime in summary.regimes:

        lines.append(regime)
        lines.append("-" * len(regime))

        regime_results = [
            result
            for result in summary.results
            if result.regime == regime
        ]

        for result in regime_results:
            lines.append(
                f"{result.strategy_name:20}"
                f" {result.total_return_percent:8.3f}%"
                f" trades={result.trade_count:3}"
                f" wins={result.winning_trades:3}"
            )

        winner = summary.winner_for_regime(
            regime
        )

        lines.append(
            f"WINNER: {winner or 'None'}"
        )
        lines.append("")

    return "\n".join(lines)
