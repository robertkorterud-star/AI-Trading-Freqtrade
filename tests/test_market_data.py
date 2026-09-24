from unittest.mock import patch

import pandas as pd

from atlas.adapters.market_data import MarketDataAdapter


def test_market_data_includes_volume_metrics():

    closes = [
        float(value)
        for value in range(51, 101)
    ]

    volumes = [
        1_000_000.0
        for _ in range(49)
    ] + [
        2_000_000.0
    ]

    history = pd.DataFrame(
        {
            "Close": closes,
            "Volume": volumes,
        }
    )

    with patch(
        "atlas.adapters.market_data.yf.Ticker"
    ) as mock_ticker:

        ticker = mock_ticker.return_value

        ticker.history.return_value = history

        ticker.fast_info = {
            "lastPrice": 100.0,
            "previousClose": 99.0,
        }

        result = MarketDataAdapter().get(
            "NVDA"
        )

    assert result.symbol == "NVDA"
    assert result.price == 100.0
    assert result.previous_close == 99.0

    assert result.volume == 2_000_000.0

    assert result.average_volume == 1_050_000.0

    assert round(
        result.volume_ratio,
        4,
    ) == round(
        2_000_000.0 / 1_050_000.0,
        4,
    )


def test_market_data_requires_sufficient_closes():

    history = pd.DataFrame(
        {
            "Close": [100.0] * 49,
            "Volume": [1_000_000.0] * 49,
        }
    )

    with patch(
        "atlas.adapters.market_data.yf.Ticker"
    ) as mock_ticker:

        mock_ticker.return_value.history.return_value = history

        try:
            MarketDataAdapter().get("NVDA")
        except ValueError as error:
            assert "Insufficient market history" in str(error)
        else:
            raise AssertionError(
                "Expected insufficient history error."
            )


def test_market_snapshot_fetches_requested_timeframes():
    from atlas.adapters.market_data import YFinanceMarketDataProvider

    index = pd.to_datetime(
        [
            "2026-09-22T14:00:00Z",
            "2026-09-22T15:00:00Z",
        ]
    )
    daily = pd.DataFrame(
        {
            "Open": [100.0, 101.0],
            "High": [102.0, 103.0],
            "Low": [99.0, 100.0],
            "Close": [101.0, 102.0],
            "Volume": [1_000.0, 1_100.0],
        },
        index=index,
    )
    hourly = pd.DataFrame(
        {
            "Open": [102.0, 103.0],
            "High": [104.0, 105.0],
            "Low": [101.0, 102.0],
            "Close": [103.0, 104.0],
            "Volume": [1_200.0, 1_300.0],
        },
        index=index,
    )
    fifteen_minute = pd.DataFrame(
        {
            "Open": [104.0, 105.0],
            "High": [106.0, 107.0],
            "Low": [103.0, 104.0],
            "Close": [105.0, 106.0],
            "Volume": [1_400.0, 1_500.0],
        },
        index=index,
    )

    with patch(
        "atlas.adapters.market_data.yf.Ticker"
    ) as mock_ticker:
        ticker = mock_ticker.return_value
        ticker.history.side_effect = (
            lambda *, period, interval: {
                "1d": daily,
                "1h": hourly,
                "15m": fifteen_minute,
            }[interval]
        )

        snapshot = YFinanceMarketDataProvider().snapshot(
            "NVDA",
            interval="1d",
            timeframes=("1h", "15m"),
        )

    assert snapshot.price == 102.0
    assert tuple(snapshot.timeframe_candles) == ("1h", "15m")
    assert snapshot.timeframe_candles["1h"][-1].close == 104.0
    assert snapshot.timeframe_candles["15m"][-1].close == 106.0
    assert [
        call.kwargs["interval"]
        for call in ticker.history.call_args_list
    ] == ["1d", "1h", "15m"]
