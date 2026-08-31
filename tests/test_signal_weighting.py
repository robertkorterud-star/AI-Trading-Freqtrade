from types import SimpleNamespace

import pytest

from atlas.algorithms.base import Action
from atlas.algorithms.decision_core import DecisionAction, DecisionCore


def weighted_signal(algorithm, action, score, confidence=1.0):
    return SimpleNamespace(
        algorithm=algorithm,
        action=action,
        score=score,
        confidence=confidence,
    )


def test_default_weight_preserves_legacy_signal_behaviour():
    core = DecisionCore()

    result = core.decide(
        [
            SimpleNamespace(action=Action.BUY, confidence=0.9),
            SimpleNamespace(action=Action.BUY, confidence=0.7),
        ]
    )

    assert result.action is DecisionAction.BUY
    assert result.score == pytest.approx(0.8)
    assert result.confidence == pytest.approx(0.8)


def test_agent_weight_is_lower_than_fusion_weight_by_default():
    core = DecisionCore()

    result = core.decide(
        [
            weighted_signal("signal_fusion", "BUY", 0.8, 1.0),
            weighted_signal("agent:momentum", "SELL", 0.8, 1.0),
        ]
    )

    expected = ((0.8 * 1.5) + (-0.8 * 0.75)) / (1.5 + 0.75)

    assert result.score == pytest.approx(expected)
    assert result.score > 0.0
    assert result.action is DecisionAction.HOLD


def test_multi_horizon_has_intermediate_weight():
    core = DecisionCore()

    result = core.decide(
        [
            weighted_signal("signal_fusion", "BUY", 0.8, 1.0),
            weighted_signal("multi_horizon", "SELL", 0.8, 1.0),
            weighted_signal("agent:momentum", "SELL", 0.8, 1.0),
        ]
    )

    expected = (
        (0.8 * 1.5) + (-0.8 * 1.25) + (-0.8 * 0.75)
    ) / (1.5 + 1.25 + 0.75)

    assert result.score == pytest.approx(expected)
    assert result.score == pytest.approx(-0.1142857143)
    assert result.action is DecisionAction.HOLD


def test_custom_weights_change_final_decision():
    core = DecisionCore(
        fusion_weight=2.0,
        horizon_weight=1.0,
        agent_weight=0.25,
    )

    result = core.decide(
        [
            weighted_signal("signal_fusion", "BUY", 0.8, 1.0),
            weighted_signal("agent:contrarian", "SELL", 1.0, 1.0),
        ]
    )

    expected = ((0.8 * 2.0) + (-1.0 * 0.25)) / 2.25

    assert result.score == pytest.approx(expected)
    assert result.action is DecisionAction.BUY


def test_signal_weights_also_weight_confidence():
    core = DecisionCore()

    result = core.decide(
        [
            weighted_signal("signal_fusion", "BUY", 0.8, 1.0),
            weighted_signal("agent:weak", "BUY", 0.8, 0.0),
        ]
    )

    assert result.confidence == pytest.approx(1.5 / 2.25)
    assert result.score == pytest.approx((0.8 * 1.5) / 2.25)
    assert result.action is DecisionAction.HOLD


def test_invalid_signal_weights_are_rejected():
    with pytest.raises(ValueError):
        DecisionCore(fusion_weight=0.0)

    with pytest.raises(ValueError):
        DecisionCore(horizon_weight=-1.0)

    with pytest.raises(ValueError):
        DecisionCore(agent_weight=0.0)
