from datetime import datetime, timedelta

from atlas.core.config import AtlasConfig
from atlas.database.analysis_snapshot_repository import AnalysisSnapshotRepository
from atlas.database.connection import Database
from atlas.models.analysis_snapshot import AnalysisSnapshot
from atlas.services.dashboard_data_service import DashboardDataService
from atlas.trading.trade_record import TradeRecord


class _FakeIntelligenceSources:
    def get(self, symbol, **kwargs):
        return []


def _service_with_snapshot(tmp_path, symbol="BTC-USD"):
    config = AtlasConfig(
        database_path=str(tmp_path / "atlas.db"),
        agent_performance_storage=str(tmp_path / "agent_performance.json"),
    )
    service = DashboardDataService(
        config=config,
        intelligence_sources=_FakeIntelligenceSources(),
    )
    repository = AnalysisSnapshotRepository(Database(config.database_path))
    repository.save(
        AnalysisSnapshot(
            database_id=None,
            symbol=symbol,
            timestamp=datetime.now(),
            provider="ollama",
            model="qwen3:4b",
            results=[
                {
                    "analyst": "Technical Analyst",
                    "symbol": symbol,
                    "action": "HOLD",
                    "confidence": 70.0,
                    "evidence": 70.0,
                    "reasoning": ["Test snapshot."],
                }
            ],
            decision={
                "symbol": symbol,
                "action": "HOLD",
                "confidence": 70.0,
                "evidence": 70.0,
                "analysts": ["Technical Analyst"],
                "agent_weights": {"Technical Analyst": 1.0},
                "dominant_action": "HOLD",
                "dominant_weight": 1.0,
                "action_support_analyst": "Technical Analyst",
                "action_support_action": "HOLD",
                "action_support_weight": 1.0,
                "opposing_analysts": [],
                "adaptive_override": False,
                "decision_margin": 100.0,
                "robustness": 70.0,
                "robustness_level": "STRONG",
                "reasoning": ["Test snapshot."],
            },
            intelligence={
                "symbol": symbol,
                "action": "HOLD",
                "evidence": 70.0,
                "confidence": 70.0,
                "buy_count": 0,
                "hold_count": 1,
                "sell_count": 0,
                "agreement": 100.0,
                "conflict": False,
                "weighted_buy": 0.0,
                "weighted_hold": 100.0,
                "weighted_sell": 0.0,
                "weighted_agreement": 100.0,
                "weighted_conflict": False,
                "analysts": ["Technical Analyst"],
                "reasoning": ["Test snapshot."],
            },
        )
    )
    return service


def test_dashboard_trade_chart_is_period_scoped_and_symbol_filtered(tmp_path, monkeypatch):
    service = _service_with_snapshot(tmp_path)
    now = datetime(2026, 9, 11, 12, 0, 0)
    trades = [
        TradeRecord("BTC-USD", "BUY", 1.0, 100000.0, 100000.0, 0.0, now - timedelta(hours=2), "entry"),
        TradeRecord("ETH-USD", "BUY", 1.0, 4000.0, 4000.0, 0.0, now - timedelta(hours=1), "other asset"),
        TradeRecord("BTC-USD", "SELL", 1.0, 101000.0, 101000.0, 1000.0, now - timedelta(days=2), "outside period"),
    ]
    monkeypatch.setattr(service.trading, "history", lambda: [trade.as_dict() for trade in trades])

    data = service.get_dashboard_data(
        selected_symbol="BTC-USD",
        trade_history_period="1d",
        now=now,
    )

    assert data["trade_chart"]["period"] == "1d"
    assert data["trade_chart"]["symbol"] == "BTC-USD"
    assert len(data["trade_chart"]["trades"]) == 2
    assert [trade["symbol"] for trade in data["trade_chart"]["trades"]] == ["BTC-USD", "ETH-USD"]
    assert data["trade_chart"]["markers"] == [
        {
            "symbol": "BTC-USD",
            "action": "BUY",
            "price_usd": 100000.0,
            "timestamp": (now - timedelta(hours=2)).isoformat(timespec="seconds"),
        }
    ]
