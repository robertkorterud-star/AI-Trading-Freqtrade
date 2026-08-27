from datetime import datetime, timezone

import pytest

from atlas.trading.strategy_memory import (
    StrategyMemory,
    StrategyMemoryRecord,
)


def _record_kwargs():
    return {
        "symbol": "BTC-USD",
        "regime": "LOW_VOLATILITY",
        "strategy_name": "Momentum",
        "trade_count": 10,
        "winning_trades": 7,
        "losing_trades": 3,
        "average_trade_return_percent": 2.5,
        "total_return_percent": 25.0,
        "evidence_strength": "MODERATE",
        "robust_winner": True,
    }


def test_record_returns_strategy_memory_record():
    memory = StrategyMemory()

    record = memory.record(
        **_record_kwargs()
    )

    assert isinstance(
        record,
        StrategyMemoryRecord,
    )

    assert record.symbol == "BTC-USD"
    assert record.regime == "LOW_VOLATILITY"
    assert record.strategy_name == "Momentum"
    assert record.trade_count == 10
    assert record.winning_trades == 7
    assert record.losing_trades == 3
    assert record.win_rate_percent == 70.0
    assert record.average_trade_return_percent == 2.5
    assert record.total_return_percent == 25.0
    assert record.evidence_strength == "MODERATE"
    assert record.robust_winner is True


def test_record_sets_utc_timestamp():
    memory = StrategyMemory()

    record = memory.record(
        **_record_kwargs()
    )

    assert isinstance(
        record.updated_at,
        datetime,
    )

    assert (
        record.updated_at.tzinfo
        == timezone.utc
    )


def test_get_returns_record():
    memory = StrategyMemory()

    memory.record(
        **_record_kwargs()
    )

    record = memory.get(
        symbol="BTC-USD",
        regime="LOW_VOLATILITY",
        strategy_name="Momentum",
    )

    assert record is not None
    assert record.strategy_name == "Momentum"


def test_get_unknown_record_returns_none():
    memory = StrategyMemory()

    assert (
        memory.get(
            symbol="BTC-USD",
            regime="RANGING",
            strategy_name="Momentum",
        )
        is None
    )


def test_for_regime_returns_only_matching_records():
    memory = StrategyMemory()

    memory.record(
        **_record_kwargs()
    )

    memory.record(
        **{
            **_record_kwargs(),
            "strategy_name": "Trend Following",
        }
    )

    memory.record(
        **{
            **_record_kwargs(),
            "regime": "RANGING",
            "strategy_name": "Mean Reversion",
        }
    )

    records = memory.for_regime(
        symbol="BTC-USD",
        regime="LOW_VOLATILITY",
    )

    assert [
        record.strategy_name
        for record in records
    ] == [
        "Momentum",
        "Trend Following",
    ]


def test_for_regime_is_deterministically_sorted():
    memory = StrategyMemory()

    memory.record(
        **{
            **_record_kwargs(),
            "strategy_name": "Trend Following",
        }
    )

    memory.record(
        **_record_kwargs()
    )

    records = memory.for_regime(
        symbol="BTC-USD",
        regime="LOW_VOLATILITY",
    )

    assert [
        record.strategy_name
        for record in records
    ] == [
        "Momentum",
        "Trend Following",
    ]


def test_record_updates_existing_key():
    memory = StrategyMemory()

    memory.record(
        **_record_kwargs()
    )

    updated = memory.record(
        **{
            **_record_kwargs(),
            "trade_count": 20,
            "winning_trades": 14,
            "losing_trades": 6,
            "average_trade_return_percent": 3.0,
            "total_return_percent": 60.0,
        }
    )

    record = memory.get(
        symbol="BTC-USD",
        regime="LOW_VOLATILITY",
        strategy_name="Momentum",
    )

    assert record == updated
    assert record.trade_count == 20
    assert record.win_rate_percent == 70.0
    assert record.total_return_percent == 60.0


def test_invalid_trade_count_is_rejected():
    memory = StrategyMemory()

    with pytest.raises(ValueError):
        memory.record(
            **{
                **_record_kwargs(),
                "trade_count": -1,
            }
        )


def test_invalid_trade_result_counts_are_rejected():
    memory = StrategyMemory()

    with pytest.raises(ValueError):
        memory.record(
            **{
                **_record_kwargs(),
                "trade_count": 5,
                "winning_trades": 4,
                "losing_trades": 2,
            }
        )


def test_empty_symbol_is_rejected():
    memory = StrategyMemory()

    with pytest.raises(ValueError):
        memory.record(
            **{
                **_record_kwargs(),
                "symbol": "",
            }
        )


def test_empty_regime_is_rejected():
    memory = StrategyMemory()

    with pytest.raises(ValueError):
        memory.record(
            **{
                **_record_kwargs(),
                "regime": "",
            }
        )


def test_empty_strategy_name_is_rejected():
    memory = StrategyMemory()

    with pytest.raises(ValueError):
        memory.record(
            **{
                **_record_kwargs(),
                "strategy_name": "",
            }
        )


def test_all_returns_all_records_deterministically():
    memory = StrategyMemory()

    memory.record(
        **{
            **_record_kwargs(),
            "strategy_name": "Trend Following",
        }
    )

    memory.record(
        **{
            **_record_kwargs(),
            "regime": "RANGING",
            "strategy_name": "Mean Reversion",
        }
    )

    memory.record(
        **_record_kwargs()
    )

    records = memory.all()

    assert [
        (
            record.symbol,
            record.regime,
            record.strategy_name,
        )
        for record in records
    ] == [
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


def test_clear_removes_all_records():
    memory = StrategyMemory()

    memory.record(
        **_record_kwargs()
    )

    memory.clear()

    assert memory.all() == ()
