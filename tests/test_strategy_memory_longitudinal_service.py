from datetime import datetime, timedelta, timezone

from atlas.trading.strategy_memory import StrategyMemoryRecord
from atlas.trading.strategy_memory_longitudinal_analyzer import (
    StrategyMemoryLongitudinalAnalysis,
)
from atlas.trading.strategy_memory_longitudinal_service import (
    StrategyMemoryLongitudinalService,
)


def _record(
    *,
    strategy="Momentum",
    regime="LOW_VOLATILITY",
    total_return=20.0,
    days_ago=10,
):
    return StrategyMemoryRecord(
        symbol="BTC-USD",
        regime=regime,
        strategy_name=strategy,
        trade_count=20,
        winning_trades=15,
        losing_trades=5,
        win_rate_percent=75.0,
        average_trade_return_percent=2.0,
        total_return_percent=total_return,
        evidence_strength="STRONG",
        robust_winner=True,
        updated_at=(
            datetime.now(timezone.utc)
            - timedelta(days=days_ago)
        ),
    )


class FakeRepository:
    def __init__(self, records):
        self.records = tuple(records)
        self.calls = []

    def history(
        self,
        *,
        symbol,
        regime,
        strategy_name,
    ):
        self.calls.append(
            (
                symbol,
                regime,
                strategy_name,
            )
        )

        return tuple(
            record
            for record in self.records
            if (
                record.symbol == symbol
                and record.regime == regime
                and record.strategy_name
                == strategy_name
            )
        )

    def history_groups(self):
        groups = {
            (
                record.symbol,
                record.regime,
                record.strategy_name,
            )
            for record in self.records
        }

        return tuple(sorted(groups))


class FakeAnalyzer:
    def __init__(self):
        self.calls = []

    def analyze(self, history):
        self.calls.append(tuple(history))

        return StrategyMemoryLongitudinalAnalysis(
            observation_count=len(history),
            average_return_percent=20.0,
            best_return_percent=25.0,
            worst_return_percent=15.0,
            average_win_rate_percent=75.0,
            average_trade_count=20.0,
            positive_periods=len(history),
            positive_period_ratio=1.0
            if history
            else 0.0,
            robust_winner_periods=len(history),
            consistency_score=90.0,
            confidence=80.0,
            classification="CONSISTENT"
            if len(history) >= 2
            else "INSUFFICIENT_DATA",
        )


def test_analyze_returns_longitudinal_analysis():
    repository = FakeRepository(
        (
            _record(total_return=15.0, days_ago=30),
            _record(total_return=25.0, days_ago=20),
            _record(total_return=20.0, days_ago=10),
        )
    )

    analyzer = FakeAnalyzer()

    service = StrategyMemoryLongitudinalService(
        repository,
        analyzer=analyzer,
    )

    result = service.analyze(
        symbol="BTC-USD",
        regime="LOW_VOLATILITY",
        strategy_name="Momentum",
    )

    assert result.classification == "CONSISTENT"
    assert result.observation_count == 3

    assert analyzer.calls == [
        repository.history(
            symbol="BTC-USD",
            regime="LOW_VOLATILITY",
            strategy_name="Momentum",
        )
    ]


def test_analyze_all_analyzes_every_history_group():
    repository = FakeRepository(
        (
            _record(
                strategy="Momentum",
                total_return=10.0,
                days_ago=30,
            ),
            _record(
                strategy="Momentum",
                total_return=20.0,
                days_ago=20,
            ),
            _record(
                strategy="Trend Following",
                total_return=15.0,
                days_ago=10,
            ),
            _record(
                regime="RANGING",
                strategy="Mean Reversion",
                total_return=8.0,
            ),
        )
    )

    analyzer = FakeAnalyzer()

    service = StrategyMemoryLongitudinalService(
        repository,
        analyzer=analyzer,
    )

    results = service.analyze_all()

    assert len(results) == 3

    assert [result.classification for result in results] == [
        "CONSISTENT",
        "INSUFFICIENT_DATA",
        "INSUFFICIENT_DATA",
    ]

    assert len(analyzer.calls) == 3

    assert repository.calls == [
        (
            "BTC-USD",
            "LOW_VOLATILITY",
            "Momentum",
        ),
        (
            "BTC-USD",
            "LOW_VOLATILITY",
            "Trend Following",
        ),
        (
            "BTC-USD",
            "RANGING",
            "Mean Reversion",
        ),
    ]


def test_analyze_all_returns_empty_for_empty_repository():
    repository = FakeRepository(())
    analyzer = FakeAnalyzer()

    service = StrategyMemoryLongitudinalService(
        repository,
        analyzer=analyzer,
    )

    assert service.analyze_all() == ()
    assert analyzer.calls == []


def test_analyze_uses_injected_analyzer():
    repository = FakeRepository(
        (
            _record(total_return=10.0, days_ago=20),
            _record(total_return=30.0, days_ago=10),
        )
    )

    analyzer = FakeAnalyzer()

    service = StrategyMemoryLongitudinalService(
        repository,
        analyzer=analyzer,
    )

    service.analyze(
        symbol="BTC-USD",
        regime="LOW_VOLATILITY",
        strategy_name="Momentum",
    )

    assert len(analyzer.calls) == 1
    assert len(analyzer.calls[0]) == 2
