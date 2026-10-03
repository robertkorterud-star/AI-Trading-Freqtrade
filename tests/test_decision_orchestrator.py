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

# ============================================================
# ATLAS agent -> DecisionCore integration tests
# ============================================================

from types import SimpleNamespace

from atlas.algorithms.orchestrator import DecisionOrchestrator


class CapturingDecisionCore:
    """Test double that captures the signals received by DecisionCore."""

    def __init__(self):
        self.received_signals = None
        self.received_risk = None

    def decide(self, signals, risk):
        self.received_signals = list(signals)
        self.received_risk = risk
        return SimpleNamespace(
            action=SimpleNamespace(value="HOLD"),
            score=0.0,
            confidence=0.0,
            risk_score=0.0,
        )


def test_orchestrator_passes_bullish_agent_to_decision_core():
    core = CapturingDecisionCore()
    orchestrator = DecisionOrchestrator(
        decision_core=core,
    )

    observation = SimpleNamespace(
        agent="bullish_test_agent",
        symbol="BTC-USD",
        score=0.90,
        confidence=0.85,
        direction="bullish",
        reason="strong bullish signal",
    )

    result = orchestrator.decide(
        symbol="BTC-USD",
        signals=[],
        observations=[observation],
    )

    agent_signals = [
        signal
        for signal in core.received_signals
        if signal.algorithm == "agent:bullish_test_agent"
    ]

    assert len(agent_signals) == 1

    signal = agent_signals[0]

    assert signal.symbol == "BTC-USD"
    assert signal.action == "BUY"
    assert signal.score == 0.90
    assert signal.confidence == 0.85
    assert signal.timeframe == "agent"
    assert signal.reasoning == ["strong bullish signal"]

    assert result.observations == (observation,)


def test_orchestrator_passes_bearish_agent_to_decision_core():
    core = CapturingDecisionCore()
    orchestrator = DecisionOrchestrator(
        decision_core=core,
    )

    observation = SimpleNamespace(
        agent="bearish_test_agent",
        symbol="BTC-USD",
        score=-0.80,
        confidence=0.75,
        direction="bearish",
        reason="strong bearish signal",
    )

    orchestrator.decide(
        symbol="BTC-USD",
        signals=[],
        observations=[observation],
    )

    agent_signals = [
        signal
        for signal in core.received_signals
        if signal.algorithm == "agent:bearish_test_agent"
    ]

    assert len(agent_signals) == 1

    signal = agent_signals[0]

    assert signal.symbol == "BTC-USD"
    assert signal.action == "SELL"
    assert signal.score == -0.80
    assert signal.confidence == 0.75
    assert signal.reasoning == ["strong bearish signal"]


def test_orchestrator_rejects_agent_observation_for_wrong_symbol():
    core = CapturingDecisionCore()
    orchestrator = DecisionOrchestrator(
        decision_core=core,
    )

    observation = SimpleNamespace(
        agent="wrong_symbol_agent",
        symbol="ETH-USD",
        score=0.90,
        confidence=0.90,
        direction="bullish",
        reason="wrong symbol",
    )

    try:
        orchestrator.decide(
            symbol="BTC-USD",
            signals=[],
            observations=[observation],
        )
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert str(exc) == "all agent observations must match symbol"

# ============================================================
# ATLAS agent -> final DecisionCore influence tests
# ============================================================

def test_bullish_agent_can_influence_final_decision():
    from types import SimpleNamespace

    from atlas.algorithms.orchestrator import DecisionOrchestrator

    observation = SimpleNamespace(
        agent="bullish_influence_agent",
        symbol="BTC-USD",
        score=1.0,
        confidence=1.0,
        direction="bullish",
        reason="maximum bullish conviction",
    )

    orchestrator = DecisionOrchestrator()

    result = orchestrator.decide(
        symbol="BTC-USD",
        signals=[],
        observations=[observation],
    )

    assert result.decision.action.value == "buy"
    assert result.decision.score > 0
    assert result.decision.confidence > 0


def test_bearish_agent_can_influence_final_decision():
    from types import SimpleNamespace

    from atlas.algorithms.orchestrator import DecisionOrchestrator

    observation = SimpleNamespace(
        agent="bearish_influence_agent",
        symbol="BTC-USD",
        score=-1.0,
        confidence=1.0,
        direction="bearish",
        reason="maximum bearish conviction",
    )

    orchestrator = DecisionOrchestrator()

    result = orchestrator.decide(
        symbol="BTC-USD",
        signals=[],
        observations=[observation],
    )

    assert result.decision.action.value == "sell"
    assert result.decision.score < 0
    assert result.decision.confidence > 0


