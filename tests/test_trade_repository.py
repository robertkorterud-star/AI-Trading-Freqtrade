from datetime import datetime

from atlas.database.connection import Database
from atlas.database.schema import initialize_database
from atlas.database.trade_repository import TradeRepository
from atlas.trading.trade_record import TradeRecord


def test_trade_repository_returns_empty_history_when_empty(tmp_path):
    database = Database(tmp_path / "atlas.db")
    initialize_database(database)

    repository = TradeRepository(database)

    assert repository.load() == []


def test_trade_repository_round_trip(tmp_path):
    database = Database(tmp_path / "atlas.db")
    initialize_database(database)

    repository = TradeRepository(database)

    trade = TradeRecord(
        symbol="BTC-USD",
        action="BUY",
        quantity=0.00161943,
        price_usd=65000.0,
        amount_nok=1000.0,
        realized_pnl_nok=0.0,
        timestamp=datetime(2026, 9, 10, 8, 30, 0),
        reason="AI BUY approved.",
    )

    repository.save(trade)

    restored = repository.load()

    assert len(restored) == 1
    assert restored[0].symbol == "BTC-USD"
    assert restored[0].action == "BUY"
    assert restored[0].quantity == 0.00161943
    assert restored[0].price_usd == 65000.0
    assert restored[0].amount_nok == 1000.0
    assert restored[0].realized_pnl_nok == 0.0
    assert restored[0].timestamp == datetime(2026, 9, 10, 8, 30, 0)
    assert restored[0].reason == "AI BUY approved."


def test_trade_repository_preserves_chronological_order(tmp_path):
    database = Database(tmp_path / "atlas.db")
    initialize_database(database)

    repository = TradeRepository(database)

    first = TradeRecord(
        symbol="BTC-USD",
        action="BUY",
        quantity=0.001,
        price_usd=65000.0,
        amount_nok=1000.0,
        realized_pnl_nok=0.0,
        timestamp=datetime(2026, 9, 10, 8, 0, 0),
    )

    second = TradeRecord(
        symbol="BTC-USD",
        action="SELL",
        quantity=0.001,
        price_usd=70000.0,
        amount_nok=1076.92,
        realized_pnl_nok=76.92,
        timestamp=datetime(2026, 9, 10, 9, 0, 0),
    )

    repository.save(first)
    repository.save(second)

    restored = repository.load()

    assert [trade.action for trade in restored] == ["BUY", "SELL"]


def test_trade_repository_clear(tmp_path):
    database = Database(tmp_path / "atlas.db")
    initialize_database(database)

    repository = TradeRepository(database)

    trade = TradeRecord(
        symbol="BTC-USD",
        action="BUY",
        quantity=0.001,
        price_usd=65000.0,
        amount_nok=1000.0,
        realized_pnl_nok=0.0,
        timestamp=datetime(2026, 9, 10, 8, 0, 0),
    )

    repository.save(trade)
    assert len(repository.load()) == 1

    repository.clear()

    assert repository.load() == []
