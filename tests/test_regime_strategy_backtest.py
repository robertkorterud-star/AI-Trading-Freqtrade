import pytest

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


def test_evaluation_start_excludes_warmup_trade_entries(monkeypatch):
    from datetime import datetime, timedelta, timezone

    from atlas.trading.historical_market_data import (
        HistoricalMarketData,
        OHLCVBar,
    )
    from atlas.trading.regime_strategy_backtest import (
        RegimeStrategyBacktestResearch,
    )
    from atlas.trading.trend_following_backtest import (
        TrendFollowingBacktestResult,
        TrendTrade,
    )

    start = datetime(
        2026, 1, 1,
        tzinfo=timezone.utc,
    )

    bars = [
        OHLCVBar(
            timestamp=start + timedelta(hours=index),
            open=100.0 + index,
            high=101.0 + index,
            low=99.0 + index,
            close=100.0 + index,
            volume=1.0,
        )
        for index in range(10)
    ]

    data = HistoricalMarketData(
        symbol="BTC-USD",
        timeframe="1h",
        source="test",
        bars=bars,
    )

    research = RegimeStrategyBacktestResearch()

    monkeypatch.setattr(
        research,
        "_regimes",
        lambda data: ["RANGING"] * len(data),
    )

    class FakeTrendBacktester:
        def __init__(self, *args, **kwargs):
            pass

        def run(self, data):
            return TrendFollowingBacktestResult(
                initial_capital=10000.0,
                final_capital=10300.0,
                strategy_return_percent=3.0,
                buy_and_hold_return_percent=0.0,
                max_drawdown_percent=0.0,
                trade_count=2,
                winning_trades=2,
                losing_trades=0,
                win_rate_percent=100.0,
                transaction_cost_percent=0.1,
                slippage_percent=0.05,
                trades=(
                    TrendTrade(
                        entry_index=2,
                        exit_index=3,
                        entry_price=102.0,
                        exit_price=103.0,
                        return_percent=1.0,
                    ),
                    TrendTrade(
                        entry_index=7,
                        exit_index=8,
                        entry_price=107.0,
                        exit_price=109.0,
                        return_percent=2.0,
                    ),
                ),
            )

    class EmptyBacktest:
        trades = ()

    class FakeEmptyBacktester:
        def __init__(self, *args, **kwargs):
            pass

        def run(self, data):
            return EmptyBacktest()

    monkeypatch.setattr(
        "atlas.trading.regime_strategy_backtest."
        "TrendFollowingBacktester",
        FakeTrendBacktester,
    )
    monkeypatch.setattr(
        "atlas.trading.regime_strategy_backtest."
        "MeanReversionBacktester",
        FakeEmptyBacktester,
    )
    monkeypatch.setattr(
        "atlas.trading.regime_strategy_backtest."
        "MomentumBacktester",
        FakeEmptyBacktester,
    )

    summary = research.run(
        data,
        evaluation_start_index=5,
    )

    assert len(summary.results) == 1

    result = summary.results[0]

    assert result.strategy_name == "Trend Following"
    assert result.regime == "RANGING"
    assert result.trade_count == 1
    assert result.winning_trades == 1
    assert result.losing_trades == 0
    assert result.total_return_percent == 2.0
    assert result.average_trade_return_percent == 2.0


def test_evaluation_start_rejects_invalid_boundaries():
    from datetime import datetime, timedelta, timezone

    from atlas.trading.historical_market_data import (
        HistoricalMarketData,
        OHLCVBar,
    )

    start = datetime(
        2026, 1, 1,
        tzinfo=timezone.utc,
    )

    bars = [
        OHLCVBar(
            timestamp=start + timedelta(hours=index),
            open=100.0,
            high=101.0,
            low=99.0,
            close=100.0,
            volume=1.0,
        )
        for index in range(3)
    ]

    data = HistoricalMarketData(
        symbol="BTC-USD",
        timeframe="1h",
        source="test",
        bars=bars,
    )

    research = RegimeStrategyBacktestResearch()

    with pytest.raises(
        ValueError,
        match="evaluation_start_index",
    ):
        research.run(
            data,
            evaluation_start_index=-1,
        )

    with pytest.raises(
        ValueError,
        match="evaluation_start_index",
    ):
        research.run(
            data,
            evaluation_start_index=4,
        )
