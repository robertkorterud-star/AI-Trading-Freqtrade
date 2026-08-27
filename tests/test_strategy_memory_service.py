from atlas.trading.regime_strategy_backtest import (
    RegimeStrategyBacktestSummary,
    RegimeTradeResult,
)
from atlas.trading.strategy_memory import StrategyMemory
from atlas.trading.strategy_memory_service import (
    StrategyMemoryService,
)


def _summary():
    return RegimeStrategyBacktestSummary(
        results=(
            RegimeTradeResult(
                strategy_name="Trend Following",
                regime="LOW_VOLATILITY",
                trade_count=4,
                winning_trades=3,
                losing_trades=1,
                total_return_percent=8.0,
                average_trade_return_percent=2.0,
            ),
            RegimeTradeResult(
                strategy_name="Momentum",
                regime="LOW_VOLATILITY",
                trade_count=6,
                winning_trades=4,
                losing_trades=2,
                total_return_percent=12.0,
                average_trade_return_percent=2.0,
            ),
            RegimeTradeResult(
                strategy_name="Mean Reversion",
                regime="RANGING",
                trade_count=3,
                winning_trades=2,
                losing_trades=1,
                total_return_percent=4.5,
                average_trade_return_percent=1.5,
            ),
        )
    )


def test_remember_stores_all_strategy_results():
    memory = StrategyMemory()
    service = StrategyMemoryService(memory)

    service.remember(
        symbol="BTC-USD",
        summary=_summary(),
    )

    records = memory.all()

    assert len(records) == 3

    assert {
        (
            record.symbol,
            record.regime,
            record.strategy_name,
        )
        for record in records
    } == {
        (
            "BTC-USD",
            "LOW_VOLATILITY",
            "Trend Following",
        ),
        (
            "BTC-USD",
            "LOW_VOLATILITY",
            "Momentum",
        ),
        (
            "BTC-USD",
            "RANGING",
            "Mean Reversion",
        ),
    }


def test_memory_record_contains_backtest_values():
    memory = StrategyMemory()
    service = StrategyMemoryService(memory)

    service.remember(
        symbol="BTC-USD",
        summary=_summary(),
    )

    record = memory.get(
        symbol="BTC-USD",
        regime="LOW_VOLATILITY",
        strategy_name="Momentum",
    )

    assert record is not None
    assert record.trade_count == 6
    assert record.winning_trades == 4
    assert record.losing_trades == 2
    assert record.average_trade_return_percent == 2.0
    assert record.total_return_percent == 12.0


def test_remember_is_idempotent_for_same_summary():
    memory = StrategyMemory()
    service = StrategyMemoryService(memory)

    summary = _summary()

    service.remember(
        symbol="BTC-USD",
        summary=summary,
    )

    service.remember(
        symbol="BTC-USD",
        summary=summary,
    )

    assert len(memory.all()) == 3


def test_empty_summary_stores_nothing():
    memory = StrategyMemory()
    service = StrategyMemoryService(memory)

    service.remember(
        symbol="BTC-USD",
        summary=RegimeStrategyBacktestSummary(
            results=()
        ),
    )

    assert memory.all() == ()


def test_empty_symbol_is_rejected():
    memory = StrategyMemory()
    service = StrategyMemoryService(memory)

    try:
        service.remember(
            symbol="",
            summary=_summary(),
        )
    except ValueError:
        pass
    else:
        raise AssertionError(
            "Expected ValueError"
        )


