from datetime import datetime, timezone

from atlas.trading.prediction_inference import (
    PredictionInferenceBuilder,
)
from atlas.trading.signal_evidence import SignalEvidence


def _evidence(**overrides):
    values = {
        "trend": "BULLISH",
        "momentum": "POSITIVE",
        "volatility": "NORMAL",
        "volume": "ABOVE_AVERAGE",
        "breakout": "BREAKOUT_50",
        "rsi_signal": "BULLISH",
        "macd_signal": "BULLISH",
        "bollinger_signal": "UPPER_ZONE",
        "adx_signal": "STRONG_TREND",
        "technical_quality": "GOOD",
        "multi_timeframe_signal": "BUY",
        "multi_timeframe_alignment": 0.92,
        "evidence_quality": "GOOD",
    }
    values.update(overrides)
    return SignalEvidence(**values)


def test_inference_builder_reuses_prediction_feature_builder():
    timestamp = datetime(2026, 9, 5, tzinfo=timezone.utc)

    result = PredictionInferenceBuilder().build(
        _evidence(),
        symbol="BTC-USD",
        timestamp=timestamp,
    )

    assert result.symbol == "BTC-USD"
    assert result.timestamp == timestamp
    assert result.features["trend"] == 1.0
    assert result.features["momentum"] == 1.0
    assert result.features["multi_timeframe_alignment"] == 0.92


def test_inference_example_has_no_training_outcome():
    result = PredictionInferenceBuilder().build(
        _evidence(),
        symbol="BTC-USD",
        timestamp=datetime(2026, 9, 5, tzinfo=timezone.utc),
    )

    assert not hasattr(result, "outcome")
    assert not hasattr(result, "correct")
    assert not hasattr(result, "evaluated")


def test_inference_feature_set_matches_prediction_feature_vector():
    result = PredictionInferenceBuilder().build(
        _evidence(),
        symbol="BTC-USD",
        timestamp=datetime(2026, 9, 5, tzinfo=timezone.utc),
    )

    assert set(result.features) == {
        "trend",
        "momentum",
        "volatility",
        "volume",
        "breakout",
        "rsi_signal",
        "macd_signal",
        "bollinger_signal",
        "adx_signal",
        "multi_timeframe_signal",
        "multi_timeframe_alignment",
        "technical_quality",
        "evidence_quality",
    }
