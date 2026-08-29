import pytest

from atlas.algorithms.multi_horizon import (
    HorizonSignal,
    MultiHorizonDecisionEngine,
    MultiHorizonResult,
    TradingHorizon,
)
from atlas.models.action import Action


def signal(
    horizon,
    action,
    score=80.0,
    confidence=75.0,
):
    return HorizonSignal(
        horizon=horizon,
        action=action,
        score=score,
        confidence=confidence,
    )


def test_strong_multi_horizon_buy():
    engine = MultiHorizonDecisionEngine()

    result = engine.decide(
        "BTC-USD",
        [
            signal(
                TradingHorizon.INTRADAY,
                Action.BUY,
                80.0,
            ),
            signal(
                TradingHorizon.SWING,
                Action.BUY,
                85.0,
            ),
            signal(
                TradingHorizon.POSITION,
                Action.BUY,
                90.0,
            ),
        ],
    )

    assert isinstance(result, MultiHorizonResult)
    assert result.action is Action.BUY
    assert result.score > 50.0
    assert result.alignment == pytest.approx(1.0)


def test_strong_multi_horizon_sell():
    engine = MultiHorizonDecisionEngine()

    result = engine.decide(
        "BTC-USD",
        [
            signal(
                TradingHorizon.INTRADAY,
                Action.SELL,
                20.0,
            ),
            signal(
                TradingHorizon.SWING,
                Action.SELL,
                15.0,
            ),
            signal(
                TradingHorizon.POSITION,
                Action.SELL,
                10.0,
            ),
        ],
    )

    assert result.action is Action.SELL
    assert result.score < 50.0
    assert result.alignment == pytest.approx(1.0)


def test_long_term_horizon_can_outweigh_intraday():
    engine = MultiHorizonDecisionEngine()

    result = engine.decide(
        "BTC-USD",
        [
            signal(
                TradingHorizon.INTRADAY,
                Action.SELL,
                10.0,
            ),
            signal(
                TradingHorizon.SWING,
                Action.BUY,
                80.0,
            ),
            signal(
                TradingHorizon.POSITION,
                Action.BUY,
                90.0,
            ),
        ],
    )

    assert result.action is Action.BUY


def test_conflicting_horizons_can_produce_hold():
    engine = MultiHorizonDecisionEngine(
        weights={
            TradingHorizon.INTRADAY: 1.0,
            TradingHorizon.SWING: 1.0,
            TradingHorizon.POSITION: 1.0,
        },
        decision_threshold=0.20,
    )

    result = engine.decide(
        "BTC-USD",
        [
            signal(
                TradingHorizon.INTRADAY,
                Action.BUY,
                80.0,
            ),
            signal(
                TradingHorizon.SWING,
                Action.SELL,
                80.0,
            ),
            signal(
                TradingHorizon.POSITION,
                Action.HOLD,
                50.0,
            ),
        ],
    )

    assert result.action is Action.HOLD


def test_horizon_cannot_be_duplicated():
    engine = MultiHorizonDecisionEngine()

    with pytest.raises(
        ValueError,
        match="each horizon may only appear once",
    ):
        engine.decide(
            "BTC-USD",
            [
                signal(
                    TradingHorizon.SWING,
                    Action.BUY,
                ),
                signal(
                    TradingHorizon.SWING,
                    Action.SELL,
                ),
            ],
        )


def test_unknown_horizon_weight_raises():
    engine = MultiHorizonDecisionEngine(
        weights={
            TradingHorizon.INTRADAY: 1.0,
        }
    )

    with pytest.raises(
        ValueError,
        match="configured weights",
    ):
        engine.decide(
            "BTC-USD",
            [
                signal(
                    TradingHorizon.SWING,
                    Action.BUY,
                )
            ],
        )


def test_empty_signals_raise():
    engine = MultiHorizonDecisionEngine()

    with pytest.raises(
        ValueError,
        match="at least one horizon signal",
    ):
        engine.decide("BTC-USD", [])


def test_invalid_signal_score_raises():
    with pytest.raises(
        ValueError,
        match="score must be between",
    ):
        HorizonSignal(
            horizon=TradingHorizon.SWING,
            action=Action.BUY,
            score=101.0,
            confidence=80.0,
        )


def test_invalid_weights_raise():
    with pytest.raises(
        ValueError,
        match="non-negative",
    ):
        MultiHorizonDecisionEngine(
            weights={
                TradingHorizon.SWING: -1.0,
            }
        )


def test_invalid_threshold_raises():
    with pytest.raises(
        ValueError,
        match="between 0 and 1",
    ):
        MultiHorizonDecisionEngine(
            decision_threshold=2.0,
        )
