from atlas.database.connection import Database
from atlas.database.schema import initialize_database
from atlas.database.trade_repository import TradeRepository
from atlas.trading.trading_service import TradingService


def test_trading_service_loads_persisted_history(tmp_path):
    database = Database(tmp_path / "atlas.db")
    initialize_database(database)

    repository = TradeRepository(database)

    first = TradingService(repository=repository)

    first.record_buy(
        symbol="BTC-USD",
        quantity=0.001,
        price_usd=65000,
        amount_nok=1000,
        reason="AI BUY approved.",
    )

    second = TradingService(repository=repository)

    assert second.count() == 1
    assert second.history()[0]["symbol"] == "BTC-USD"
    assert second.history()[0]["action"] == "BUY"
    assert second.history()[0]["amount_nok"] == 1000.0


def test_trading_service_clear_persists(tmp_path):
    database = Database(tmp_path / "atlas.db")
    initialize_database(database)

    repository = TradeRepository(database)
    trading = TradingService(repository=repository)

    trading.record_buy(
        symbol="BTC-USD",
        quantity=0.001,
        price_usd=65000,
        amount_nok=1000,
    )

    trading.clear()

    restored = TradingService(repository=repository)

    assert trading.count() == 0
    assert restored.count() == 0
