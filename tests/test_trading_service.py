from atlas.trading.trading_service import TradingService


def test_trading_service_records_buy():

    trading = TradingService()

    trading.record_buy(
        symbol="BTC-USD",
        quantity=0.00161943,
        price_usd=65000,
        amount_nok=1000,
        reason="AI BUY approved.",
    )

    history = trading.history()

    assert len(history) == 1
    assert history[0]["symbol"] == "BTC-USD"
    assert history[0]["action"] == "BUY"
    assert history[0]["amount_nok"] == 1000
    assert history[0]["realized_pnl_nok"] == 0.0


def test_trading_service_records_sell():

    trading = TradingService()

    trading.record_sell(
        symbol="BTC-USD",
        quantity=0.00161943,
        price_usd=70000,
        amount_nok=1076.92,
        realized_pnl_nok=76.92,
        reason="AI SELL approved.",
    )

    history = trading.history()

    assert len(history) == 1
    assert history[0]["action"] == "SELL"
    assert history[0]["amount_nok"] == 1076.92
    assert history[0]["realized_pnl_nok"] == 76.92


def test_trading_service_returns_newest_trade_first():

    trading = TradingService()

    trading.record_buy(
        symbol="BTC-USD",
        quantity=0.00161943,
        price_usd=65000,
        amount_nok=1000,
    )

    trading.record_sell(
        symbol="BTC-USD",
        quantity=0.00161943,
        price_usd=70000,
        amount_nok=1076.92,
        realized_pnl_nok=76.92,
    )

    history = trading.history()

    assert len(history) == 2
    assert history[0]["action"] == "SELL"
    assert history[1]["action"] == "BUY"


def test_trading_service_clear():

    trading = TradingService()

    trading.record_buy(
        symbol="BTC-USD",
        quantity=0.001,
        price_usd=65000,
        amount_nok=1000,
    )

    assert trading.count() == 1

    trading.clear()

    assert trading.count() == 0
    assert trading.history() == []
