"""Tests that multi-timeframe evidence changes ML inference."""

from datetime import datetime, timezone

from atlas.models.action import Action
from atlas.trading.ml_baseline import LogisticRegressionBaseline
from atlas.trading.ml_signal import MLPredictionSignal
from atlas.trading.prediction_signal_service import PredictionSignalService
from atlas.trading.prediction_training_dataset import PredictionTrainingExample
from atlas.trading.signal_evidence import SignalEvidence


_COMMON = dict(
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


def _training_example(mtf_signal: float, mtf_alignment: float, outcome: float, day: int):
    return PredictionTrainingExample(
        features={
            "multi_timeframe_signal": mtf_signal,
            "multi_timeframe_alignment": mtf_alignment,
        },
        outcome=outcome,
        symbol="BTC-USD",
        action="BUY",
        timestamp=datetime(2026, 1, day),
    )


def _model() -> LogisticRegressionBaseline:
    model = LogisticRegressionBaseline(learning_rate=0.1, epochs=1000)
    model.fit([
        _training_example(1.0, 1.0, 1.0, 1),
        _training_example(-1.0, 0.0, 0.0, 2),
    ])
    return model


def _evidence(signal: str, alignment: float) -> SignalEvidence:
    return SignalEvidence(
        **_COMMON,
        multi_timeframe_signal=signal,
        multi_timeframe_alignment=alignment,
    )


def test_mtf_evidence_changes_actual_ml_probability_and_signal():
    model = _model()
    service = PredictionSignalService(signal=MLPredictionSignal(model))
    timestamp = datetime(2026, 9, 5, tzinfo=timezone.utc)

    bullish = service.predict(
        _evidence("BUY", 100.0),
        symbol="BTC-USD",
        timestamp=timestamp,
    )
    bearish = service.predict(
        _evidence("SELL", 0.0),
        symbol="BTC-USD",
        timestamp=timestamp,
    )

    bullish_probability = float(bullish.reasoning[0].split("=")[1])
    bearish_probability = float(bearish.reasoning[0].split("=")[1])

    assert bullish_probability > bearish_probability
    assert bullish.action == Action.BUY
    assert bearish.action == Action.SELL
    assert bullish.score > bearish.score
