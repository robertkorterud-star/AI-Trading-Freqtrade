from datetime import datetime, timedelta

from atlas.trading.historical_market_data import (
    HistoricalMarketData,
    OHLCVBar,
)
from atlas.trading.regime_strategy_backtest import (
    RegimeStrategyBacktestResearch,
    RegimeStrategyBacktestSummary,
    RegimeTradeResult,
)


def _data():
    closes = [
        100.0,
        100.0,
        100.0,
        100.0,
        100.0,
        95.0,
        96.0,
        97.0,
        98.0,
        99.0,
        100.0,
        101.0,
        102.0,
        103.0,
        104.0,
        100.0,
        99.0,
        98.0,
        97.0,
        96.0,
        95.0,
        96.0,
        97.0,
        98.0,
        99.0,
        100.0,
        101.0,
        102.0,
        103.0,
        104.0,
        105.0,
        106.0,
        107.0,
        108.0,
        109.0,
        110.0,
        111.0,
        112.0,
        113.0,
        114.0,
    ]

    bars = []

    for index, close in enumerate(closes):
        previous = (
            closes[index - 1]
            if index
            else close
        )

        bars.append(
            OHLCVBar(
                timestamp=(
                    datetime(2026, 1, 1)
                    + timedelta(hours=index)
                ),
                open=previous,
                high=max(previous, close) + 1.0,
                low=min(previous, close) - 1.0,
                close=close,
                volume=1000.0,
            )
        )

    return HistoricalMarketData(
        symbol="BTC-USD",
        bars=bars,
        timeframe="4h",
        source="test",
    )


def test_research_runs():
    result = (
        RegimeStrategyBacktestResearch()
        .run(_data())
    )

    assert isinstance(
        result,
        RegimeStrategyBacktestSummary,
    )


def test_result_contains_all_strategies():
    result = (
        RegimeStrategyBacktestResearch()
        .run(_data())
    )

    assert "Trend Following" in result.strategies
    assert "Momentum" in result.strategies
    assert "Mean Reversion" in result.strategies


def test_result_contains_mean_reversion_trades():
    result = (
        RegimeStrategyBacktestResearch()
        .run(_data())
    )

    mean_reversion_results = [
        item
        for item in result.results
        if item.strategy_name
        == "Mean Reversion"
    ]

    assert mean_reversion_results
    assert sum(
        item.trade_count
        for item in mean_reversion_results
    ) > 0


def test_winner_for_unknown_regime_is_none():
    summary = RegimeStrategyBacktestSummary(
        results=(
            RegimeTradeResult(
                strategy_name="Trend Following",
                regime="TRENDING_UP",
                trade_count=2,
                winning_trades=1,
                losing_trades=1,
                total_return_percent=2.0,
                average_trade_return_percent=1.0,
            ),
        )
    )

    assert (
        summary.winner_for_regime(
            "RANGING"
        )
        is None
    )


def test_winner_uses_total_return():
    summary = RegimeStrategyBacktestSummary(
        results=(
            RegimeTradeResult(
                strategy_name="Trend Following",
                regime="TRENDING_UP",
                trade_count=2,
                winning_trades=2,
                losing_trades=0,
                total_return_percent=3.0,
                average_trade_return_percent=1.5,
            ),
            RegimeTradeResult(
                strategy_name="Momentum",
                regime="TRENDING_UP",
                trade_count=2,
                winning_trades=1,
                losing_trades=1,
                total_return_percent=5.0,
                average_trade_return_percent=2.5,
            ),
        )
    )

    assert (
        summary.winner_for_regime(
            "TRENDING_UP"
        )
        == "Momentum"
    )


def test_research_is_deterministic():
    data = _data()

    research = (
        RegimeStrategyBacktestResearch()
    )

    first = research.run(data)
    second = research.run(data)

    assert first == second
