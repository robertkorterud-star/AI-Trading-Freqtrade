from atlas.models.action import Action
from atlas.models.analysis_result import AnalysisResult
from atlas.models.decision_result import DecisionResult
from atlas.services.analysis_snapshot_builder import (
    AnalysisSnapshotBuilder,
)


def make_decision():
    return DecisionResult(
        symbol="BTC-USD",
        action=Action.BUY,
        confidence=90.0,
        evidence=85.0,
        analysts=[
            "Technical Analyst",
            "News Analyst",
        ],
        agent_weights={
            "Technical Analyst": 0.60,
            "News Analyst": 0.40,
        },
        dominant_action=Action.BUY,
        dominant_weight=60.0,
        action_support_analyst="Technical Analyst",
        action_support_action=Action.BUY,
        action_support_weight=0.60,
        opposing_analysts=[],
        adaptive_override=False,
        decision_margin=20.0,
        robustness=80.0,
        robustness_level="STRONG",
        reasoning=[
            "Decision based on combined analyst evidence.",
            "Learned support: Technical Analyst supports BUY.",
        ],
    )


def make_results():
    return [
        AnalysisResult(
            symbol="BTC-USD",
            analyst="Technical Analyst",
            action=Action.BUY,
            confidence=90.0,
            evidence=90.0,
            reasoning=["Strong technical evidence."],
        ),
        AnalysisResult(
            symbol="BTC-USD",
            analyst="News Analyst",
            action=Action.BUY,
            confidence=85.0,
            evidence=80.0,
            reasoning=["Positive news."],
        ),
    ]


def test_snapshot_builder_serializes_action_support():
    builder = AnalysisSnapshotBuilder()

    snapshot = builder.build(
        symbol="BTC-USD",
        results=make_results(),
        decision=make_decision(),
    )

    decision = snapshot.decision

    assert decision["action_support_analyst"] == (
        "Technical Analyst"
    )

    assert decision["action_support_action"] == "BUY"

    assert decision["action_support_weight"] == 0.60


def test_snapshot_builder_preserves_action_support_round_trip():
    builder = AnalysisSnapshotBuilder()

    snapshot = builder.build(
        symbol="BTC-USD",
        results=make_results(),
        decision=make_decision(),
    )

    data = snapshot.decision

    assert data["action_support_analyst"] == (
        "Technical Analyst"
    )
    assert data["action_support_action"] == "BUY"
    assert data["action_support_weight"] == 0.60


def test_snapshot_builder_keeps_reference_to_decision_for_trade_linkage():
    decision = make_decision()

    snapshot = AnalysisSnapshotBuilder().build(
        symbol="BTC-USD",
        results=make_results(),
        decision=decision,
    )

    assert snapshot.decision_ref is decision
    assert decision.analysis_snapshot_id is None


def test_snapshot_builder_preserves_algorithm_signal_metadata():
    decision = make_decision()
    result = AnalysisResult(
        symbol="BTC-USD",
        analyst="algorithm:intraday_momentum",
        action=Action.BUY,
        confidence=82.0,
        evidence=70.0,
        reasoning=["Momentum is positive."],
        signal_confidence=82.0,
        metadata={
            "algorithm": "intraday_momentum",
            "timeframe": "5m",
            "score": 85.0,
            "expected_edge": 0.02,
        },
    )

    snapshot = AnalysisSnapshotBuilder().build(
        symbol="BTC-USD",
        results=[result],
        decision=decision,
    )

    assert snapshot.results[0]["metadata"] == {
        "algorithm": "intraday_momentum",
        "timeframe": "5m",
        "score": 85.0,
        "expected_edge": 0.02,
    }


def test_snapshot_builder_preserves_final_risk_and_portfolio_decision_context():
    from types import SimpleNamespace

    decision = make_decision()
    decision.risk_assessment = SimpleNamespace(
        allowed=True,
        action=Action.BUY,
        position_size=0.25,
        position_value=2500.0,
        risk_level="LOW",
        reasons=["Within risk limits."],
    )
    decision.portfolio_assessment = SimpleNamespace(
        allowed=True,
        approved_value=2500.0,
        reasons=["Within portfolio limits."],
    )

    snapshot = AnalysisSnapshotBuilder().build(
        symbol="BTC-USD",
        results=make_results(),
        decision=decision,
    )

    assert snapshot.decision["risk_assessment"] == {
        "allowed": True,
        "action": "BUY",
        "position_size": 0.25,
        "position_value": 2500.0,
        "risk_level": "LOW",
        "reasons": ["Within risk limits."],
    }
    assert snapshot.decision["portfolio_assessment"] == {
        "allowed": True,
        "approved_value": 2500.0,
        "reasons": ["Within portfolio limits."],
    }
