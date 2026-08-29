from atlas.agents.intelligence import IntelligenceResult
from atlas.algorithms.decision_core import DecisionCore, RiskContext
from atlas.algorithms.multi_horizon import (
    HorizonSignal,
    MultiHorizonDecisionEngine,
    TradingHorizon,
)
from atlas.algorithms.position_exit import PositionAction, PositionContext
from atlas.core.decision_orchestrator import DecisionOrchestrator
from atlas.models.action import Action


def _intelligence(score=0.9, confidence=0.9, direction="bullish"):
    return IntelligenceResult(
        symbol="BTC-USD",
        score=score,
        confidence=confidence,
        direction=direction,
        observations=(),
    )


def _horizon(action=Action.BUY, score=90.0, confidence=90.0):
    engine = MultiHorizonDecisionEngine()
    return engine.decide(
        "BTC-USD",
        [
            HorizonSignal(
                TradingHorizon.INTRADAY,
                action,
                score,
                confidence,
            ),
            HorizonSignal(
                TradingHorizon.SWING,
                action,
                score,
                confidence,
            ),
            HorizonSignal(
                TradingHorizon.POSITION,
                action,
                score,
                confidence,
            ),
        ],
    )


def test_strong_consensus_enters_position():
    result = DecisionOrchestrator().decide(
        _intelligence(),
        _horizon(),
        position=PositionContext(),
    )

    assert result.decision.action is not Action.HOLD
    assert result.position.action is PositionAction.ENTER
    assert result.combined_score > 0.55


def test_high_risk_blocks_entry():
    result = DecisionOrchestrator().decide(
        _intelligence(),
        _horizon(),
        risk=RiskContext(risk_score=1.0),
        position=PositionContext(),
    )

    assert result.decision.action is Action.HOLD
    assert result.position.action is PositionAction.HOLD
    assert "risk gate" in result.decision.reason


def test_conflicting_intelligence_and_horizon_can_cancel():
    result = DecisionOrchestrator().decide(
        _intelligence(score=-0.9, direction="bearish"),
        _horizon(action=Action.BUY, score=70.0),
    )

    assert result.combined_score < 0.0
    assert result.decision.action is Action.HOLD


def test_strong_sell_exits_existing_position():
    result = DecisionOrchestrator().decide(
        _intelligence(score=-0.95, direction="bearish"),
        _horizon(action=Action.SELL, score=10.0),
        position=PositionContext(current_position=0.8, confidence=0.95),
    )

    assert result.decision.action is Action.SELL
    assert result.position.action is PositionAction.EXIT
    assert result.position.target_position == 0.0


def test_symbol_mismatch_is_rejected():
    horizon = _horizon()
    other = IntelligenceResult(
        symbol="ETH-USD",
        score=0.9,
        confidence=0.9,
        direction="bullish",
        observations=(),
    )

    try:
        DecisionOrchestrator().decide(other, horizon)
    except ValueError as exc:
        assert "symbols must match" in str(exc)
    else:
        raise AssertionError("symbol mismatch should raise ValueError")


def test_weights_are_normalized():
    orchestrator = DecisionOrchestrator(
        intelligence_weight=7.0,
        horizon_weight=3.0,
    )

    assert orchestrator.intelligence_weight == 0.7
    assert orchestrator.horizon_weight == 0.3


def test_result_contains_reproducible_trace():
    result = DecisionOrchestrator().decide(_intelligence(), _horizon())
    payload = result.as_dict()

    assert payload["symbol"] == "BTC-USD"
    assert payload["decision"]["action"] == result.decision.action.value
    assert len(payload["reasoning"]) >= 6


def test_custom_decision_core_can_be_injected():
    core = DecisionCore(
        buy_threshold=0.40,
        minimum_confidence=0.40,
        maximum_risk=0.90,
    )

    result = DecisionOrchestrator(decision_core=core).decide(
        _intelligence(score=0.6, confidence=0.7),
        _horizon(score=75.0, confidence=70.0),
    )

    assert result.decision.action is Action.BUY
