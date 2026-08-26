from atlas.trading.prediction_features import (
    PredictionFeatureBuilder,
)
from atlas.trading.signal_evidence import (
    SignalEvidence,
)


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


def test_feature_builder_converts_bullish_evidence():

    result = PredictionFeatureBuilder().build(
        _evidence()
    )

    assert result.trend == 1.0
    assert result.momentum == 1.0

    assert result.volatility == 0.0
    assert result.volume == 1.0

    assert result.breakout == 1.0

    assert result.rsi_signal == 1.0
    assert result.macd_signal == 1.0
    assert result.bollinger_signal == 1.0
    assert result.adx_signal == 1.0

    assert result.multi_timeframe_signal == 1.0
    assert result.multi_timeframe_alignment == 0.92

    assert result.technical_quality == 1.0
    assert result.evidence_quality == 1.0


def test_feature_builder_converts_bearish_evidence():

    result = PredictionFeatureBuilder().build(
        _evidence(
            trend="BEARISH",
            momentum="NEGATIVE",
            volume="BELOW_AVERAGE",
            breakout="NONE",
            rsi_signal="BEARISH",
            macd_signal="BEARISH",
            bollinger_signal="LOWER_ZONE",
            multi_timeframe_signal="SELL",
            multi_timeframe_alignment=0.8,
        )
    )

    assert result.trend == -1.0
    assert result.momentum == -1.0
    assert result.volume == -1.0

    assert result.breakout == 0.0

    assert result.rsi_signal == -1.0
    assert result.macd_signal == -1.0
    assert result.bollinger_signal == -1.0

    assert result.multi_timeframe_signal == -1.0
    assert result.multi_timeframe_alignment == 0.8


def test_feature_builder_handles_unknown_values():

    result = PredictionFeatureBuilder().build(
        _evidence(
            trend="UNKNOWN",
            momentum="UNKNOWN",
            volatility="UNKNOWN",
            volume="UNKNOWN",
            breakout="UNKNOWN",
            rsi_signal="UNKNOWN",
            macd_signal="UNKNOWN",
            bollinger_signal="UNKNOWN",
            adx_signal="UNKNOWN",
            multi_timeframe_signal="UNKNOWN",
            multi_timeframe_alignment=0.0,
            technical_quality="MISSING",
            evidence_quality="MISSING",
        )
    )

    assert result.trend == 0.0
    assert result.momentum == 0.0
    assert result.volatility == 0.0
    assert result.volume == 0.0
    assert result.breakout == 0.0

    assert result.rsi_signal == 0.0
    assert result.macd_signal == 0.0
    assert result.bollinger_signal == 0.0
    assert result.adx_signal == 0.0

    assert result.multi_timeframe_signal == 0.0
    assert result.multi_timeframe_alignment == 0.0

    assert result.technical_quality == 0.0
    assert result.evidence_quality == 0.0


def test_feature_builder_does_not_make_trade_decision():

    result = PredictionFeatureBuilder().build(
        _evidence()
    )

    assert not hasattr(result, "decision")
    assert not hasattr(result, "action")
    assert not hasattr(result, "buy")
    assert not hasattr(result, "sell")
