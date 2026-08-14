from unittest.mock import patch

import pandas as pd

from atlas.adapters.historical_market_data import (
    HistoricalMarketDataAdapter,
)


def test_historical_market_data_returns_candles():

    data = pd.DataFrame(
        {
            "Open": [100.0, 101.0],
            "High": [102.0, 103.0],
            "Low": [99.0, 100.0],
            "Close": [101.0, 102.0],
            "Volume": [1000.0, 1200.0],
        },
        index=pd.to_datetime(
            [
                "2026-01-01",
                "2026-01-02",
            ]
        ),
    )

    fake_ticker = patch(
        "atlas.adapters.historical_market_data.yf.Ticker"
    )

    with fake_ticker as mock_ticker:

        mock_ticker.return_value.history.return_value = data

        candles = HistoricalMarketDataAdapter().get(
            "NVDA"
        )

    assert len(candles) == 2
    assert candles[0]["open"] == 100.0
    assert candles[0]["close"] == 101.0
    assert candles[1]["volume"] == 1200.0


def test_historical_market_data_handles_empty_history():

    data = pd.DataFrame(
        columns=[
            "Open",
            "High",
            "Low",
            "Close",
            "Volume",
        ]
    )

    with patch(
        "atlas.adapters.historical_market_data.yf.Ticker"
    ) as mock_ticker:

        mock_ticker.return_value.history.return_value = data

        candles = HistoricalMarketDataAdapter().get(
            "NVDA"
        )

    assert candles == []
