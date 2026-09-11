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


def test_trade_repository_round_trip_preserves_analysis_snapshot_id(tmp_path):
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
        timestamp=datetime(2026, 9, 10, 8, 30, 0),
        analysis_snapshot_id=42,
    )

    repository.save(trade)

    restored = repository.load()

    assert restored[0].analysis_snapshot_id == 42


def test_trade_repository_migrates_existing_paper_trades(tmp_path):
    database = Database(tmp_path / "atlas.db")

    with database.connect() as connection:
        connection.execute(
            """
            CREATE TABLE paper_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                action TEXT NOT NULL,
                quantity REAL NOT NULL,
                price_usd REAL NOT NULL,
                amount_nok REAL NOT NULL,
                realized_pnl_nok REAL NOT NULL,
                timestamp TEXT NOT NULL,
                reason TEXT NOT NULL DEFAULT ''
            )
            """
        )
        connection.execute(
            """
            INSERT INTO paper_trades (
                symbol, action, quantity, price_usd,
                amount_nok, realized_pnl_nok, timestamp, reason
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "BTC-USD",
                "BUY",
                0.001,
                65000.0,
                1000.0,
                0.0,
                "2026-09-10T08:30:00",
                "legacy",
            ),
        )
        connection.commit()

    initialize_database(database)

    restored = TradeRepository(database).load()

    assert len(restored) == 1
    assert restored[0].analysis_snapshot_id is None


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
