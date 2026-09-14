from datetime import datetime, timedelta

from atlas.database.analysis_snapshot_repository import AnalysisSnapshotRepository
from atlas.database.connection import Database
from atlas.models.analysis_snapshot import AnalysisSnapshot
from atlas.services.dashboard_data_service import DashboardDataService
from atlas.core.config import AtlasConfig
from atlas.trading.trade_record import TradeRecord


class _FakeIntelligenceSources:
    def __init__(self, items=None):
        self.items = items or []

    def get(self, symbol, **kwargs):
        return list(self.items)


def test_dashboard_news_prioritizes_distinct_sources(tmp_path):
    config = AtlasConfig(
        database_path=str(tmp_path / "atlas.db"),
        agent_performance_storage=str(tmp_path / "agent_performance.json"),
    )
    service = DashboardDataService(
        config=config,
        intelligence_sources=_FakeIntelligenceSources(
            [
                {"source": "YouTube", "title": f"Video {index}"}
                for index in range(6)
            ]
            + [
                {"source": "Finnhub", "title": "BTC market update"},
                {"source": "Reuters", "title": "Markets update"},
                {"source": "Yahoo Finance", "title": "Bitcoin update"},
            ]
        ),
    )

    news = service._get_latest_news("BTC-USD")

    assert [article["source"] for article in news[:4]] == [
        "YouTube",
        "Finnhub",
        "Reuters",
        "Yahoo Finance",
    ]
    assert len({article["source"] for article in news[:5]}) > 1


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
            timestamp=__import__("datetime").datetime.now(),
            provider="ollama",
            model="qwen3:4b",
            results=[
                {
                    "analyst": "Technical Analyst",
                    "symbol": symbol,
                    "action": "BUY",
                    "confidence": 90.0,
                    "evidence": 90.0,
                    "reasoning": ["Strong technical evidence."],
                },
                {
                    "analyst": "Company Analyst",
                    "symbol": symbol,
                    "action": "BUY",
                    "confidence": 80.0,
                    "evidence": 80.0,
                    "reasoning": ["Positive company evidence."],
                },
            ],
            decision={
                "symbol": symbol,
                "action": "BUY",
                "confidence": 85.0,
                "evidence": 85.0,
                "analysts": ["Technical Analyst", "Company Analyst"],
                "agent_weights": {
                    "Technical Analyst": 0.5,
                    "Company Analyst": 0.5,
                },
                "dominant_action": "BUY",
                "dominant_weight": 1.0,
                "action_support_analyst": "Technical Analyst",
                "action_support_action": "BUY",
                "action_support_weight": 0.5,
                "opposing_analysts": [],
                "adaptive_override": False,
                "decision_margin": 100.0,
                "robustness": 85.0,
                "robustness_level": "STRONG",
                "reasoning": ["Strong analyst agreement."],
            },
            intelligence={
                "symbol": symbol,
                "action": "BUY",
                "evidence": 85.0,
                "confidence": 85.0,
                "buy_count": 2,
                "hold_count": 0,
                "sell_count": 0,
                "agreement": 100.0,
                "conflict": False,
                "weighted_buy": 100.0,
                "weighted_hold": 0.0,
                "weighted_sell": 0.0,
                "weighted_agreement": 100.0,
                "weighted_conflict": False,
                "analysts": ["Technical Analyst", "Company Analyst"],
                "reasoning": ["Strong analyst agreement."],
            },
        )
    )
    return service


def test_dashboard_reports_paper_trading_status(tmp_path):
    service = _service_with_snapshot(tmp_path)
    service.settings.set_trading_mode("paper")

    data = service.get_dashboard_data(selected_symbol="BTC-USD")

    assert data["status"] == "Running"
    assert data["trading"]["mode"] == "paper"
    assert data["trading"]["paper_trading"] is True
    assert data["trading"]["live_orders"] is False
    assert data["trading"]["virtual_capital_nok"] == 5000.0


def test_dashboard_waits_for_canonical_runtime_snapshot(tmp_path):
    config = AtlasConfig(
        database_path=str(tmp_path / "atlas.db"),
        agent_performance_storage=str(tmp_path / "agent_performance.json"),
    )
    service = DashboardDataService(
        config=config,
        intelligence_sources=_FakeIntelligenceSources(),
    )

    data = service.get_dashboard_data(selected_symbol="BTC-USD")

    assert data["status"] == "Waiting for ATLAS runtime"
    assert data["decision"] is None
    assert data["intelligence"] is None


def test_dashboard_keeps_selected_market_visible_while_waiting_for_runtime(tmp_path, monkeypatch):
    config = AtlasConfig(
        database_path=str(tmp_path / "atlas.db"),
        agent_performance_storage=str(tmp_path / "agent_performance.json"),
    )
    service = DashboardDataService(
        config=config,
        intelligence_sources=_FakeIntelligenceSources(),
    )

    class _FakeMarket:
        price = 1.35
        change_percent = 2.5

    monkeypatch.setattr(service.market_data, "get", lambda symbol: _FakeMarket())

    data = service.get_dashboard_data(selected_symbol="XRP-USD")

    selected = next(item for item in data["market"] if item["symbol"] == "XRP-USD")

    assert selected["is_selected"] is True
    assert selected["price_usd"] == 1.35
    assert selected["change"] == 2.5
    assert selected["decision"] == "WAITING"
    assert selected["confidence"] is None
    assert selected["evidence"] is None
    assert data["status"] == "Waiting for ATLAS runtime"
    assert data["decision"] is None
    assert data["intelligence"] is None


