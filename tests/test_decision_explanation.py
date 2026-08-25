
from atlas.decision.explanation import explain_decision
from atlas.models.action import Action
from atlas.models.decision_explanation import DecisionExplanation


def test_decision_explanation_defaults():
    explanation = DecisionExplanation(
        action=Action.BUY,
        headline="BUY – STRONG",
        summary="ATLAS has a strong bullish decision.",
        evidence=85.0,
        confidence=90.0,
        agreement=100.0,
    )

    assert explanation.action == Action.BUY
    assert explanation.headline == "BUY – STRONG"
    assert explanation.evidence == 85.0
    assert explanation.confidence == 90.0
    assert explanation.agreement == 100.0
    assert explanation.dominant_action is None
    assert explanation.dominant_weight == 0.0
    assert explanation.decision_margin == 0.0
    assert explanation.robustness == 0.0
    assert explanation.robustness_level == "WEAK"
    assert explanation.opposing_analysts == []
    assert explanation.adaptive_override is False
    assert explanation.key_reasons == []


def test_decision_explanation_preserves_structured_influence():
    explanation = DecisionExplanation(
        action=Action.BUY,
        headline="BUY – STRONG",
        summary="Technical analysis dominates the decision.",
        evidence=88.0,
        confidence=91.0,
        agreement=83.3,
        dominant_action=Action.BUY,
        dominant_weight=72.0,
        decision_margin=44.0,
        robustness=82.5,
        robustness_level="STRONG",
        opposing_analysts=["News Analyst"],
        adaptive_override=True,
        key_reasons=[
            "Technical Analyst is the dominant signal.",
            "Adaptive weighting influenced the decision.",
        ],
    )

    assert explanation.dominant_action == Action.BUY
    assert explanation.dominant_weight == 72.0
    assert explanation.decision_margin == 44.0
    assert explanation.robustness == 82.5
    assert explanation.robustness_level == "STRONG"
    assert explanation.opposing_analysts == ["News Analyst"]
    assert explanation.adaptive_override is True
    assert len(explanation.key_reasons) == 2


def test_explain_decision_builds_human_readable_summary():

    from atlas.decision.explanation import explain_decision
    from atlas.models.decision_result import DecisionResult

    decision = DecisionResult(
        symbol="BTC-USD",
        action=Action.BUY,
        confidence=91.0,
        evidence=88.0,
        analysts=[
            "Technical Analyst",
            "News Analyst",
            "Company Analyst",
        ],
        agent_weights={
            "Technical Analyst": 0.72,
            "News Analyst": 0.18,
            "Company Analyst": 0.10,
        },
        dominant_action=Action.BUY,
        dominant_weight=72.0,
        opposing_analysts=["News Analyst"],
        adaptive_override=True,
        decision_margin=44.0,
        robustness=82.5,
        robustness_level="STRONG",
    )

    explanation = explain_decision(
        decision,
        agreement=83.3,
    )

    assert explanation.action == Action.BUY
    assert explanation.headline == "BUY – STRONG"

    assert (
        explanation.summary
        == "ATLAS decided BUY with 91.0% confidence and 88.0% evidence."
    )

    assert explanation.evidence == 88.0
    assert explanation.confidence == 91.0
    assert explanation.agreement == 83.3
    assert explanation.dominant_action == Action.BUY
    assert explanation.dominant_weight == 72.0
    assert explanation.decision_margin == 44.0
    assert explanation.robustness == 82.5
    assert explanation.robustness_level == "STRONG"

    assert explanation.opposing_analysts == [
        "News Analyst"
    ]

    assert explanation.adaptive_override is True

    assert any(
        "BUY is the dominant signal" in reason
        for reason in explanation.key_reasons
    )

    assert any(
        "83.3%" in reason
        for reason in explanation.key_reasons
    )

    assert any(
        "44.0%" in reason
        for reason in explanation.key_reasons
    )

    assert any(
        "Opposing analysts" in reason
        for reason in explanation.key_reasons
    )

    assert any(
        "Adaptive weighting influenced" in reason
        for reason in explanation.key_reasons
    )


def test_explain_decision_handles_simple_hold():

    from atlas.decision.explanation import explain_decision
    from atlas.models.decision_result import DecisionResult

    decision = DecisionResult(
        symbol="BTC-USD",
        action=Action.HOLD,
        confidence=62.0,
        evidence=58.0,
        analysts=["Technical Analyst"],
        dominant_action=Action.HOLD,
        dominant_weight=60.0,
        decision_margin=15.0,
        robustness=55.0,
        robustness_level="WEAK",
    )

    explanation = explain_decision(
        decision,
        agreement=60.0,
    )

    assert explanation.action == Action.HOLD
    assert explanation.headline == "HOLD – WEAK"
    assert explanation.agreement == 60.0
    assert explanation.opposing_analysts == []
    assert explanation.adaptive_override is False

    assert any(
        "Adaptive analyst weights" not in reason
        for reason in explanation.key_reasons
    )


def test_explanation_reports_strongest_learned_action_support():
    from atlas.models.action import Action
    from atlas.models.decision_result import DecisionResult

    decision = DecisionResult(
        symbol="BTC-USD",
        action=Action.SELL,
        confidence=85.0,
        evidence=90.0,
        dominant_action=Action.SELL,
        dominant_weight=55.0,
        action_support_analyst="Technical Analyst",
        action_support_action=Action.BUY,
        action_support_weight=0.4063,
    )

    explanation = explain_decision(
        decision,
        agreement=66.7,
    )

    assert explanation.action_support_analyst == (
        "Technical Analyst"
    )

    assert explanation.action_support_action == (
        Action.BUY
    )

    assert explanation.action_support_weight == 0.4063

    assert any(
        "Technical Analyst" in reason
        and "BUY" in reason
        for reason in explanation.key_reasons
    )
