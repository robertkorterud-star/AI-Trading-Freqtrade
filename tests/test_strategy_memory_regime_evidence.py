from datetime import datetime, timezone

from atlas.trading.strategy_memory_history_record import (
    StrategyMemoryHistoryRecord,
)
from atlas.trading.strategy_memory_regime_evidence import (
    StrategyMemoryRegimeEvidence,
)


def _record(
    *,
    strategy_name: str,
    research_run_id: str,
    total_return: float,
    win_rate: float = 70.0,
    trade_count: int = 20,
    robust_winner: bool = True,
):
    return StrategyMemoryHistoryRecord(
        research_run_id=research_run_id,
        symbol="BTC-USD",
        regime="LOW_VOLATILITY",
        strategy_name=strategy_name,
        trade_count=trade_count,
        winning_trades=int(
            trade_count * win_rate / 100
        ),
        losing_trades=int(
            trade_count * (1 - win_rate / 100)
        ),
        win_rate_percent=win_rate,
        average_trade_return_percent=(
            total_return / trade_count
        ),
        total_return_percent=total_return,
        evidence_strength="STRONG",
        robust_winner=robust_winner,
        recorded_at=datetime.now(timezone.utc),
    )


def test_recommends_strategy_with_strong_longitudinal_evidence():
    records = (
        _record(
            strategy_name="Momentum",
            research_run_id="run-001",
            total_return=30.0,
        ),
        _record(
            strategy_name="Momentum",
            research_run_id="run-002",
            total_return=32.0,
        ),
        _record(
            strategy_name="Momentum",
            research_run_id="run-003",
            total_return=28.0,
        ),
        _record(
            strategy_name="Trend Following",
            research_run_id="run-001",
            total_return=15.0,
        ),
        _record(
            strategy_name="Trend Following",
            research_run_id="run-002",
            total_return=16.0,
        ),
        _record(
            strategy_name="Trend Following",
            research_run_id="run-003",
            total_return=14.0,
        ),
    )

    result = StrategyMemoryRegimeEvidence().evaluate(
        records,
        symbol="BTC-USD",
        regime="LOW_VOLATILITY",
    )

    assert result.recommended_strategy == "Momentum"
    assert result.robust_winner is True
    assert result.independent_run_count == 3
    assert result.confidence > 0.0


def test_duplicate_records_do_not_create_independent_evidence():
    records = (
        _record(
            strategy_name="Momentum",
            research_run_id="run-001",
            total_return=30.0,
        ),
        _record(
            strategy_name="Momentum",
            research_run_id="run-001",
            total_return=30.0,
        ),
        _record(
            strategy_name="Momentum",
            research_run_id="run-001",
            total_return=30.0,
        ),
    )

    result = StrategyMemoryRegimeEvidence().evaluate(
        records,
        symbol="BTC-USD",
        regime="LOW_VOLATILITY",
    )

    assert result.recommended_strategy is None
    assert result.robust_winner is False
    assert result.independent_run_count == 1


def test_no_robust_winner_when_strategies_are_too_close():
    records = (
        _record(
            strategy_name="Momentum",
            research_run_id="run-001",
            total_return=20.0,
        ),
        _record(
            strategy_name="Momentum",
            research_run_id="run-002",
            total_return=20.0,
        ),
        _record(
            strategy_name="Trend Following",
            research_run_id="run-001",
            total_return=19.5,
        ),
        _record(
            strategy_name="Trend Following",
            research_run_id="run-002",
            total_return=19.5,
        ),
    )

    result = StrategyMemoryRegimeEvidence().evaluate(
        records,
        symbol="BTC-USD",
        regime="LOW_VOLATILITY",
    )

    assert result.recommended_strategy is None
    assert result.robust_winner is False


def test_empty_history_returns_no_robust_winner():
    result = StrategyMemoryRegimeEvidence().evaluate(
        (),
        symbol="BTC-USD",
        regime="LOW_VOLATILITY",
    )

    assert result.recommended_strategy is None
    assert result.confidence == 0.0
    assert result.independent_run_count == 0
    assert result.robust_winner is False
