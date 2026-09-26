from datetime import datetime

from atlas.database.connection import Database
from atlas.database.paper_account_state_repository import PaperAccountStateRepository
from atlas.database.schema import initialize_database


def test_paper_account_state_repository_returns_no_peak_when_empty(tmp_path):
    database = Database(tmp_path / "atlas.db")
    initialize_database(database)

    repository = PaperAccountStateRepository(database)

    assert repository.get_peak_equity_nok() is None


def test_paper_account_state_repository_round_trip_peak_equity(tmp_path):
    database = Database(tmp_path / "atlas.db")
    initialize_database(database)

    repository = PaperAccountStateRepository(database)

    repository.set_peak_equity_nok(10000.0)

    assert repository.get_peak_equity_nok() == 10000.0


def test_paper_account_state_repository_updates_peak_equity(tmp_path):
    database = Database(tmp_path / "atlas.db")
    initialize_database(database)

    repository = PaperAccountStateRepository(database)

    repository.set_peak_equity_nok(10000.0)
    repository.set_peak_equity_nok(12000.0)

    assert repository.get_peak_equity_nok() == 12000.0



def test_paper_account_state_repository_round_trip_position_peak_price(tmp_path):
    database = Database(tmp_path / "atlas.db")
    initialize_database(database)

    repository = PaperAccountStateRepository(database)

    repository.set_position_peak_price_usd("BTC-USD", 120.0)

    assert repository.get_position_peak_price_usd("BTC-USD") == 120.0
    assert repository.get_position_peak_price_usd("ETH-USD") is None



def test_paper_account_state_repository_deletes_position_peak_price(tmp_path):
    database = Database(tmp_path / "atlas.db")
    initialize_database(database)

    repository = PaperAccountStateRepository(database)

    repository.set_position_peak_price_usd("BTC-USD", 120.0)
    repository.delete_position_peak_price_usd("BTC-USD")

    assert repository.get_position_peak_price_usd("BTC-USD") is None



def test_paper_account_state_repository_round_trip_trade_replay_after(tmp_path):
    database = Database(tmp_path / "atlas.db")
    initialize_database(database)

    repository = PaperAccountStateRepository(database)
    boundary = datetime(2026, 9, 14, 7, 27, 24, 123456)

    repository.set_trade_replay_after(boundary)

    assert repository.get_trade_replay_after() == boundary


def test_initialize_database_migrates_trade_replay_after_column(tmp_path):
    database = Database(tmp_path / "atlas.db")

    with database.connect() as connection:
        connection.execute(
            """
            CREATE TABLE paper_account_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                peak_equity_nok REAL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO paper_account_state (id, peak_equity_nok)
            VALUES (1, 12000.0)
            """
        )
        connection.commit()

    initialize_database(database)

    repository = PaperAccountStateRepository(database)

    assert repository.get_peak_equity_nok() == 12000.0
    assert repository.get_trade_replay_after() is None
