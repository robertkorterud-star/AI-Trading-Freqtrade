from atlas.services.dashboard_data_service import DashboardDataService


def test_dashboard_reports_paper_trading_status():

    service = DashboardDataService()

    service.settings.set_trading_mode("paper")

    data = service.get_dashboard_data(
        selected_symbol="BTC-USD"
    )

    assert data["status"] == "Running"
    assert data["trading"]["mode"] == "paper"
    assert data["trading"]["paper_trading"] is True
    assert data["trading"]["live_orders"] is False
    assert data["trading"]["virtual_capital_nok"] == 5000.0

def test_dashboard_reports_agent_performance():
    service = DashboardDataService()

    data = service.get_dashboard_data(
        selected_symbol="BTC-USD"
    )

    assert "agent_performance" in data

    performance = data["agent_performance"]

    assert "history" in performance
    assert "weights" in performance

    assert isinstance(
        performance["history"],
        list,
    )

    assert isinstance(
        performance["weights"],
        dict,
    )


def test_dashboard_news_analyst_uses_selected_ai_provider():

    service = DashboardDataService()

    service.settings.set_ai_provider("ollama")

    news_analyst = next(
        agent
        for agent in service.registry.get_all()
        if agent.name == "News Analyst"
    )

    assert news_analyst.config is service.settings.get_config()
    assert news_analyst.config.ai_provider == "ollama"


def test_dashboard_reports_intelligence_summary():

    service = DashboardDataService()

    data = service.get_dashboard_data(
        selected_symbol="NVDA"
    )

    intelligence = data["intelligence"]

    assert intelligence["symbol"] == "NVDA"

    assert intelligence["action"] in (
        "BUY",
        "HOLD",
        "SELL",
    )

    assert 0 <= intelligence["agreement"] <= 100
    assert 0 <= intelligence["evidence"] <= 100
    assert 0 <= intelligence["confidence"] <= 100

    assert intelligence["buy_count"] >= 0
    assert intelligence["hold_count"] >= 0
    assert intelligence["sell_count"] >= 0

    assert isinstance(
        intelligence["conflict"],
        bool,
    )

    assert intelligence["analysts"]
    assert intelligence["reasoning"]


def test_dashboard_decision_contains_agent_weights(
    monkeypatch,
    tmp_path,
):
    from atlas.core.config import AtlasConfig
    from atlas.models.action import Action
    from atlas.models.analysis_result import AnalysisResult

    config = AtlasConfig(
        agent_performance_storage=str(
            tmp_path / "agent_performance.json"
        )
    )

    service = DashboardDataService(
        config=config
    )

    def fake_analyze(symbol, exclude=None):
        return [
            AnalysisResult(
                symbol=symbol,
                analyst="Technical Analyst",
                action=Action.BUY,
                confidence=90.0,
                evidence=90.0,
                reasoning=["Strong technical evidence."],
            ),
            AnalysisResult(
                symbol=symbol,
                analyst="Company Analyst",
                action=Action.BUY,
                confidence=80.0,
                evidence=80.0,
                reasoning=["Positive company evidence."],
            ),
        ]

    def fake_analyze_with_news(symbol, news):
        return fake_analyze(symbol)

    monkeypatch.setattr(
        service.analysis,
        "analyze",
        fake_analyze,
    )

    monkeypatch.setattr(
        service.analysis,
        "analyze_with_news",
        fake_analyze_with_news,
    )

    data = service.get_dashboard_data(
        selected_symbol="BTC-USD"
    )

    decision = data["decision"]
    influence = data["decision_influence"]

    assert decision.agent_weights

    assert (
        "Technical Analyst"
        in decision.agent_weights
    )

    assert influence["action_support_analyst"] == (
        decision.action_support_analyst
    )

    assert influence["action_support_action"] == (
        decision.action_support_action.value
        if decision.action_support_action
        else None
    )

    assert influence["action_support_weight"] == round(
        decision.action_support_weight * 100,
        1,
    )

    assert (
        "Company Analyst"
        in decision.agent_weights
    )

    assert round(
        sum(decision.agent_weights.values()),
        4,
    ) == 1.0


