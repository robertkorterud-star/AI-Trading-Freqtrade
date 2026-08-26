from datetime import datetime, timedelta, timezone

from atlas.trading.coingecko_ohlc import (
    CoinGeckoOHLCProvider,
)
from atlas.trading.trend_following_backtest import (
    TrendFollowingBacktester,
)
from atlas.trading.walk_forward import (
    TrendFollowingWalkForward,
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

            # Først opptrend, deretter nedtrend.
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


def _market_data():

    provider = CoinGeckoOHLCProvider(
        client=FakeCoinGeckoOHLCClient(),
        coin_ids={
            "BTC-USD": "bitcoin",
        },
    )

    return provider.load(
        symbol="BTC-USD",
    )


def test_real_ohlc_shape_reaches_backtester():

    data = _market_data()

    result = TrendFollowingBacktester(
        fast_period=5,
        slow_period=15,
        transaction_cost_percent=0.1,
        slippage_percent=0.05,
    ).run(data)

    assert len(data) == 120
    assert result.final_capital > 0.0
    assert result.trade_count >= 0


def test_real_ohlc_reaches_walk_forward():

    data = _market_data()

    result = TrendFollowingWalkForward(
        fast_period=5,
        slow_period=15,
        transaction_cost_percent=0.1,
        slippage_percent=0.05,
    ).evaluate(
        data,
        train_size=50,
        test_size=20,
    )

    assert result.total_points == 120
    assert len(result.windows) > 0


def test_ohlc_values_are_preserved_before_research():

    data = _market_data()

    first = data.bars[0]

    assert first.open == 100.0
    assert first.high == 102.0
    assert first.low == 99.0
    assert first.close == 101.0
    assert first.high != first.close
    assert first.low != first.close
