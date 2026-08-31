"""
Decision Explanation Builder

Converts a structured DecisionResult into a human-readable
DecisionExplanation.
"""
from atlas.models.action import Action

from atlas.models.decision_explanation import DecisionExplanation
from atlas.models.decision_result import DecisionResult


def explain_decision(
    decision: DecisionResult,
    agreement: float,
) -> DecisionExplanation:
    """Build a structured human-readable explanation."""

    action = decision.action
    level = decision.robustness_level

    headline = (
        f"{action.value} – {level}"
    )

    summary = (
        f"ATLAS decided {action.value} with "
        f"{decision.confidence:.1f}% confidence and "
        f"{decision.evidence:.1f}% evidence."
    )

    decision_path = []

    if (
        decision.opposing_analysts
        and decision.dominant_action in {
            Action.BUY,
            Action.SELL,
        }
    ):
        decision_path.append(
            "Directional analyst signals are in conflict."
        )

    if decision.dominant_action is not None:
        decision_path.append(
            f"Dominant signal: "
            f"{decision.dominant_action.value} "
            f"with {decision.dominant_weight:.1f}% "
            f"weighted influence."
        )

    if decision.action == decision.dominant_action:
        decision_path.append(
            "Final decision follows the dominant signal."
        )
    elif decision.adaptive_override:
        decision_path.append(
            f"Adaptive weighting resolved the conflict "
            f"in favor of {decision.action.value}."
        )
    elif (
        decision.action == Action.HOLD
        and decision.dominant_action in {
            Action.BUY,
            Action.SELL,
        }
    ):
        decision_path.append(
            "ATLAS kept HOLD because the dominant "
            "directional signal did not clear the "
            "conflict-resolution gate."
        )
    else:
        decision_path.append(
            f"Final policy decision: {decision.action.value}."
        )

    decision_path.append(
        f"Decision margin: {decision.decision_margin:.1f}%."
    )

    decision_path.append(
        f"Robustness: {decision.robustness:.1f}% "
        f"({decision.robustness_level})."
    )

    key_reasons = []

    if decision.dominant_action is not None:
        key_reasons.append(
            f"{decision.dominant_action.value} is the dominant "
            f"signal with {decision.dominant_weight:.1f}% weighted influence."
        )

    key_reasons.append(
        f"Analyst agreement is {agreement:.1f}%."
    )

    key_reasons.append(
        f"Decision margin is {decision.decision_margin:.1f}%."
    )

    if decision.opposing_analysts:
        key_reasons.append(
            "Opposing analysts: "
            + ", ".join(decision.opposing_analysts)
            + "."
        )

    if (
        decision.action_support_analyst is not None
        and decision.action_support_action is not None
    ):
        key_reasons.append(
            f"Strongest learned support: "
            f"{decision.action_support_analyst} "
            f"for {decision.action_support_action.value} "
            f"at {decision.action_support_weight * 100:.1f}% weight."
        )

    if decision.adaptive_override:
        key_reasons.append(
            "Adaptive weighting influenced the final decision."
        )
    elif decision.agent_weights:
        key_reasons.append(
            "Adaptive analyst weights were considered."
        )

    return DecisionExplanation(
        action=action,
        headline=headline,
        summary=summary,
        evidence=decision.evidence,
        confidence=decision.confidence,
        agreement=agreement,
        dominant_action=decision.dominant_action,
        dominant_weight=decision.dominant_weight,
        action_support_analyst=decision.action_support_analyst,
        action_support_action=decision.action_support_action,
        action_support_weight=decision.action_support_weight,
        decision_margin=decision.decision_margin,
        robustness=decision.robustness,
        robustness_level=decision.robustness_level,
        opposing_analysts=list(
            decision.opposing_analysts
        ),
        adaptive_override=decision.adaptive_override,
        decision_path=decision_path,
        key_reasons=key_reasons,
    )
