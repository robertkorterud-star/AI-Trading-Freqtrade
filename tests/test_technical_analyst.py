from unittest.mock import patch

from atlas.adapters.market_data import MarketData
from atlas.agents.technical_analyst import TechnicalAnalyst
from atlas.intelligence.technical_signal import TechnicalSignal
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


def test_technical_analyst_classifies_normal_volume():

    market_data = MarketData(
        symbol="BTC-USD",
        price=100.0,
        previous_close=99.0,
        change_percent=1.01,
        ma20=98.0,
        ma50=95.0,
        volume=1_000_000.0,
        average_volume=1_000_000.0,
        volume_ratio=1.0,
    )

    with patch(
        "atlas.agents.technical_analyst.MarketDataAdapter"
    ) as mock_adapter:

        mock_adapter.return_value.get.return_value = market_data

        result = TechnicalAnalyst().analyze("BTC-USD")

    reasoning = " ".join(result.reasoning)

    assert "NORMAL" in reasoning
    assert "1.00x" in reasoning


def test_technical_analyst_classifies_extreme_volume():

    market_data = MarketData(
        symbol="BTC-USD",
        price=100.0,
        previous_close=99.0,
        change_percent=1.01,
        ma20=98.0,
        ma50=95.0,
        volume=3_500_000.0,
        average_volume=1_000_000.0,
        volume_ratio=3.5,
    )

    with patch(
        "atlas.agents.technical_analyst.MarketDataAdapter"
    ) as mock_adapter:

        mock_adapter.return_value.get.return_value = market_data

        result = TechnicalAnalyst().analyze("BTC-USD")

    reasoning = " ".join(result.reasoning)

    assert "EXTREME" in reasoning
    assert "3.50x" in reasoning


def test_technical_analyst_classifies_low_volume():

    market_data = MarketData(
        symbol="BTC-USD",
        price=100.0,
        previous_close=99.0,
        change_percent=1.01,
        ma20=98.0,
        ma50=95.0,
        volume=700_000.0,
        average_volume=1_000_000.0,
        volume_ratio=0.7,
    )

    with patch(
        "atlas.agents.technical_analyst.MarketDataAdapter"
    ) as mock_adapter:

        mock_adapter.return_value.get.return_value = market_data

        result = TechnicalAnalyst().analyze("BTC-USD")

    reasoning = " ".join(result.reasoning)

    assert "LOW" in reasoning
    assert "0.70x" in reasoning


def test_technical_analyst_delegates_direction_to_signal_engine():

    market_data = MarketData(
        symbol="BTC-USD",
        price=100.0,
        previous_close=99.0,
        change_percent=1.01,
        ma20=98.0,
        ma50=95.0,
        volume=1_000_000.0,
        average_volume=1_000_000.0,
        volume_ratio=1.0,
    )

    forced_signal = TechnicalSignal(
        symbol="BTC-USD",
        action=Action.SELL,
        confidence=91,
        reasons=("test_engine_direction",),
    )

    with (
        patch("atlas.agents.technical_analyst.MarketDataAdapter") as mock_adapter,
        patch(
            "atlas.agents.technical_analyst.generate_technical_signal",
            return_value=forced_signal,
        ) as mock_signal_engine,
    ):
        mock_adapter.return_value.get.return_value = market_data

        result = TechnicalAnalyst().analyze("BTC-USD")

    mock_signal_engine.assert_called_once_with(market_data)
    assert result.action == Action.SELL
    assert result.confidence == 88
    assert "test_engine_direction" in result.reasoning
    assert "Technical signal engine confidence: 91/100." in result.reasoning
