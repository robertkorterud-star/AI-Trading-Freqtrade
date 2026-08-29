import pytest

from atlas.algorithms.base import AlgorithmSignal
from atlas.algorithms.fusion import FusionResult, SignalFusion
from atlas.models.action import Action


def signal(
    algorithm,
    action,
    score=75.0,
    confidence=70.0,
    symbol="BTC-USD",
    timeframe="5m",
):
    return AlgorithmSignal(
        algorithm=algorithm,
        symbol=symbol,
        timeframe=timeframe,
        action=action,
        score=score,
        confidence=confidence,
        expected_edge=None,
        reasoning=[f"{algorithm} test signal"],
    )


def test_fusion_returns_buy_for_buy_majority():
    fusion = SignalFusion()

    result = fusion.combine(
        [
            signal("momentum", Action.BUY, 80.0),
            signal("mean_reversion", Action.BUY, 75.0),
            signal("breakout", Action.HOLD, 60.0),
        ]
    )

    assert isinstance(result, FusionResult)
    assert result.symbol == "BTC-USD"
    assert result.timeframe == "5m"
    assert result.action is Action.BUY
    assert result.agreement == pytest.approx(0.6667)
    assert result.confidence > 50.0
    assert len(result.signals) == 3
    assert result.reasoning


def test_fusion_returns_sell_for_sell_majority():
    fusion = SignalFusion()

    result = fusion.combine(
        [
            signal("momentum", Action.SELL, 80.0),
            signal("mean_reversion", Action.SELL, 75.0),
            signal("breakout", Action.HOLD, 60.0),
        ]
    )

    assert result.action is Action.SELL
    assert result.agreement == pytest.approx(0.6667)


def test_fusion_returns_hold_without_directional_consensus():
    fusion = SignalFusion()

    result = fusion.combine(
        [
            signal("momentum", Action.BUY),
            signal("mean_reversion", Action.SELL),
            signal("breakout", Action.HOLD),
        ]
    )

    assert result.action is Action.HOLD
    assert result.agreement == pytest.approx(0.3333)


def test_fusion_requires_signals():
    fusion = SignalFusion()

    with pytest.raises(
        ValueError,
        match="at least one algorithm signal",
    ):
        fusion.combine([])


def test_fusion_requires_same_symbol():
    fusion = SignalFusion()

    with pytest.raises(
        ValueError,
        match="same symbol",
    ):
        fusion.combine(
            [
                signal("momentum", Action.BUY),
                signal(
                    "breakout",
                    Action.BUY,
                    symbol="ETH-USD",
                ),
            ]
        )


def test_fusion_requires_same_timeframe():
    fusion = SignalFusion()

    with pytest.raises(
        ValueError,
        match="same timeframe",
    ):
        fusion.combine(
            [
                signal("momentum", Action.BUY),
                signal(
                    "breakout",
                    Action.BUY,
                    timeframe="15m",
                ),
            ]
        )


def test_fusion_supports_custom_thresholds():
    fusion = SignalFusion(
        buy_threshold=0.75,
        sell_threshold=0.75,
    )

    result = fusion.combine(
        [
            signal("momentum", Action.BUY),
            signal("mean_reversion", Action.BUY),
            signal("breakout", Action.HOLD),
        ]
    )

    assert result.action is Action.HOLD


def test_fusion_rejects_invalid_threshold():
    with pytest.raises(
        ValueError,
        match="between 0 and 1",
    ):
        SignalFusion(buy_threshold=1.5)


def test_fusion_preserves_signal_order():
    fusion = SignalFusion()

    first = signal("momentum", Action.BUY)
    second = signal("mean_reversion", Action.HOLD)
    third = signal("breakout", Action.SELL)

    result = fusion.combine(
        [first, second, third]
    )

    assert result.signals == (
        first,
        second,
        third,
    )
