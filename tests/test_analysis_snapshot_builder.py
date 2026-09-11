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
