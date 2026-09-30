from datetime import datetime, timezone

from atlas.trading.run_btc_regime_strategy_research import (
    build_research_run_id,
)


def test_same_actual_research_period_has_same_run_id():
    start = datetime(
        2026, 1, 1, 0, 0,
        tzinfo=timezone.utc,
    )
    end = datetime(
        2026, 1, 31, 0, 0,
        tzinfo=timezone.utc,
    )

    first = build_research_run_id(
        symbol="BTC-USD",
        start=start,
        end=end,
    )
    second = build_research_run_id(
        symbol="BTC-USD",
        start=start,
        end=end,
    )

    assert first == second


def test_different_actual_research_period_has_different_run_id():
    first = build_research_run_id(
        symbol="BTC-USD",
        start=datetime(
            2026, 1, 1,
            tzinfo=timezone.utc,
        ),
        end=datetime(
            2026, 1, 31,
            tzinfo=timezone.utc,
        ),
    )

    second = build_research_run_id(
        symbol="BTC-USD",
        start=datetime(
            2026, 2, 1,
            tzinfo=timezone.utc,
        ),
        end=datetime(
            2026, 2, 28,
            tzinfo=timezone.utc,
        ),
    )

    assert first != second
