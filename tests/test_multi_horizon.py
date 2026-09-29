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


def test_horizon_signal_from_fused_algorithm_evidence():
    """Fused algorithm evidence can be normalized into one horizon signal."""
    from types import SimpleNamespace

    from atlas.algorithms.multi_horizon import HorizonSignal
    from atlas.market.trading_horizon import TradingHorizon
    from atlas.models.action import Action

    fused = SimpleNamespace(
        action=Action.BUY,
        score=82.5,
        confidence=74.0,
    )

    signal = HorizonSignal.from_fusion(
        TradingHorizon.SWING,
        fused,
    )

    assert signal == HorizonSignal(
        horizon=TradingHorizon.SWING,
        action=Action.BUY,
        score=82.5,
        confidence=74.0,
    )


def test_horizon_signal_from_candles_uses_existing_indicator_features():
    """Horizon evidence is derived from canonical OHLCV indicator features."""
    from atlas.algorithms.multi_horizon import HorizonSignal
    from atlas.market.trading_horizon import TradingHorizon
    from atlas.models.action import Action
    from atlas.trading.market_data import Candle

    candles = tuple(
        Candle(
            timestamp=float(index + 1),
            open=100.0 + index,
            high=101.0 + index,
            low=99.0 + index,
            close=100.0 + index,
            volume=1_000.0,
        )
        for index in range(60)
    )

    signal = HorizonSignal.from_candles(
        TradingHorizon.SWING,
        candles,
    )

    assert signal.horizon is TradingHorizon.SWING
    assert signal.action is Action.BUY
    assert 0.0 <= signal.score <= 100.0
    assert 0.0 <= signal.confidence <= 100.0


def test_horizon_signal_from_candles_generates_bearish_evidence():
    from atlas.algorithms.multi_horizon import HorizonSignal
    from atlas.market.trading_horizon import TradingHorizon
    from atlas.models.action import Action
    from atlas.trading.market_data import Candle

    candles = tuple(
        Candle(
            timestamp=float(index + 1),
            open=160.0 - index,
            high=161.0 - index,
            low=159.0 - index,
            close=160.0 - index,
            volume=1_000.0,
        )
        for index in range(60)
    )

    signal = HorizonSignal.from_candles(
        TradingHorizon.SWING,
        candles,
    )

    assert signal.action is Action.SELL
    assert signal.score < 50.0


def test_horizon_signal_from_insufficient_candles_is_neutral():
    from atlas.algorithms.multi_horizon import HorizonSignal
    from atlas.market.trading_horizon import TradingHorizon
    from atlas.models.action import Action
    from atlas.trading.market_data import Candle

    candles = tuple(
        Candle(
            timestamp=float(index + 1),
            open=100.0,
            high=101.0,
            low=99.0,
            close=100.0,
            volume=1_000.0,
        )
        for index in range(10)
    )

    signal = HorizonSignal.from_candles(
        TradingHorizon.SWING,
        candles,
    )

    assert signal.action is Action.HOLD
    assert signal.score == 50.0
    assert signal.confidence == 50.0
