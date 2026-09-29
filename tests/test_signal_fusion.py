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


def test_fusion_does_not_treat_same_evidence_family_as_independent_consensus():
    fusion = SignalFusion()

    signals = [
        signal("intraday_momentum", Action.BUY, 80.0),
        signal("intraday_trend", Action.BUY, 80.0),
        signal("intraday_breakout", Action.BUY, 80.0),
        signal("positioning", Action.SELL, 80.0),
        signal("catalyst", Action.SELL, 80.0),
    ]

    signals = [
        AlgorithmSignal(
            algorithm=item.algorithm,
            symbol=item.symbol,
            timeframe=item.timeframe,
            action=item.action,
            score=item.score,
            confidence=item.confidence,
            expected_edge=item.expected_edge,
            reasoning=item.reasoning,
            evidence_family=family,
        )
        for item, family in zip(
            signals,
            (
                "price_direction",
                "price_direction",
                "price_direction",
                "positioning",
                "catalyst",
            ),
        )
    ]

    result = fusion.combine(signals)

    assert result.action is Action.SELL
    assert result.agreement == pytest.approx(2 / 3, abs=1e-4)
    assert result.signals == tuple(signals)


def test_fusion_same_family_disagreement_is_order_independent():
    fusion = SignalFusion()

    def family_signal(name, action):
        return AlgorithmSignal(
            algorithm=name,
            symbol="BTC-USD",
            timeframe="5m",
            action=action,
            score=80.0,
            confidence=80.0,
            evidence_family="price_direction",
        )

    first = fusion.combine(
        [
            family_signal("trend", Action.BUY),
            family_signal("breakout", Action.SELL),
        ]
    )
    reversed_result = fusion.combine(
        [
            family_signal("breakout", Action.SELL),
            family_signal("trend", Action.BUY),
        ]
    )

    assert first.action is Action.HOLD
    assert reversed_result.action is Action.HOLD
    assert first.score == reversed_result.score
    assert first.agreement == reversed_result.agreement


def test_algorithm_signal_serializes_evidence_family():
    item = AlgorithmSignal(
        algorithm="trend",
        symbol="BTC-USD",
        timeframe="5m",
        action=Action.BUY,
        score=80.0,
        confidence=80.0,
        evidence_family="price_direction",
    )

    assert item.as_dict()["evidence_family"] == "price_direction"
