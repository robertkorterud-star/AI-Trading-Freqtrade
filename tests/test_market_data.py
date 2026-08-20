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
