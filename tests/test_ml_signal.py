from datetime import datetime, timezone

from atlas.algorithms.base import AlgorithmSignal
from atlas.algorithms.fusion import SignalFusion
from atlas.decision.engine import DecisionEngine
from atlas.models.action import Action
from atlas.trading.ml_baseline import LogisticRegressionBaseline
from atlas.trading.ml_signal import MLPredictionSignal
from atlas.trading.prediction_inference import PredictionInferenceBuilder
from atlas.trading.prediction_training_dataset import PredictionTrainingExample
from atlas.trading.signal_evidence import SignalEvidence


def _example(trend: float) -> PredictionTrainingExample:
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
        _example(-1.0),
        PredictionTrainingExample(
            features={"trend": 1.0}, outcome=0.0, symbol="BTC-USD",
            action="BUY", timestamp=datetime(2026, 1, 2),
        ),
    ])
    return model


def test_ml_signal_produces_algorithm_signal():
    signal = MLPredictionSignal(_model()).predict(_example(-1.0))
    assert isinstance(signal, AlgorithmSignal)
    assert signal.symbol == "BTC-USD"
    assert signal.algorithm == "ml_baseline"
    assert signal.action in {Action.BUY, Action.SELL}
    assert 0.0 <= signal.confidence <= 1.0
    assert 0.0 <= signal.score <= 100.0
    assert signal.reasoning


def test_ml_signal_score_matches_canonical_fusion_scale():
    signal = MLPredictionSignal(_model()).predict(_example(-1.0))
    expected_score = 50.0 + (
        (signal.confidence if signal.action is Action.BUY else -signal.confidence)
        * 50.0
    )
    assert signal.score == expected_score


def test_ml_signal_can_enter_signal_fusion_without_scale_distortion():
    ml_signal = MLPredictionSignal(_model()).predict(_example(-1.0))
    companion = AlgorithmSignal(
        algorithm="companion", symbol="BTC-USD", timeframe="model",
        action=Action.BUY, score=80.0, confidence=0.8,
    )
    fused = SignalFusion().combine([ml_signal, companion])
    assert fused.action is Action.BUY
    assert 0.0 <= fused.score <= 100.0
    assert fused.score > 50.0


def test_ml_signal_is_deterministic_for_same_example():
    producer = MLPredictionSignal(_model())
    assert producer.predict(_example(-1.0)) == producer.predict(_example(-1.0))


def test_ml_signal_enters_canonical_decision_engine_boundary():
    signal = MLPredictionSignal(_model()).predict(_example(-1.0))
    decision = DecisionEngine().evaluate_algorithm_signals([signal])
    assert decision.symbol == "BTC-USD"
    assert decision.action is signal.action
    assert "algorithm:ml_baseline" in decision.analysts
    assert 0.0 <= decision.evidence <= 100.0
    assert 0.0 <= decision.confidence <= 100.0


def test_ml_signal_accepts_live_prediction_inference_example():
    evidence = SignalEvidence(
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
    inference = PredictionInferenceBuilder().build(
        evidence,
        symbol="BTC-USD",
        timestamp=datetime(2026, 9, 5, tzinfo=timezone.utc),
    )

    signal = MLPredictionSignal(_model()).predict(inference)

    assert signal.symbol == "BTC-USD"
    assert signal.action in {Action.BUY, Action.SELL}
    assert 0.0 <= signal.confidence <= 1.0
    assert 0.0 <= signal.score <= 100.0
