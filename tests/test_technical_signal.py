from atlas.adapters.market_data import MarketData
from atlas.intelligence.technical_signal import generate_technical_signal
from atlas.models.action import Action


def snapshot(**overrides) -> MarketData:
    values = dict(
        symbol="TEST.OL",
        price=12.0,
        previous_close=11.8,
        change_percent=1.69,
        ma20=10.0,
        ma50=9.0,
        volume=2000.0,
        average_volume=1000.0,
        volume_ratio=2.0,
        currency="NOK",
    )
    values.update(overrides)
    return MarketData(**values)


def test_bullish_trend_generates_buy_and_volume_boost() -> None:
    signal = generate_technical_signal(snapshot())
    assert signal.action is Action.BUY
    assert signal.confidence == 78
    assert "price_above_ma20" in signal.reasons
    assert "ma20_above_ma50" in signal.reasons
    assert "volume_2.00x_average" in signal.reasons


def test_bearish_trend_generates_sell() -> None:
    signal = generate_technical_signal(
        snapshot(price=7.0, ma20=8.0, ma50=9.0, volume_ratio=2.0)
    )
    assert signal.action is Action.SELL
    assert signal.confidence == 78


def test_mixed_trend_generates_hold() -> None:
    signal = generate_technical_signal(
        snapshot(price=10.0, ma20=11.0, ma50=9.0, volume_ratio=2.0)
    )
    assert signal.action is Action.HOLD
    assert signal.confidence == 55


def test_low_volume_reduces_confidence_but_not_direction() -> None:
    signal = generate_technical_signal(snapshot(volume_ratio=0.55))
    assert signal.action is Action.BUY
    assert signal.confidence == 65
    assert "low_volume_0.55x_average" in signal.reasons
