from unittest.mock import patch

import pandas as pd

from atlas.adapters.market_data import YFinanceMarketDataProvider
from atlas.trading.market_data import MarketSnapshot


def test_yfinance_provider_builds_normalized_market_snapshot():
    history = pd.DataFrame(
        {
            "Open": [100.0, 101.0, 102.0],
            "High": [105.0, 106.0, 107.0],
            "Low": [99.0, 100.0, 101.0],
            "Close": [103.0, 104.0, 106.0],
            "Volume": [1000.0, 1100.0, 1200.0],
        },
        index=pd.to_datetime(
            [
                "2026-09-01",
                "2026-09-02",
                "2026-09-03",
            ]
        ),
    )

    with patch("atlas.adapters.market_data.yf.Ticker") as mock_ticker:
        mock_ticker.return_value.history.return_value = history

        result = YFinanceMarketDataProvider(
            history_period="3mo"
        ).snapshot(
            "NVDA",
            interval="1d",
            limit=100,
        )

    assert isinstance(result, MarketSnapshot)
    assert result.symbol == "NVDA"
    assert result.price == 106.0
    assert len(result.candles) == 3

    assert result.candles[-1].open == 102.0
    assert result.candles[-1].high == 107.0
    assert result.candles[-1].low == 101.0
    assert result.candles[-1].close == 106.0
    assert result.candles[-1].volume == 1200.0

    mock_ticker.return_value.history.assert_called_once_with(
        period="3mo",
        interval="1d",
    )


def test_yfinance_snapshot_applies_limit():
    history = pd.DataFrame(
        {
            "Open": [100.0, 101.0, 102.0, 103.0],
            "High": [105.0, 106.0, 107.0, 108.0],
            "Low": [99.0, 100.0, 101.0, 102.0],
            "Close": [103.0, 104.0, 106.0, 107.0],
            "Volume": [1000.0, 1100.0, 1200.0, 1300.0],
        },
        index=pd.date_range("2026-09-01", periods=4, freq="D"),
    )

    with patch("atlas.adapters.market_data.yf.Ticker") as mock_ticker:
        mock_ticker.return_value.history.return_value = history

        result = YFinanceMarketDataProvider().snapshot(
            "NVDA",
            limit=2,
        )

    assert len(result.candles) == 2
    assert result.candles[0].close == 106.0
    assert result.candles[1].close == 107.0


def test_yfinance_snapshot_drops_invalid_ohlcv_rows():
    history = pd.DataFrame(
        {
            "Open": [100.0, None, 102.0],
            "High": [105.0, 106.0, 107.0],
            "Low": [99.0, 100.0, 101.0],
            "Close": [103.0, 104.0, 106.0],
            "Volume": [1000.0, 1100.0, 1200.0],
        },
        index=pd.date_range("2026-09-01", periods=3, freq="D"),
    )

    with patch("atlas.adapters.market_data.yf.Ticker") as mock_ticker:
        mock_ticker.return_value.history.return_value = history

        result = YFinanceMarketDataProvider().snapshot("NVDA")

    assert len(result.candles) == 2
    assert result.candles[0].close == 103.0
    assert result.candles[1].close == 106.0


def test_yfinance_snapshot_uses_zero_for_missing_volume():
    history = pd.DataFrame(
        {
            "Open": [100.0],
            "High": [105.0],
            "Low": [99.0],
            "Close": [103.0],
            "Volume": [float("nan")],
        },
        index=pd.to_datetime(["2026-09-01"]),
    )

    with patch("atlas.adapters.market_data.yf.Ticker") as mock_ticker:
        mock_ticker.return_value.history.return_value = history

        result = YFinanceMarketDataProvider().snapshot("NVDA")

    assert result.candles[0].volume == 0.0


def test_yfinance_snapshot_rejects_empty_history():
    history = pd.DataFrame(
        columns=["Open", "High", "Low", "Close", "Volume"]
    )

    with patch("atlas.adapters.market_data.yf.Ticker") as mock_ticker:
        mock_ticker.return_value.history.return_value = history

        try:
            YFinanceMarketDataProvider().snapshot("NVDA")
        except ValueError as exc:
            assert "No market history available" in str(exc)
        else:
            raise AssertionError("Expected ValueError")
