from datetime import datetime, timezone

from atlas.algorithms.base import AlgorithmSignal
from atlas.models.action import Action
from atlas.trading.ml_baseline import LogisticRegressionBaseline
from atlas.trading.ml_signal import MLPredictionSignal
from atlas.trading.prediction_signal_service import PredictionSignalService
from atlas.trading.prediction_training_dataset import PredictionTrainingExample
from atlas.trading.signal_evidence import SignalEvidence


def _training_example(trend: float) -> PredictionTrainingExample:
    return PredictionTrainingExample(
        features={"trend": trend},
        outcome=1.0,
        symbol="BTC-USD",
        action="BUY",
        timestamp=datetime(2026, 1, 1),
    )


def _model() -> LogisticRegressionBaseline:
    model = LogisticRegressionBaseline(learning_rate=0.1, epochs=1000)
    model.fit([
        _training_example(-1.0),
        PredictionTrainingExample(
            features={"trend": 1.0},
            outcome=0.0,
            symbol="BTC-USD",
            action="BUY",
            timestamp=datetime(2026, 1, 2),
        ),
    ])
    return model


def _evidence() -> SignalEvidence:
    return SignalEvidence(
        trend="BULLISH",
        momentum="POSITIVE",
        volatility="NORMAL",
        volume="ABOVE_AVERAGE",
        breakout="BREAKOUT_50",
        rsi_signal="BULLISH",
        macd_signal="BULLISH",
        bollinger_signal="UPPER_ZONE",
        adx_signal="STRONG_TREND",
        technical_quality="GOOD",
        multi_timeframe_signal="BUY",
        multi_timeframe_alignment=0.92,
        evidence_quality="GOOD",
    )


def test_prediction_signal_service_bridges_evidence_to_ml_signal():
    service = PredictionSignalService(
        signal=MLPredictionSignal(_model()),
    )

    result = service.predict(
        _evidence(),
        symbol="BTC-USD",
        timestamp=datetime(2026, 9, 5, tzinfo=timezone.utc),
    )

    assert isinstance(result, AlgorithmSignal)
    assert result.symbol == "BTC-USD"
    assert result.algorithm == "ml_baseline"
    assert result.action in {Action.BUY, Action.SELL}
    assert 0.0 <= result.confidence <= 1.0
    assert 0.0 <= result.score <= 100.0


def test_prediction_signal_service_does_not_change_signal_contract():
    service = PredictionSignalService(
        signal=MLPredictionSignal(_model()),
    )

    result = service.predict(
        _evidence(),
        symbol="BTC-USD",
        timestamp=datetime(2026, 9, 5, tzinfo=timezone.utc),
    )

    assert result.timeframe == "model"
    assert result.reasoning
