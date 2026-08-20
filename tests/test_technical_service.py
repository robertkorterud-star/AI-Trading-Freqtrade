from unittest.mock import patch

from atlas.adapters.market_data import MarketData
from atlas.services.technical_service import TechnicalService


def test_technical_snapshot_includes_volume_metrics():

    market_data = MarketData(
        symbol="BTC-USD",
        price=100.0,
        previous_close=99.0,
        change_percent=1.01,
        ma20=98.0,
        ma50=95.0,
        volume=2_000_000.0,
        average_volume=1_050_000.0,
        volume_ratio=2_000_000.0 / 1_050_000.0,
    )

    with patch(
        "atlas.services.technical_service.MarketDataAdapter"
    ) as mock_adapter:

        mock_adapter.return_value.get.return_value = market_data

        snapshot = TechnicalService().get_snapshot(
            "BTC-USD"
        )

    assert snapshot.symbol == "BTC-USD"
    assert snapshot.volume == 2_000_000.0
    assert snapshot.average_volume == 1_050_000.0

    assert round(
        snapshot.volume_ratio,
        4,
    ) == round(
        2_000_000.0 / 1_050_000.0,
        4,
    )


def test_technical_snapshot_preserves_trend():

    market_data = MarketData(
        symbol="BTC-USD",
        price=100.0,
        previous_close=99.0,
        change_percent=1.01,
        ma20=98.0,
        ma50=95.0,
        volume=2_000_000.0,
        average_volume=1_000_000.0,
        volume_ratio=2.0,
    )

    with patch(
        "atlas.services.technical_service.MarketDataAdapter"
    ) as mock_adapter:

        mock_adapter.return_value.get.return_value = market_data

        snapshot = TechnicalService().get_snapshot(
            "BTC-USD"
        )

    assert snapshot.trend == "Bullish"
