"""Tests that multi-timeframe evidence reaches ML features."""

from atlas.trading.prediction_features import PredictionFeatureBuilder
from atlas.trading.signal_evidence import SignalEvidence


def test_mtf_evidence_changes_ml_feature_vector():
    builder = PredictionFeatureBuilder()
    common = dict(
        trend="BULLISH",
        momentum="POSITIVE",
        volatility="NORMAL",
        volume="NORMAL",
        breakout="NONE",
        rsi_signal="BULLISH",
        macd_signal="BULLISH",
        bollinger_signal="MID_ZONE",
        adx_signal="STRONG_TREND",
        technical_quality="GOOD",
        evidence_quality="GOOD",
    )

    bullish = SignalEvidence(
        **common,
        multi_timeframe_signal="BUY",
        multi_timeframe_alignment=90.0,
    )
    bearish = SignalEvidence(
        **common,
        multi_timeframe_signal="SELL",
        multi_timeframe_alignment=10.0,
    )

    bullish_features = builder.build(bullish)
    bearish_features = builder.build(bearish)

    assert bullish_features.multi_timeframe_signal == 1.0
    assert bullish_features.multi_timeframe_alignment == 0.9
    assert bearish_features.multi_timeframe_signal == -1.0
    assert bearish_features.multi_timeframe_alignment == 0.1
    assert bullish_features.multi_timeframe_signal != bearish_features.multi_timeframe_signal
    assert bullish_features.multi_timeframe_alignment != bearish_features.multi_timeframe_alignment
