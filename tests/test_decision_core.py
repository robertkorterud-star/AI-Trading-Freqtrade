from types import SimpleNamespace

import pytest

from atlas.algorithms.base import Action
from atlas.algorithms.decision_core import (
    DecisionAction,
    DecisionCore,
    RiskContext,
)


def signal(action, confidence=0.8):
    return SimpleNamespace(
        action=action,
        confidence=confidence,
    )


def test_strong_buy_consensus_returns_buy():
    core = DecisionCore()

    result = core.decide(
        [
            signal(Action.BUY, 0.9),
            signal(Action.BUY, 0.8),
            signal(Action.BUY, 0.7),
        ]
    )

    assert result.action is DecisionAction.BUY
    assert result.score > 0.55
    assert result.confidence == pytest.approx(0.8)


def test_strong_sell_consensus_returns_sell():
    core = DecisionCore()

    result = core.decide(
        [
            signal(Action.SELL, 0.9),
            signal(Action.SELL, 0.8),
            signal(Action.SELL, 0.7),
        ]
    )

    assert result.action is DecisionAction.SELL
    assert result.score < -0.55


def test_mixed_direction_returns_hold():
    core = DecisionCore()

    result = core.decide(
        [
            signal(Action.BUY, 0.8),
            signal(Action.SELL, 0.8),
            signal(Action.HOLD, 0.8),
        ]
    )

    assert result.action is DecisionAction.HOLD
    assert result.reason == "no directional consensus"


def test_low_confidence_returns_hold():
    core = DecisionCore(minimum_confidence=0.6)

    result = core.decide(
        [
            signal(Action.BUY, 0.4),
            signal(Action.BUY, 0.5),
        ]
    )

    assert result.action is DecisionAction.HOLD
    assert result.reason == "confidence below minimum"


def test_high_risk_blocks_buy():
    core = DecisionCore(maximum_risk=0.5)

    result = core.decide(
        [
            signal(Action.BUY, 0.95),
            signal(Action.BUY, 0.90),
        ],
        RiskContext(
            risk_score=0.9,
            volatility_score=0.9,
            drawdown_score=0.8,
            position_score=0.7,
        ),
    )

    assert result.action is DecisionAction.HOLD
    assert result.reason == "risk gate blocked decision"


def test_low_risk_allows_strong_buy():
    core = DecisionCore(maximum_risk=0.7)

    result = core.decide(
        [
            signal(Action.BUY, 0.95),
            signal(Action.BUY, 0.90),
        ],
        RiskContext(
            risk_score=0.1,
            volatility_score=0.2,
            drawdown_score=0.1,
            position_score=0.1,
        ),
    )

    assert result.action is DecisionAction.BUY


def test_empty_signal_set_returns_hold():
    core = DecisionCore()

    result = core.decide([])

    assert result.action is DecisionAction.HOLD
    assert result.confidence == 0.0
    assert result.score == 0.0
    assert result.reason == "no signals"


def test_risk_score_is_aggregated():
    core = DecisionCore()

    result = core.decide(
        [signal(Action.BUY, 0.8)],
        RiskContext(
            risk_score=0.2,
            volatility_score=0.4,
            drawdown_score=0.6,
            position_score=0.8,
        ),
    )

    assert result.risk_score == pytest.approx(0.5)


def test_invalid_thresholds_are_rejected():
    with pytest.raises(ValueError):
        DecisionCore(buy_threshold=1.5)

    with pytest.raises(ValueError):
        DecisionCore(sell_threshold=0.1)

    with pytest.raises(ValueError):
        DecisionCore(minimum_confidence=-0.1)

    with pytest.raises(ValueError):
        DecisionCore(maximum_risk=1.5)


def test_hold_signal_does_not_create_direction():
    core = DecisionCore()

    result = core.decide(
        [
            signal(Action.BUY, 0.9),
            signal(Action.HOLD, 0.9),
        ]
    )

    assert result.action is DecisionAction.HOLD
    assert result.score == pytest.approx(0.45)
