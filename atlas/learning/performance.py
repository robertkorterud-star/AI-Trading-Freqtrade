"""
ATLAS Learning & Performance Attribution

Records completed trades and measures how signals, agents,
market regimes and trading horizons perform over time.

The first version is intentionally descriptive rather than
self-modifying. ATLAS learns from measured outcomes without
automatically changing live trading parameters.
"""

from __future__ import annotations

from dataclasses import dataclass
from collections import defaultdict


@dataclass(frozen=True)
class TradeOutcome:
    """Completed trade outcome used by the learning engine."""

    trade_id: str
    symbol: str
    side: str
    entry_price: float
    exit_price: float
    quantity: float
    pnl: float
    return_pct: float
    holding_period: float
    agent: str | None = None
    regime: str | None = None
    horizon: str | None = None
    signal: str | None = None
    confidence: float = 0.0
    risk_score: float = 0.0

    @property
    def is_win(self) -> bool:
        return self.pnl > 0.0


@dataclass(frozen=True)
class PerformanceStats:
    """Aggregated performance statistics."""

    trades: int
    wins: int
    losses: int
    win_rate: float
    total_pnl: float
    average_pnl: float
    average_return_pct: float
    expectancy: float
    average_holding_period: float


class PerformanceAttribution:
    """
    Aggregates trade outcomes by agent, regime, horizon or signal.

    This gives ATLAS a measurable answer to questions such as:

    - Which agent performs best?
    - Which market regime produces the best results?
    - Which horizon is most reliable?
    - Which signals have positive expectancy?
    """

    def __init__(self) -> None:
        self._outcomes: list[TradeOutcome] = []

    def record(self, outcome: TradeOutcome) -> None:
        self._outcomes.append(outcome)

    @property
    def outcomes(self) -> tuple[TradeOutcome, ...]:
        return tuple(self._outcomes)

    def overall(self) -> PerformanceStats:
        return self._stats(self._outcomes)

    def by_agent(self) -> dict[str, PerformanceStats]:
        return self._group(lambda x: x.agent)

    def by_regime(self) -> dict[str, PerformanceStats]:
        return self._group(lambda x: x.regime)

    def by_horizon(self) -> dict[str, PerformanceStats]:
        return self._group(lambda x: x.horizon)

    def by_signal(self) -> dict[str, PerformanceStats]:
        return self._group(lambda x: x.signal)

    def best_agent(
        self,
        minimum_trades: int = 1,
    ) -> str | None:
        candidates = {
            key: stats
            for key, stats in self.by_agent().items()
            if stats.trades >= minimum_trades
        }

        if not candidates:
            return None

        return max(
            candidates,
            key=lambda key: candidates[key].expectancy,
        )

    def best_regime(
        self,
        minimum_trades: int = 1,
    ) -> str | None:
        candidates = {
            key: stats
            for key, stats in self.by_regime().items()
            if stats.trades >= minimum_trades
        }

        if not candidates:
            return None

        return max(
            candidates,
            key=lambda key: candidates[key].expectancy,
        )

    def _group(
        self,
        key_fn,
    ) -> dict[str, PerformanceStats]:
        groups: dict[str, list[TradeOutcome]] = defaultdict(list)

        for outcome in self._outcomes:
            key = key_fn(outcome)

            if key is None:
                continue

            groups[str(key)].append(outcome)

        return {
            key: self._stats(values)
            for key, values in groups.items()
        }

    @staticmethod
    def _stats(
        outcomes: list[TradeOutcome] | tuple[TradeOutcome, ...],
    ) -> PerformanceStats:
        trades = len(outcomes)

        if trades == 0:
            return PerformanceStats(
                trades=0,
                wins=0,
                losses=0,
                win_rate=0.0,
                total_pnl=0.0,
                average_pnl=0.0,
                average_return_pct=0.0,
                expectancy=0.0,
                average_holding_period=0.0,
            )

        wins = sum(1 for x in outcomes if x.is_win)
        losses = trades - wins

        total_pnl = sum(x.pnl for x in outcomes)
        average_pnl = total_pnl / trades

        average_return = (
            sum(x.return_pct for x in outcomes) / trades
        )

        average_holding = (
            sum(x.holding_period for x in outcomes) / trades
        )

        return PerformanceStats(
            trades=trades,
            wins=wins,
            losses=losses,
            win_rate=wins / trades,
            total_pnl=total_pnl,
            average_pnl=average_pnl,
            average_return_pct=average_return,
            expectancy=average_pnl,
            average_holding_period=average_holding,
        )


class LearningEngine:
    """
    High-level learning facade.

    It records outcomes and exposes attribution data while keeping
    strategy parameters immutable. Parameter adaptation can later
    be introduced as a separate, explicitly controlled component.
    """

    def __init__(self) -> None:
        self.performance = PerformanceAttribution()

    def record_trade(self, outcome: TradeOutcome) -> None:
        self.performance.record(outcome)

    def summary(self) -> PerformanceStats:
        return self.performance.overall()

    def agent_report(self) -> dict[str, PerformanceStats]:
        return self.performance.by_agent()

    def regime_report(self) -> dict[str, PerformanceStats]:
        return self.performance.by_regime()

    def horizon_report(self) -> dict[str, PerformanceStats]:
        return self.performance.by_horizon()

    def signal_report(self) -> dict[str, PerformanceStats]:
        return self.performance.by_signal()
