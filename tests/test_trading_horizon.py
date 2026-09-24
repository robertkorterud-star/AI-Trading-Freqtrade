from atlas.market.trading_horizon import (
    TradingHorizon,
    timeframes_for_horizon,
)


def test_trading_horizons_cover_professional_atlas_contexts():
    assert tuple(TradingHorizon) == (
        TradingHorizon.LONG_TERM,
        TradingHorizon.SWING,
        TradingHorizon.SHORT_TERM,
        TradingHorizon.DAY_TRADE,
        TradingHorizon.SCALP,
    )


def test_trading_horizon_timeframes_are_explicit_context():
    assert timeframes_for_horizon(TradingHorizon.LONG_TERM) == (
        "1wk",
        "1d",
    )
    assert timeframes_for_horizon(TradingHorizon.SWING) == (
        "1d",
        "1h",
    )
    assert timeframes_for_horizon(TradingHorizon.SHORT_TERM) == (
        "1d",
        "1h",
        "15m",
    )
    assert timeframes_for_horizon(TradingHorizon.DAY_TRADE) == (
        "1h",
        "15m",
        "5m",
    )
    assert timeframes_for_horizon(TradingHorizon.SCALP) == (
        "15m",
        "5m",
        "1m",
    )


def test_timeframe_contract_does_not_expose_trade_direction():
    timeframes = timeframes_for_horizon(TradingHorizon.DAY_TRADE)

    assert all(
        direction not in timeframes
        for direction in ("BUY", "SELL", "LONG", "SHORT")
    )
