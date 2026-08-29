from atlas.algorithms.base import Action
from atlas.algorithms.position_exit import (
    PositionAction,
    PositionContext,
    PositionExitEngine,
)


def test_strong_buy_enters_position():
    engine = PositionExitEngine()

    result = engine.decide(
        Action.BUY,
        PositionContext(
            confidence=0.95,
            risk_score=0.10,
        ),
    )

    assert result.action is PositionAction.ENTER
    assert result.target_position > 0.0
    assert result.target_position <= engine.max_position


def test_high_risk_reduces_position_size():
    engine = PositionExitEngine()

    low_risk = engine.decide(
        Action.BUY,
        PositionContext(
            confidence=0.95,
            risk_score=0.10,
        ),
    )

    high_risk = engine.decide(
        Action.BUY,
        PositionContext(
            confidence=0.95,
            risk_score=0.90,
        ),
    )

    assert low_risk.action is PositionAction.ENTER
    assert high_risk.action is PositionAction.ENTER
    assert high_risk.target_position < low_risk.target_position


def test_weak_buy_without_position_holds():
    engine = PositionExitEngine()

    result = engine.decide(
        Action.BUY,
        PositionContext(
            confidence=0.40,
            risk_score=0.10,
        ),
    )

    assert result.action is PositionAction.HOLD
    assert result.target_position == 0.0


def test_weak_buy_reduces_existing_position():
    engine = PositionExitEngine()

    result = engine.decide(
        Action.BUY,
        PositionContext(
            current_position=0.80,
            confidence=0.40,
            risk_score=0.10,
        ),
    )

    assert result.action is PositionAction.REDUCE
    assert result.target_position < 0.80


def test_strong_sell_exits_position():
    engine = PositionExitEngine()

    result = engine.decide(
        Action.SELL,
        PositionContext(
            current_position=0.80,
            confidence=0.90,
        ),
    )

    assert result.action is PositionAction.EXIT
    assert result.target_position == 0.0


def test_moderate_sell_reduces_position():
    engine = PositionExitEngine()

    result = engine.decide(
        Action.SELL,
        PositionContext(
            current_position=0.80,
            confidence=0.50,
        ),
    )

    assert result.action is PositionAction.REDUCE
    assert result.target_position < 0.80
    assert result.target_position > 0.0


def test_weak_sell_holds_position():
    engine = PositionExitEngine()

    result = engine.decide(
        Action.SELL,
        PositionContext(
            current_position=0.80,
            confidence=0.20,
        ),
    )

    assert result.action is PositionAction.HOLD
    assert result.target_position == 0.80


def test_sell_without_position_holds():
    engine = PositionExitEngine()

    result = engine.decide(
        Action.SELL,
        PositionContext(
            current_position=0.0,
            confidence=0.90,
        ),
    )

    assert result.action is PositionAction.HOLD
    assert result.target_position == 0.0


def test_stop_loss_has_priority():
    engine = PositionExitEngine(stop_loss=0.08)

    result = engine.decide(
        Action.BUY,
        PositionContext(
            current_position=0.80,
            entry_price=100.0,
            current_price=90.0,
            confidence=0.95,
        ),
    )

    assert result.action is PositionAction.EXIT
    assert result.target_position == 0.0
    assert "stop loss" in result.reason


def test_trailing_stop_has_priority():
    engine = PositionExitEngine(trailing_stop=0.10)

    result = engine.decide(
        Action.BUY,
        PositionContext(
            current_position=0.80,
            peak_price=100.0,
            current_price=85.0,
            confidence=0.95,
        ),
    )

    assert result.action is PositionAction.EXIT
    assert result.target_position == 0.0
    assert "trailing stop" in result.reason


def test_hold_preserves_existing_position():
    engine = PositionExitEngine()

    result = engine.decide(
        Action.HOLD,
        PositionContext(
            current_position=0.60,
        ),
    )

    assert result.action is PositionAction.HOLD
    assert result.target_position == 0.60


def test_position_fraction_is_bounded():
    engine = PositionExitEngine(max_position=1.0)

    result = engine.decide(
        Action.BUY,
        PositionContext(
            confidence=1.0,
            risk_score=0.0,
        ),
    )

    assert 0.0 <= result.size_fraction <= 1.0