def test_dashboard_decision_contains_structured_explanation(
    monkeypatch,
    tmp_path,
):
    from atlas.core.config import AtlasConfig
    from atlas.models.action import Action
    from atlas.models.analysis_result import AnalysisResult
    from atlas.models.decision_explanation import (
        DecisionExplanation,
    )

    config = AtlasConfig(
        agent_performance_storage=str(
            tmp_path / "agent_performance.json"
        )
    )

    service = DashboardDataService(
        config=config
    )

    def fake_analyze(symbol, exclude=None):
        return [
            AnalysisResult(
                symbol=symbol,
                analyst="Technical Analyst",
                action=Action.BUY,
                confidence=90.0,
                evidence=90.0,
                reasoning=["Strong technical evidence."],
            ),
            AnalysisResult(
                symbol=symbol,
                analyst="Company Analyst",
                action=Action.BUY,
                confidence=80.0,
                evidence=80.0,
                reasoning=["Positive company evidence."],
            ),
        ]

    def fake_analyze_with_news(symbol, news):
        return fake_analyze(symbol)

    monkeypatch.setattr(
        service.analysis,
        "analyze",
        fake_analyze,
    )

    monkeypatch.setattr(
        service.analysis,
        "analyze_with_news",
        fake_analyze_with_news,
    )

    data = service.get_dashboard_data(
        selected_symbol="BTC-USD"
    )

    decision = data["decision"]
    explanation = data["decision_explanation"]

    assert isinstance(
        explanation,
        DecisionExplanation,
    )

    assert explanation.action == decision.action
    assert explanation.evidence == decision.evidence
    assert explanation.confidence == decision.confidence
    assert explanation.dominant_action == (
        decision.dominant_action
    )
    assert explanation.dominant_weight == (
        decision.dominant_weight
    )
    assert explanation.decision_margin == (
        decision.decision_margin
    )
    assert explanation.robustness == (
        decision.robustness
    )
    assert explanation.robustness_level == (
        decision.robustness_level
    )

    assert explanation.headline
    assert explanation.summary
    assert explanation.key_reasons


def test_dashboard_decision_influence_contains_learned_action_support(
    monkeypatch,
    tmp_path,
):
    from atlas.core.config import AtlasConfig
    from atlas.models.action import Action
    from atlas.models.analysis_result import AnalysisResult

    config = AtlasConfig(
        agent_performance_storage=str(
            tmp_path / "agent_performance.json"
        )
    )

    service = DashboardDataService(config=config)

    def fake_analyze(symbol, exclude=None):
        return [
            AnalysisResult(
                symbol=symbol,
                analyst="Technical Analyst",
                action=Action.BUY,
                confidence=90.0,
                evidence=90.0,
                reasoning=["Strong technical evidence."],
            ),
            AnalysisResult(
                symbol=symbol,
                analyst="Company Analyst",
                action=Action.BUY,
                confidence=80.0,
                evidence=80.0,
                reasoning=["Positive company evidence."],
            ),
        ]

    def fake_analyze_with_news(symbol, news):
        return fake_analyze(symbol)

    monkeypatch.setattr(
        service.analysis,
        "analyze",
        fake_analyze,
    )

    monkeypatch.setattr(
        service.analysis,
        "analyze_with_news",
        fake_analyze_with_news,
    )

    data = service.get_dashboard_data(
        selected_symbol="BTC-USD"
    )

    influence = data["decision_influence"]

    assert "action_support_analyst" in influence
    assert "action_support_action" in influence
    assert "action_support_weight" in influence

    assert influence["action_support_weight"] >= 0.0


def test_dashboard_reports_market_scan_candidates(monkeypatch):
    from atlas.models.action import Action
    from atlas.models.decision_result import DecisionResult

    service = DashboardDataService()

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

    data = service.get_dashboard_data(
        selected_symbol="NVDA"
    )

    assert "market_scan" in data
    assert len(data["market_scan"]) == 2

    assert data["market_scan"][0]["symbol"] == "NVDA"
    assert data["market_scan"][0]["selected"] is True
    assert data["market_scan"][0]["discovery_score"] == 92.5
    assert data["market_scan"][0]["decision"] == "BUY"


def test_dashboard_decision_influence_contains_learned_action_support(
    monkeypatch,
    tmp_path,
):
    from atlas.core.config import AtlasConfig
    from atlas.models.action import Action
    from atlas.models.analysis_result import AnalysisResult

    config = AtlasConfig(
        agent_performance_storage=str(
            tmp_path / "agent_performance.json"
        )
    )

    service = DashboardDataService(config=config)

    def fake_analyze(symbol, exclude=None):
        return [
            AnalysisResult(
                symbol=symbol,
                analyst="Technical Analyst",
                action=Action.BUY,
                confidence=90.0,
                evidence=90.0,
                reasoning=["Strong technical evidence."],
            ),
            AnalysisResult(
                symbol=symbol,
                analyst="Company Analyst",
                action=Action.BUY,
                confidence=80.0,
                evidence=80.0,
                reasoning=["Positive company evidence."],
            ),
        ]

    def fake_analyze_with_news(symbol, news):
        return fake_analyze(symbol)

    monkeypatch.setattr(
        service.analysis,
        "analyze",
        fake_analyze,
    )

    monkeypatch.setattr(
        service.analysis,
        "analyze_with_news",
        fake_analyze_with_news,
    )

    data = service.get_dashboard_data(
        selected_symbol="BTC-USD"
    )

    influence = data["decision_influence"]

    assert "action_support_analyst" in influence
    assert "action_support_action" in influence
    assert "action_support_weight" in influence

    if influence["action_support_analyst"]:
        assert influence["action_support_action"] in {
            "BUY",
            "HOLD",
            "SELL",
        }
        assert influence["action_support_weight"] >= 0.0
