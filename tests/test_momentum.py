from atlas.algorithms.momentum import IntradayMomentumAlgorithm
from atlas.models.action import Action


def _candles(values):
    return [
        {"high": value + 1.0, "low": value - 1.0, "close": value}
        for value in values
    ]


def test_momentum_uses_indicator_confirmation_for_bullish_trend():
    candles = _candles([100.0 + index for index in range(80)])
    signal = IntradayMomentumAlgorithm().generate_signal("TEST", candles)

    assert signal.action is Action.BUY
    assert signal.confidence > 50.0
    assert any("RSI" in reason for reason in signal.reasoning)
    assert any("MACD" in reason for reason in signal.reasoning)
    assert any("EMA" in reason for reason in signal.reasoning)
    assert any("ADX" in reason for reason in signal.reasoning)


def test_momentum_uses_indicator_confirmation_for_bearish_trend():
    candles = _candles([200.0 - index for index in range(80)])
    signal = IntradayMomentumAlgorithm().generate_signal("TEST", candles)

    assert signal.action is Action.SELL
    assert signal.confidence > 50.0
    assert any("RSI" in reason for reason in signal.reasoning)
    assert any("MACD" in reason for reason in signal.reasoning)
    assert any("EMA" in reason for reason in signal.reasoning)
    assert any("ADX" in reason for reason in signal.reasoning)
