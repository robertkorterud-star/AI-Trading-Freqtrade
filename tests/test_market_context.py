from datetime import datetime, timezone

from atlas.market.asset_type import AssetType
from atlas.market.market_context import MarketContextService


def timestamp_utc(hour, minute):
    return datetime(
        2026,
        9,
        14,
        hour,
        minute,
        tzinfo=timezone.utc,
    ).timestamp()


def test_us_equity_premarket_context():
    context = MarketContextService.build(
        asset_type=AssetType.STOCK,
        timestamp=timestamp_utc(13, 0),
        change_percent=1.0,
        volume_ratio=1.8,
    )

    assert context.session == "PREMARKET"
    assert context.volatility_level == "NORMAL"
    assert context.liquidity_level == "HIGH"


def test_us_equity_power_hour_context():
    context = MarketContextService.build(
        asset_type=AssetType.STOCK,
        timestamp=timestamp_utc(19, 30),
        change_percent=5.0,
        volume_ratio=3.0,
    )

    assert context.session == "POWER_HOUR"
    assert context.volatility_level == "EXTREME"
    assert context.liquidity_level == "VERY_HIGH"


def test_crypto_has_continuous_session_context():
    context = MarketContextService.build(
        asset_type=AssetType.CRYPTO,
        timestamp=timestamp_utc(3, 0),
        change_percent=0.5,
        volume_ratio=0.5,
    )

    assert context.session == "CRYPTO_24_7"
    assert context.volatility_level == "LOW"
    assert context.liquidity_level == "LOW"


def test_context_is_not_a_trading_decision():
    context = MarketContextService.build(
        asset_type=AssetType.STOCK,
        timestamp=timestamp_utc(14, 0),
        change_percent=2.5,
        volume_ratio=2.0,
    )

    assert context.session
    assert context.volatility_level == "HIGH"
    assert context.liquidity_level == "HIGH"


def test_us_equity_weekend_is_closed_even_during_session_hours():
    saturday = datetime(
        2026,
        9,
        19,
        14,
        0,
        tzinfo=timezone.utc,
    ).timestamp()

    assert (
        MarketContextService.session(
            AssetType.STOCK,
            saturday,
        )
        == "CLOSED"
    )


def test_crypto_remains_open_on_weekends():
    saturday = datetime(
        2026,
        9,
        19,
        14,
        0,
        tzinfo=timezone.utc,
    ).timestamp()

    assert (
        MarketContextService.session(
            AssetType.CRYPTO,
            saturday,
        )
        == "CRYPTO_24_7"
    )


def test_crypto_freshness_marks_old_data_stale_while_market_is_open():
    now = datetime(
        2026,
        9,
        24,
        16,
        0,
        tzinfo=timezone.utc,
    ).timestamp()
    latest_candle = datetime(
        2026,
        9,
        24,
        15,
        50,
        tzinfo=timezone.utc,
    ).timestamp()

    assert (
        MarketContextService.data_freshness(
            asset_type=AssetType.CRYPTO,
            now_timestamp=now,
            latest_candle_timestamp=latest_candle,
            expected_interval_seconds=60,
        )
        == "STALE"
    )


def test_closed_us_equity_session_does_not_mark_last_candle_stale():
    saturday = datetime(
        2026,
        9,
        19,
        14,
        0,
        tzinfo=timezone.utc,
    ).timestamp()
    friday_close = datetime(
        2026,
        9,
        18,
        20,
        0,
        tzinfo=timezone.utc,
    ).timestamp()

    assert (
        MarketContextService.data_freshness(
            asset_type=AssetType.STOCK,
            now_timestamp=saturday,
            latest_candle_timestamp=friday_close,
            expected_interval_seconds=60,
        )
        == "NOT_APPLICABLE"
    )
