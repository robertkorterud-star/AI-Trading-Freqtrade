from unittest.mock import patch

from atlas.adapters.market_data import MarketData
from atlas.agents.technical_analyst import TechnicalAnalyst
from atlas.models.action import Action


def test_technical_analyst_explains_strong_volume_confirmation():

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
        "atlas.agents.technical_analyst.MarketDataAdapter"
    ) as mock_adapter:

        mock_adapter.return_value.get.return_value = market_data

        result = TechnicalAnalyst().analyze(
            "BTC-USD"
        )

    assert result.action == Action.BUY
    assert result.confidence == 88
    assert result.evidence == 85

    reasoning = " ".join(result.reasoning)

    assert "volume" in reasoning.lower()
    assert "2.00x" in reasoning


def test_technical_analyst_explains_low_volume_confirmation():

    market_data = MarketData(
        symbol="BTC-USD",
        price=100.0,
        previous_close=99.0,
        change_percent=1.01,
        ma20=98.0,
        ma50=95.0,
        volume=500_000.0,
        average_volume=1_000_000.0,
        volume_ratio=0.5,
    )

    with patch(
        "atlas.agents.technical_analyst.MarketDataAdapter"
    ) as mock_adapter:

        mock_adapter.return_value.get.return_value = market_data

        result = TechnicalAnalyst().analyze(
            "BTC-USD"
        )

    assert result.action == Action.BUY
    assert result.confidence == 88
    assert result.evidence == 85

    reasoning = " ".join(result.reasoning)

    assert "volume" in reasoning.lower()
    assert "0.50x" in reasoning
