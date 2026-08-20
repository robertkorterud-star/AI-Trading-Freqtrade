from atlas.intelligence.volume_confirmation import (
    VolumeConfirmation,
    confirm_volume,
)


def test_buy_extreme_volume_is_very_strong():

    result = confirm_volume(
        action="BUY",
        volume_level="EXTREME",
        volume_ratio=3.5,
    )

    assert isinstance(result, VolumeConfirmation)
    assert result.strength == "VERY_STRONG"
    assert "BUY" in result.interpretation
    assert "3.50x" in result.interpretation


def test_buy_strong_volume_is_strong():

    result = confirm_volume(
        action="BUY",
        volume_level="STRONG",
        volume_ratio=2.0,
    )

    assert result.strength == "STRONG"
    assert "strong volume" in result.interpretation.lower()


def test_buy_normal_volume_is_normal():

    result = confirm_volume(
        action="BUY",
        volume_level="NORMAL",
        volume_ratio=1.0,
    )

    assert result.strength == "NORMAL"


def test_buy_low_volume_is_weak():

    result = confirm_volume(
        action="BUY",
        volume_level="LOW",
        volume_ratio=0.5,
    )

    assert result.strength == "WEAK"
    assert "weak" in result.interpretation.lower()


def test_sell_extreme_volume_is_very_strong():

    result = confirm_volume(
        action="SELL",
        volume_level="EXTREME",
        volume_ratio=3.5,
    )

    assert result.strength == "VERY_STRONG"
    assert "SELL" in result.interpretation


def test_sell_low_volume_is_weak():

    result = confirm_volume(
        action="SELL",
        volume_level="LOW",
        volume_ratio=0.6,
    )

    assert result.strength == "WEAK"


def test_hold_extreme_volume_means_high_activity():

    result = confirm_volume(
        action="HOLD",
        volume_level="EXTREME",
        volume_ratio=4.0,
    )

    assert result.strength == "HIGH_ACTIVITY"
    assert "direction remains unclear" in result.interpretation


def test_hold_normal_volume_is_normal():

    result = confirm_volume(
        action="HOLD",
        volume_level="NORMAL",
        volume_ratio=1.0,
    )

    assert result.strength == "NORMAL"


def test_hold_low_volume_means_low_activity():

    result = confirm_volume(
        action="HOLD",
        volume_level="LOW",
        volume_ratio=0.5,
    )

    assert result.strength == "LOW_ACTIVITY"


def test_unknown_volume_is_unknown():

    result = confirm_volume(
        action="BUY",
        volume_level="UNKNOWN",
        volume_ratio=0.0,
    )

    assert result.strength == "UNKNOWN"
    assert "unavailable" in result.interpretation.lower()


def test_volume_never_creates_direction():

    result = confirm_volume(
        action="HOLD",
        volume_level="EXTREME",
        volume_ratio=5.0,
    )

    assert result.action == "HOLD"
    assert result.strength == "HIGH_ACTIVITY"
    assert "BUY" not in result.interpretation
    assert "SELL" not in result.interpretation
