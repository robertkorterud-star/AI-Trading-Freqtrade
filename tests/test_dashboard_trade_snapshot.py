from datetime import datetime

from atlas.database.analysis_snapshot_repository import AnalysisSnapshotRepository
from atlas.database.connection import Database
from atlas.database.schema import initialize_database
from atlas.models.analysis_snapshot import AnalysisSnapshot
from atlas.services.dashboard_data_service import DashboardDataService
from atlas.services.trade_history_service import TradeHistoryService
from atlas.trading.trade_record import TradeRecord
from atlas.trading.trading_service import TradingService


def make_snapshot():
    return AnalysisSnapshot(
        database_id=None,
        symbol="BTC-USD",
        timestamp=datetime(2026, 9, 10, 8, 0, 0),
        provider="test",
        model="test-model",
        results=[
            {
                "analyst": "Technical Analyst",
                "symbol": "BTC-USD",
                "action": "BUY",
                "confidence": 90.0,
                "evidence": 85.0,
                "reasoning": ["Strong technical evidence."],
            }
        ],
        decision={
            "symbol": "BTC-USD",
            "action": "BUY",
            "confidence": 90.0,
            "evidence": 85.0,
            "reasoning": ["ATLAS approved the BUY."],
        },
        intelligence={
            "symbol": "BTC-USD",
            "action": "BUY",
            "evidence": 85.0,
            "confidence": 90.0,
            "buy_count": 1,
            "hold_count": 0,
            "sell_count": 0,
            "agreement": 100.0,
            "conflict": False,
            "reasoning": ["Analysts agree on BUY."],
        },
    )


def test_analysis_snapshot_repository_get_by_id(tmp_path):
    database = Database(tmp_path / "atlas.db")
    initialize_database(database)
    repository = AnalysisSnapshotRepository(database)

    snapshot = make_snapshot()
    snapshot_id = repository.save(snapshot)

    restored = repository.get_by_id(snapshot_id)

    assert restored is not None
    assert restored.database_id == snapshot_id
    assert restored.symbol == "BTC-USD"
    assert restored.decision["action"] == "BUY"


def test_dashboard_trade_history_attaches_canonical_snapshot(tmp_path):
    database = Database(tmp_path / "atlas.db")
    initialize_database(database)

    snapshot_repository = AnalysisSnapshotRepository(database)
    snapshot = make_snapshot()
    snapshot_id = snapshot_repository.save(snapshot)

    trading = TradingService()
    trading._history.append(
        TradeRecord(
            symbol="BTC-USD",
            action="BUY",
            quantity=0.001,
            price_usd=65000.0,
            amount_nok=1000.0,
            realized_pnl_nok=0.0,
            timestamp=datetime(2026, 9, 10, 8, 1, 0),
            reason="ExecutionAdapter: paper BUY",
            analysis_snapshot_id=snapshot_id,
        )
    )

    service = DashboardDataService.__new__(DashboardDataService)
    service.trading = trading
    service.trade_history = TradeHistoryService()
    service.snapshot_repository = snapshot_repository

    result = service._dashboard_trade_history(
        "all",
        now=datetime(2026, 9, 11, 8, 0, 0),
    )

    trade = result["trades"][0]
    assert trade["analysis_snapshot_id"] == snapshot_id
    assert trade["analysis_snapshot"]["database_id"] == snapshot_id
    assert trade["analysis_snapshot"]["decision"]["action"] == "BUY"
    assert trade["analysis_snapshot"]["intelligence"]["agreement"] == 100.0



def test_analysis_snapshot_repository_preserves_subsecond_latest_order(tmp_path):
    database = Database(tmp_path / "atlas.db")
    initialize_database(database)
    repository = AnalysisSnapshotRepository(database)

    newer = make_snapshot()
    newer.timestamp = datetime(2026, 9, 10, 8, 0, 0, 900000)
    repository.save(newer)

    older = make_snapshot()
    older.timestamp = datetime(2026, 9, 10, 8, 0, 0, 100000)
    repository.save(older)

    latest = repository.get_latest("BTC-USD")

    assert latest.database_id == newer.database_id
    assert latest.timestamp == newer.timestamp