def test_conflicting_agent_observations_reduce_signal_strength():
    from types import SimpleNamespace

    from atlas.algorithms.orchestrator import DecisionOrchestrator

    bullish = SimpleNamespace(
        agent="bullish_agent",
        symbol="BTC-USD",
        score=1.0,
        confidence=1.0,
        direction="bullish",
        reason="bullish",
    )

    bearish = SimpleNamespace(
        agent="bearish_agent",
        symbol="BTC-USD",
        score=-1.0,
        confidence=1.0,
        direction="bearish",
        reason="bearish",
    )

    orchestrator = DecisionOrchestrator()

    result = orchestrator.decide(
        symbol="BTC-USD",
        signals=[],
        observations=[bullish, bearish],
    )

    assert abs(result.decision.score) < 0.01


def test_neutral_agent_does_not_create_directional_bias():
    from types import SimpleNamespace

    from atlas.algorithms.orchestrator import DecisionOrchestrator

    observation = SimpleNamespace(
        agent="neutral_agent",
        symbol="BTC-USD",
        score=0.0,
        confidence=1.0,
        direction="neutral",
        reason="no directional conviction",
    )

    orchestrator = DecisionOrchestrator()

    result = orchestrator.decide(
        symbol="BTC-USD",
        signals=[],
        observations=[observation],
    )

    assert abs(result.decision.score) < 0.01


def test_multiple_bullish_agents_strengthen_bullish_signal():
    from types import SimpleNamespace

    from atlas.algorithms.orchestrator import DecisionOrchestrator

    observations = [
        SimpleNamespace(
            agent="bullish_agent_1",
            symbol="BTC-USD",
            score=0.8,
            confidence=0.9,
            direction="bullish",
            reason="bullish signal 1",
        ),
        SimpleNamespace(
            agent="bullish_agent_2",
            symbol="BTC-USD",
            score=0.9,
            confidence=0.9,
            direction="bullish",
            reason="bullish signal 2",
        ),
    ]

    orchestrator = DecisionOrchestrator()

    result = orchestrator.decide(
        symbol="BTC-USD",
        signals=[],
        observations=observations,
    )

    assert result.decision.action.value == "buy"
    assert result.decision.score > 0.5
    assert result.decision.confidence > 0


def test_agent_reasoning_is_preserved_in_orchestration_result():
    from types import SimpleNamespace

    from atlas.algorithms.orchestrator import DecisionOrchestrator

    observation = SimpleNamespace(
        agent="reasoning_agent",
        symbol="BTC-USD",
        score=0.75,
        confidence=0.80,
        direction="bullish",
        reason="momentum and breakout confirmation",
    )

    orchestrator = DecisionOrchestrator()

    result = orchestrator.decide(
        symbol="BTC-USD",
        signals=[],
        observations=[observation],
    )

    assert result.observations == (observation,)
    assert any(
        "Agent observations: 1." in item
        for item in result.reasoning
    )


def test_agent_signal_is_combined_with_existing_algorithm_signal():
    from types import SimpleNamespace

    from atlas.algorithms.base import AlgorithmSignal
    from atlas.algorithms.orchestrator import DecisionOrchestrator

    algorithm_signal = AlgorithmSignal(
        algorithm="test_algorithm",
        symbol="BTC-USD",
        timeframe="test",
        action="BUY",
        score=0.8,
        confidence=0.8,
    )

    observation = SimpleNamespace(
        agent="confirmation_agent",
        symbol="BTC-USD",
        score=0.9,
        confidence=0.9,
        direction="bullish",
        reason="agent confirms algorithm",
    )

    orchestrator = DecisionOrchestrator()

    result = orchestrator.decide(
        symbol="BTC-USD",
        signals=[algorithm_signal],
        observations=[observation],
    )

    assert result.decision.action.value == "buy"
    assert result.decision.score > 0



# ============================================================
# DecisionCore action normalization regression tests
# ============================================================

def test_agent_bullish_signal_reaches_buy_decision():
    from types import SimpleNamespace

    from atlas.algorithms.orchestrator import DecisionOrchestrator

    observation = SimpleNamespace(
        agent="regression_bullish",
        symbol="BTC-USD",
        score=1.0,
        confidence=1.0,
        direction="bullish",
        reason="maximum bullish conviction",
    )

    result = DecisionOrchestrator().decide(
        symbol="BTC-USD",
        signals=[],
        observations=[observation],
    )

    assert result.decision.action.value == "buy"
    assert result.decision.score >= 0.55