def test_dashboard_reports_agent_performance(tmp_path):
    service = _service_with_snapshot(tmp_path)
    data = service.get_dashboard_data(selected_symbol="BTC-USD")

    performance = data["agent_performance"]
    assert isinstance(performance["history"], list)
    assert isinstance(performance["weights"], dict)


def test_dashboard_news_analyst_uses_selected_ai_provider(tmp_path):
    service = _service_with_snapshot(tmp_path)
    service.settings.set_ai_provider("ollama")

    news_analyst = next(
        agent for agent in service.registry.get_all() if agent.name == "News Analyst"
    )

    assert news_analyst.config is service.settings.get_config()
    assert news_analyst.config.ai_provider == "ollama"


def test_dashboard_reports_canonical_intelligence_summary(tmp_path):
    service = _service_with_snapshot(tmp_path, symbol="NVDA")
    data = service.get_dashboard_data(selected_symbol="NVDA")
    intelligence = data["intelligence"]

    assert intelligence.symbol == "NVDA"
    assert intelligence.action.value == "BUY"
    assert intelligence.agreement == 100.0
    assert intelligence.buy_count == 2
    assert intelligence.hold_count == 0
    assert intelligence.sell_count == 0
    assert intelligence.conflict is False
    assert intelligence.analysts
    assert intelligence.reasoning


def test_dashboard_decision_and_explanation_come_from_snapshot(tmp_path):
    from atlas.models.decision_explanation import DecisionExplanation

    service = _service_with_snapshot(tmp_path)
    data = service.get_dashboard_data(selected_symbol="BTC-USD")

    decision = data["decision"]
    explanation = data["decision_explanation"]
    influence = data["decision_influence"]

    assert decision.agent_weights
    assert "Technical Analyst" in decision.agent_weights
    assert "Company Analyst" in decision.agent_weights
    assert sum(decision.agent_weights.values()) == 1.0
    assert isinstance(explanation, DecisionExplanation)
    assert explanation.action == decision.action
    assert explanation.confidence == decision.confidence
    assert influence["action_support_analyst"] == decision.action_support_analyst
    assert influence["action_support_action"] == decision.action_support_action.value


def test_dashboard_reports_market_scan_candidates(monkeypatch, tmp_path):
    service = _service_with_snapshot(tmp_path)

    monkeypatch.setattr(
        service,
        "market_scan",
        lambda: [
            {
                "symbol": "NVDA",
                "discovery_score": 92.5,
                "decision": "BUY",
                "confidence": 88.0,
                "selected": True,
            },
            {
                "symbol": "BTC-USD",
                "discovery_score": 84.0,
                "decision": "HOLD",
                "confidence": 78.0,
                "selected": False,
            },
        ],
    )

    data = service.get_dashboard_data(selected_symbol="BTC-USD")

    assert len(data["market_scan"]) == 2
    assert data["market_scan"][0]["symbol"] == "NVDA"
    assert data["market_scan"][0]["selected"] is True
    assert data["market_scan"][0]["discovery_score"] == 92.5
    assert data["market_scan"][0]["decision"] == "BUY"


def test_dashboard_exposes_filtered_trade_history_and_markers(tmp_path, monkeypatch):
    service = _service_with_snapshot(tmp_path)
    now = datetime(2026, 9, 11, 12, 0, 0)
    trades = [
        TradeRecord("XRP-USD", "BUY", 1.0, 1.34, 1.34, 0.0, now - timedelta(hours=2), "test"),
        TradeRecord("XRP-USD", "SELL", 1.0, 1.39, 1.39, 0.05, now - timedelta(hours=1), "test"),
        TradeRecord("BTC-USD", "BUY", 1.0, 100000, 100000, 0.0, now - timedelta(days=10), "old"),
    ]
    monkeypatch.setattr(service.trading, "history", lambda: [trade.as_dict() for trade in trades])

    data = service.get_dashboard_data(selected_symbol="BTC-USD", trade_history_period="1d", now=now)

    assert data["trade_history_period"] == "1d"
    assert len(data["trade_history"]) == 2
    assert [item["action"] for item in data["trade_history"]] == ["BUY", "SELL"]
    assert data["trade_history_markers"] == [
        {
            "symbol": "XRP-USD",
            "action": "BUY",
            "price_usd": 1.34,
            "timestamp": (now - timedelta(hours=2)).isoformat(timespec="seconds"),
        },
        {
            "symbol": "XRP-USD",
            "action": "SELL",
            "price_usd": 1.39,
            "timestamp": (now - timedelta(hours=1)).isoformat(timespec="seconds"),
        },
    ]
