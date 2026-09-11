from atlas.database.connection import Database
from atlas.database.event_repository import AtlasEventRepository
from atlas.database.schema import initialize_database


def test_atlas_event_repository_persists_and_reads_events(tmp_path):
    database = Database(str(tmp_path / "atlas.db"))
    initialize_database(database)
    repository = AtlasEventRepository(database)

    event_id = repository.publish(
        "TRADE_EXECUTED",
        {"symbol": "BTC-USD", "action": "BUY", "quantity": 1.5},
    )

    events = repository.after(event_id - 1)

    assert len(events) == 1
    assert events[0]["id"] == event_id
    assert events[0]["type"] == "TRADE_EXECUTED"
    assert events[0]["payload"]["symbol"] == "BTC-USD"
    assert events[0]["payload"]["quantity"] == 1.5


def test_atlas_event_repository_cursor_excludes_consumed_events(tmp_path):
    database = Database(str(tmp_path / "atlas.db"))
    initialize_database(database)
    repository = AtlasEventRepository(database)

    first = repository.publish("DECISION_READY", {"symbol": "NVDA"})
    second = repository.publish("TRADE_EXECUTED", {"symbol": "NVDA"})

    events = repository.after(first)

    assert [event["id"] for event in events] == [second]