def test_agent_bearish_signal_reaches_sell_decision():
    from types import SimpleNamespace

    from atlas.algorithms.orchestrator import DecisionOrchestrator

    observation = SimpleNamespace(
        agent="regression_bearish",
        symbol="BTC-USD",
        score=-1.0,
        confidence=1.0,
        direction="bearish",
        reason="maximum bearish conviction",
    )

    result = DecisionOrchestrator().decide(
        symbol="BTC-USD",
        signals=[],
        observations=[observation],
    )

    assert result.decision.action.value == "sell"
    assert result.decision.score <= -0.55


def test_neutral_agent_does_not_create_maximum_hold_evidence():
    from types import SimpleNamespace

    from atlas.algorithms.orchestrator import DecisionOrchestrator

    observation = SimpleNamespace(
        agent="neutral_evidence_agent",
        symbol="BTC-USD",
        score=0.0,
        confidence=0.5,
        direction="neutral",
        reason="no directional conviction",
    )

    result = DecisionOrchestrator().decide(
        symbol="BTC-USD",
        signals=[],
        observations=[observation],
    )

    canonical = result.canonical_decision

    assert canonical is not None
    assert canonical.action is Action.HOLD
    assert canonical.evidence == 0.0


def test_neutral_market_intelligence_does_not_create_maximum_hold_evidence():
    from atlas.algorithms.base import AlgorithmSignal
    from atlas.decision.engine import DecisionEngine

    signal = AlgorithmSignal(
        algorithm="market_intelligence",
        symbol="BTC-USD",
        timeframe="multi",
        action=Action.HOLD,
        score=0.0,
        confidence=0.5,
    )

    result = DecisionEngine().evaluate_algorithm_signals([signal])

    assert result.action is Action.HOLD
    assert result.evidence == 0.0


def test_orchestrator_forwards_open_position_context_to_canonical_engine():
    """Canonical DecisionEngine must receive the actual open-position context."""
    from atlas.algorithms.base import AlgorithmSignal
    from atlas.algorithms.orchestrator import DecisionOrchestrator
    from atlas.models.action import Action

    captured = {}

    class CapturingDecisionEngine:
        def evaluate_algorithm_signals(
            self,
            signals,
            *,
            price=None,
            equity=None,
            current_exposure_pct=0.0,
            drawdown_pct=0.0,
            portfolio_positions=(),
            current_position=0.0,
            last_buy_price=None,
            average_price=None,
            peak_price=None,
        ):
            captured.update(
                current_position=current_position,
                last_buy_price=last_buy_price,
                average_price=average_price,
                peak_price=peak_price,
            )

            return type(
                "CanonicalDecision",
                (),
                {
                    "action": Action.SELL,
                    "confidence": 80.0,
                    "evidence": 80.0,
                },
            )()

    orchestrator = DecisionOrchestrator(
        decision_engine=CapturingDecisionEngine(),
    )

    orchestrator.decide(
        "BTC-USD",
        [
            AlgorithmSignal(
                algorithm="test_sell",
                symbol="BTC-USD",
                timeframe="4h",
                action=Action.SELL,
                score=20.0,
                confidence=0.8,
            )
        ],
        price=100.0,
        equity=10_000.0,
        current_position=2.5,
        last_buy_price=90.0,
        average_price=92.0,
        peak_price=110.0,
    )

    assert captured == {
        "current_position": 2.5,
        "last_buy_price": 90.0,
        "average_price": 92.0,
        "peak_price": 110.0,
    }


def test_canonical_sell_with_open_position_is_not_blocked_as_positionless():
    """An actual open position must allow canonical SELL risk evaluation."""
    from atlas.algorithms.base import AlgorithmSignal
    from atlas.algorithms.orchestrator import DecisionOrchestrator
    from atlas.models.action import Action
    from atlas.decision.engine import DecisionEngine
    from atlas.risk.manager import RiskManager

    risk_manager = RiskManager()
    orchestrator = DecisionOrchestrator(
        decision_engine=DecisionEngine(risk_manager=risk_manager),
    )

    result = orchestrator.decide(
        "BTC-USD",
        [],
        algorithm_signals=[
            AlgorithmSignal(
                algorithm="test_sell",
                symbol="BTC-USD",
                timeframe="4h",
                action=Action.SELL,
                score=20.0,
                confidence=0.90,
            )
        ],
        price=100.0,
        equity=10_000.0,
        current_position=2.5,
        average_price=110.0,
    )

    canonical = result.canonical_decision
    risk = orchestrator.decision_engine.last_risk_assessment

    assert canonical is not None
    assert canonical.action is Action.SELL
    assert risk is not None
    assert risk.allowed is True
    assert "No open position available to sell." not in risk.reasons