def test_robust_winner_is_stored_only_for_actual_winner():
    memory = StrategyMemory()

    class FakeRecommender:
        def recommend(self, summary, regime):
            if regime == "LOW_VOLATILITY":
                from atlas.trading.strategy_regime_recommendation import (
                    StrategyRegimeRecommendation,
                )

                return StrategyRegimeRecommendation(
                    regime=regime,
                    recommended_strategy="Momentum",
                    confidence=75.0,
                    evidence_strength="STRONG",
                    robust_winner=True,
                    trade_count=20,
                    win_rate_percent=75.0,
                    average_trade_return_percent=2.0,
                    total_return_percent=40.0,
                    reason="Momentum is robust.",
                )

            raise AssertionError(
                "Unexpected regime"
            )

    service = StrategyMemoryService(
        memory,
        recommender=FakeRecommender(),
    )

    summary = RegimeStrategyBacktestSummary(
        results=(
            RegimeTradeResult(
                strategy_name="Trend Following",
                regime="LOW_VOLATILITY",
                trade_count=20,
                winning_trades=10,
                losing_trades=10,
                total_return_percent=10.0,
                average_trade_return_percent=0.5,
            ),
            RegimeTradeResult(
                strategy_name="Momentum",
                regime="LOW_VOLATILITY",
                trade_count=20,
                winning_trades=15,
                losing_trades=5,
                total_return_percent=40.0,
                average_trade_return_percent=2.0,
            ),
        )
    )

    service.remember(
        symbol="BTC-USD",
        summary=summary,
    )

    trend = memory.get(
        symbol="BTC-USD",
        regime="LOW_VOLATILITY",
        strategy_name="Trend Following",
    )

    momentum = memory.get(
        symbol="BTC-USD",
        regime="LOW_VOLATILITY",
        strategy_name="Momentum",
    )

    assert trend is not None
    assert momentum is not None

    assert trend.robust_winner is False
    assert momentum.robust_winner is True
    assert momentum.evidence_strength == "STRONG"


def test_remember_persists_records_when_repository_is_supplied(
    tmp_path,
):
    from atlas.database.connection import Database
    from atlas.database.schema import initialize_database
    from atlas.database.strategy_memory_repository import (
        StrategyMemoryRepository,
    )

    database = Database(
        tmp_path / "strategy_memory.db"
    )

    initialize_database(database)

    memory = StrategyMemory()

    repository = StrategyMemoryRepository(
        database
    )

    service = StrategyMemoryService(
        memory=memory,
        repository=repository,
    )

    service.remember(
        symbol="BTC-USD",
        summary=_summary(),
    )

    assert len(memory.all()) == 3
    assert repository.count() == 3

    restored = repository.get(
        symbol="BTC-USD",
        regime="LOW_VOLATILITY",
        strategy_name="Momentum",
    )

    assert restored is not None
    assert restored.trade_count == 6
    assert restored.total_return_percent == 12.0


def test_remember_without_repository_still_works():
    memory = StrategyMemory()

    service = StrategyMemoryService(
        memory=memory,
    )

    service.remember(
        symbol="BTC-USD",
        summary=_summary(),
    )

    assert len(memory.all()) == 3


def test_remember_persists_one_history_record_per_research_run(
    tmp_path,
):
    from atlas.database.connection import Database
    from atlas.database.schema import initialize_database
    from atlas.database.strategy_memory_repository import (
        StrategyMemoryRepository,
    )

    database = Database(
        tmp_path / "strategy_memory.db"
    )

    initialize_database(database)

    memory = StrategyMemory()

    repository = StrategyMemoryRepository(
        database
    )

    service = StrategyMemoryService(
        memory=memory,
        repository=repository,
    )

    service.remember(
        symbol="BTC-USD",
        summary=_summary(),
        research_run_id="run-001",
    )

    assert repository.count() == 3
    assert repository.history_count() == 3

    history = repository.history(
        symbol="BTC-USD",
        regime="LOW_VOLATILITY",
        strategy_name="Momentum",
    )

    assert len(history) == 1
    assert history[0].total_return_percent == 12.0


def test_different_research_runs_create_separate_history(
    tmp_path,
):
    from atlas.database.connection import Database
    from atlas.database.schema import initialize_database
    from atlas.database.strategy_memory_repository import (
        StrategyMemoryRepository,
    )

    database = Database(
        tmp_path / "strategy_memory.db"
    )

    initialize_database(database)

    memory = StrategyMemory()

    repository = StrategyMemoryRepository(
        database
    )

    service = StrategyMemoryService(
        memory=memory,
        repository=repository,
    )

    service.remember(
        symbol="BTC-USD",
        summary=_summary(),
        research_run_id="run-001",
    )

    service.remember(
        symbol="BTC-USD",
        summary=_summary(),
        research_run_id="run-002",
    )

    assert repository.count() == 3
    assert repository.history_count() == 6

    history = repository.history(
        symbol="BTC-USD",
        regime="LOW_VOLATILITY",
        strategy_name="Momentum",
    )

    assert len(history) == 2
