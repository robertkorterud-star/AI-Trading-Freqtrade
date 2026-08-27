"""
ATLAS Strategy Memory.

Research-only memory of historical strategy performance
within market regimes.

This module does not generate trading decisions.
"""

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True, slots=True)
class StrategyMemoryRecord:
    symbol: str
    regime: str
    strategy_name: str
    trade_count: int
    winning_trades: int
    losing_trades: int
    win_rate_percent: float
    average_trade_return_percent: float
    total_return_percent: float
    evidence_strength: str
    robust_winner: bool
    updated_at: datetime


class StrategyMemory:
    """
    In-memory research store for strategy/regime performance.

    Records are keyed by symbol, regime and strategy.
    """

    def __init__(self):
        self._records = {}

    def record(
        self,
        *,
        symbol: str,
        regime: str,
        strategy_name: str,
        trade_count: int,
        winning_trades: int,
        losing_trades: int,
        average_trade_return_percent: float,
        total_return_percent: float,
        evidence_strength: str,
        robust_winner: bool,
    ) -> StrategyMemoryRecord:

        if not symbol:
            raise ValueError(
                "symbol must not be empty."
            )

        if not regime:
            raise ValueError(
                "regime must not be empty."
            )

        if not strategy_name:
            raise ValueError(
                "strategy_name must not be empty."
            )

        if trade_count < 0:
            raise ValueError(
                "trade_count must not be negative."
            )

        if winning_trades < 0:
            raise ValueError(
                "winning_trades must not be negative."
            )

        if losing_trades < 0:
            raise ValueError(
                "losing_trades must not be negative."
            )

        if (
            winning_trades + losing_trades
            > trade_count
        ):
            raise ValueError(
                "winning_trades + losing_trades "
                "must not exceed trade_count."
            )

        win_rate = (
            winning_trades
            / trade_count
            * 100.0
            if trade_count
            else 0.0
        )

        record = StrategyMemoryRecord(
            symbol=symbol,
            regime=regime,
            strategy_name=strategy_name,
            trade_count=trade_count,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate_percent=round(
                win_rate,
                2,
            ),
            average_trade_return_percent=(
                float(
                    average_trade_return_percent
                )
            ),
            total_return_percent=float(
                total_return_percent
            ),
            evidence_strength=evidence_strength,
            robust_winner=bool(
                robust_winner
            ),
            updated_at=datetime.now(
                timezone.utc
            ),
        )

        self._records[
            (
                symbol,
                regime,
                strategy_name,
            )
        ] = record

        return record

    def get(
        self,
        *,
        symbol: str,
        regime: str,
        strategy_name: str,
    ) -> StrategyMemoryRecord | None:

        return self._records.get(
            (
                symbol,
                regime,
                strategy_name,
            )
        )

    def for_regime(
        self,
        *,
        symbol: str,
        regime: str,
    ) -> tuple[StrategyMemoryRecord, ...]:

        records = [
            record
            for record in self._records.values()
            if record.symbol == symbol
            and record.regime == regime
        ]

        return tuple(
            sorted(
                records,
                key=lambda record: (
                    record.strategy_name
                ),
            )
        )

    def all(
        self,
    ) -> tuple[StrategyMemoryRecord, ...]:

        return tuple(
            sorted(
                self._records.values(),
                key=lambda record: (
                    record.symbol,
                    record.regime,
                    record.strategy_name,
                ),
            )
        )

    def clear(self) -> None:
        self._records.clear()
