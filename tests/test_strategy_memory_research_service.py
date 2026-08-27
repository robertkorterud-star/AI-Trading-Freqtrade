from datetime import datetime, timedelta, timezone

from atlas.trading.strategy_memory import StrategyMemoryRecord
from atlas.trading.strategy_memory_history_analyzer import (
    StrategyMemoryHistoryAnalysis,
)
from atlas.trading.strategy_memory_history_service import (
    StrategyMemoryHistoryService,
)

from atlas.trading.strategy_memory_research_service import (
    StrategyMemoryResearchService,
)


def _record(
    *,
    symbol="BTC-USD",
    regime="LOW_VOLATILITY",
    strategy="Momentum",
    total_return=20.0,
    days_ago=0,
    robust_winner=True,
):
    return StrategyMemoryRecord(
        symbol=symbol,
        regime=regime,
        strategy_name=strategy,
        trade_count=20,
        winning_trades=15,
        losing_trades=5,
        win_rate_percent=75.0,
        average_trade_return_percent=2.0,
        total_return_percent=total_return,
        evidence_strength="STRONG",
        robust_winner=robust_winner,
        updated_at=(
            datetime.now(timezone.utc)
            - timedelta(days=days_ago)
        ),
    )


class FakeRepository:
    def __init__(self, records):
        self.records = tuple(records)

    def get_all(self):
        return self.records


class FakeAnalyzer:
    def __init__(self):
        self.calls = []

    def analyze(self, history):
        self.calls.append(tuple(history))

        return StrategyMemoryHistoryAnalysis(
            observation_count=len(history),
            average_return_percent=10.0,
            best_return_percent=20.0,
            worst_return_percent=5.0,
            average_win_rate_percent=75.0,
            average_trade_count=20.0,
            positive_periods=len(history),
            positive_period_ratio=1.0,
            robust_winner_periods=len(history),
            consistency_score=90.0,
            classification="CONSISTENT",
        )


def test_analyze_all_groups_history_by_symbol_regime_strategy():

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

    service = StrategyMemoryResearchService(
        repository
    )

    results = service.analyze_all()

    assert len(results) == 3

    keys = {
        (
            result.symbol,
            result.regime,
            result.strategy_name,
        )
        for result in results
    }

    assert keys == {
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
    }


def test_analyze_all_passes_each_history_group_to_analyzer():

    records = (
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
    )

    repository = FakeRepository(records)
    analyzer = FakeAnalyzer()

    service = StrategyMemoryResearchService(
        repository,
        analyzer=analyzer,
    )

    results = service.analyze_all()

    assert len(results) == 1
    assert len(analyzer.calls) == 1
    assert len(analyzer.calls[0]) == 2
    assert results[0].classification == "CONSISTENT"


def test_empty_repository_returns_empty_results():

    service = StrategyMemoryResearchService(
        FakeRepository(())
    )

    assert service.analyze_all() == ()
