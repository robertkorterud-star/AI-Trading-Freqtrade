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
