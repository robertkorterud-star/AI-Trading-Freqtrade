from datetime import datetime, timedelta, timezone

from atlas.trading.coingecko_ohlc import (
    CoinGeckoOHLCProvider,
)
from atlas.trading.historical_strategy_research import (
    HistoricalStrategyResearch,
)


class FakeCoinGeckoOHLCClient:

    def get_ohlc(
        self,
        coin_id,
        vs_currency,
        days,
    ):
        start = datetime(
            2026,
            1,
            1,
            tzinfo=timezone.utc,
        )

        rows = []
        price = 100.0

        for index in range(120):

            if index < 70:
                close = price + 1.0
            else:
                close = price - 0.8

            rows.append(
                [
                    (
                        start
                        + timedelta(days=index)
                    ).timestamp()
                    * 1000,
                    price,
                    max(price, close) + 1.0,
                    min(price, close) - 1.0,
                    close,
                ]
            )

            price = close

        return rows


def _data():

    provider = CoinGeckoOHLCProvider(
        client=FakeCoinGeckoOHLCClient(),
        coin_ids={
            "BTC-USD": "bitcoin",
        },
    )

    return provider.load(
        symbol="BTC-USD",
    )


def test_historical_strategy_research_runs_full_pipeline():

    result = HistoricalStrategyResearch(
        fast_period=5,
        slow_period=15,
        transaction_cost_percent=0.1,
        slippage_percent=0.05,
    ).run(
        _data(),
        train_size=50,
        test_size=20,
    )

    assert result.symbol == "BTC-USD"
    assert result.points == 120

    assert result.backtest is not None
    assert result.walk_forward is not None
    assert result.report is not None


def test_historical_strategy_research_preserves_data_size():

    data = _data()

    result = HistoricalStrategyResearch().run(
        data,
        train_size=50,
        test_size=20,
    )

    assert result.points == len(data)
    assert result.points == 120


def test_historical_strategy_research_is_deterministic():

    data = _data()

    research = HistoricalStrategyResearch(
        fast_period=5,
        slow_period=15,
        transaction_cost_percent=0.1,
        slippage_percent=0.05,
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


def test_historical_strategy_research_includes_data_quality():

    data = _data()

    result = HistoricalStrategyResearch().run(
        data,
        train_size=50,
        test_size=20,
    )

    assert result.quality is not None
    assert result.quality.valid is True
    assert result.quality.bar_count == len(data)


def test_historical_strategy_research_preserves_data_metadata():

    data = _data()

    result = HistoricalStrategyResearch().run(
        data,
        train_size=50,
        test_size=20,
    )

    assert data.symbol == "BTC-USD"
    assert data.timeframe == "4h"
    assert data.source == "coingecko"
