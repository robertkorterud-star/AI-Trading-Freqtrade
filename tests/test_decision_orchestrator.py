from atlas.algorithms import (
    AlgorithmSignal,
    DecisionAction,
    DecisionOrchestrator,
    HorizonSignal,
    RiskContext,
    TradingHorizon,
)
from atlas.models.action import Action


def signal(symbol="BTC-USD", action=Action.BUY, confidence=0.90):
    return AlgorithmSignal(
        algorithm="test",
        symbol=symbol,
        timeframe="5m",
        action=action,
        score=90.0 if action is Action.BUY else 10.0,
        confidence=confidence,
    )


def test_orchestrator_produces_buy_from_strong_signal():
    result = DecisionOrchestrator().decide(
        "BTC-USD",
        [signal()],
    )

    assert result.decision.action is DecisionAction.BUY
    assert result.symbol == "BTC-USD"


def test_orchestrator_normalizes_multi_horizon_confidence():
    horizons = [
        HorizonSignal(TradingHorizon.INTRADAY, Action.BUY, 90.0, 90.0),
        HorizonSignal(TradingHorizon.SWING, Action.BUY, 85.0, 80.0),
        HorizonSignal(TradingHorizon.POSITION, Action.BUY, 80.0, 75.0),
    ]

    result = DecisionOrchestrator().decide(
        "BTC-USD",
        [],
        horizons=horizons,
    )

    assert result.horizon_result is not None
    assert result.decision.action is DecisionAction.BUY
    assert 0.0 <= result.decision.confidence <= 1.0


def test_risk_gate_blocks_high_risk_decision():
    result = DecisionOrchestrator().decide(
        "BTC-USD",
        [signal()],
        risk=RiskContext(
            risk_score=1.0,
            volatility_score=1.0,
            drawdown_score=1.0,
            position_score=1.0,
        ),
    )

    assert result.decision.action is DecisionAction.HOLD
    assert result.decision.reason == "risk gate blocked decision"


def test_orchestrator_preserves_agent_observations():
    observations = [
        {"agent": "trend", "score": 0.8},
        {"agent": "volatility", "score": 0.2},
    ]

    result = DecisionOrchestrator().decide(
        "BTC-USD",
        [signal()],
        observations=observations,
    )

    assert result.observations == tuple(observations)


def test_orchestrator_rejects_wrong_symbol():
    try:
        DecisionOrchestrator().decide(
            "BTC-USD",
            [signal(symbol="ETH-USD")],
        )
    except ValueError as exc:
        assert "match symbol" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_orchestrator_can_use_algorithm_pipeline_fusion():
    from atlas.algorithms.pipeline import AlgorithmPipeline
    from atlas.algorithms.registry import AlgorithmRegistry

    class BuyAlgorithm:
        name = "test_buy"
        timeframe = "multi"

        def generate_signal(self, symbol, candles):
            return AlgorithmSignal(
                algorithm=self.name,
                symbol=symbol,
                timeframe="multi",
                action=Action.BUY,
                score=90.0,
                confidence=0.90,
            )

    class HoldAlgorithm:
        name = "test_hold"
        timeframe = "multi"

        def generate_signal(self, symbol, candles):
            return AlgorithmSignal(
                algorithm=self.name,
                symbol=symbol,
                timeframe="multi",
                action=Action.HOLD,
                score=50.0,
                confidence=0.50,
            )

    registry = AlgorithmRegistry()
    registry.register(BuyAlgorithm())
    registry.register(HoldAlgorithm())

    pipeline = AlgorithmPipeline(registry)

    result = DecisionOrchestrator(
        algorithm_pipeline=pipeline,
    ).decide(
        "BTC-USD",
        [],
        market_data={
            "price": 100.0,
            "candles": [],
        },
    )

    assert result.fusion_result is not None
    assert result.fusion_result.action is Action.HOLD
    assert result.fusion_result.agreement == 0.5
    assert result.decision.action is DecisionAction.HOLD
    assert result.fusion_result.symbol == "BTC-USD"


def test_orchestrator_fusion_confidence_is_normalized():
    from atlas.algorithms.pipeline import AlgorithmPipeline
    from atlas.algorithms.registry import AlgorithmRegistry

    class BuyAlgorithm:
        name = "test_buy"
        timeframe = "multi"

        def generate_signal(self, symbol, candles):
            return AlgorithmSignal(
                algorithm=self.name,
                symbol=symbol,
                timeframe="multi",
                action=Action.BUY,
                score=90.0,
                confidence=0.90,
            )

    registry = AlgorithmRegistry()
    registry.register(BuyAlgorithm())

    result = DecisionOrchestrator(
        algorithm_pipeline=AlgorithmPipeline(registry),
    ).decide(
        "BTC-USD",
        [],
        market_data={
            "price": 100.0,
            "candles": [],
        },
    )

    assert result.fusion_result is not None
    assert 0.0 <= result.decision.confidence <= 1.0
