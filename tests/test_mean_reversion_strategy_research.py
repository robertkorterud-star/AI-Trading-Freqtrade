from datetime import datetime, timedelta, timezone

from atlas.trading.historical_market_data import (
    HistoricalMarketData,
    OHLCVBar,
)
from atlas.trading.mean_reversion_strategy_research import (
    MeanReversionStrategyResearch,
)


def _data():

    start = datetime(
        2026,
        1,
        1,
        tzinfo=timezone.utc,
    )

    bars = []

    price = 100.0

    for index in range(120):

        if index % 20 == 10:
            close = price * 0.95
        else:
            close = price * 1.005

        bars.append(
            OHLCVBar(
                timestamp=(
                    start
                    + timedelta(hours=index)
                ),
                open=price,
                high=max(
                    price,
                    close,
                ) + 1.0,
                low=min(
                    price,
                    close,
                ) - 1.0,
                close=close,
                volume=1000.0,
            )
        )

        price = close

    return HistoricalMarketData(
        symbol="BTC-USD",
        timeframe="4h",
        source="test",
        bars=bars,
    )


def test_mean_reversion_research_runs_full_pipeline():

    result = MeanReversionStrategyResearch(
        lookback_period=5,
        entry_deviation_percent=2.0,
    ).run(
        _data(),
        train_size=50,
        test_size=20,
    )

    assert result.symbol == "BTC-USD"
    assert result.points == 120
    assert result.backtest is not None
    assert result.walk_forward is not None
    assert result.verdict in {
        "EDGE",
        "NO_EDGE",
        "INCONCLUSIVE",
    }


def test_mean_reversion_research_calculates_advantage():

    result = MeanReversionStrategyResearch(
        lookback_period=5,
        entry_deviation_percent=2.0,
    ).run(
        _data(),
        train_size=50,
        test_size=20,
    )

    assert (
        result.advantage_percent
        == (
            result.strategy_return_percent
            - result.buy_and_hold_return_percent
        )
    )


def test_mean_reversion_research_preserves_data_size():

    data = _data()

    result = MeanReversionStrategyResearch().run(
        data,
        train_size=50,
        test_size=20,
    )

    assert result.points == len(data)
    assert result.points == 120


def test_mean_reversion_research_is_deterministic():

    data = _data()

    research = MeanReversionStrategyResearch(
        lookback_period=5,
        entry_deviation_percent=2.0,
    )

    first = research.run(
        data,
        train_size=50,
        test_size=20,
    )

    second = research.run(
        data,
        train_size=50,
        test_size=20,
    )

    assert first == second
