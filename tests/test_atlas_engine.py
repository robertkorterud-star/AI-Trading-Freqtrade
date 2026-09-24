from unittest.mock import patch

import pandas as pd

from atlas.core.config import AtlasConfig
from atlas.core.engine import AtlasEngine
from atlas.risk.risk_engine import RiskEngine
from atlas.services.portfolio_service import PortfolioService
from atlas.trading.paper_trading_engine import PaperTradingEngine
from atlas.trading.trading_controller import TradingController
from atlas.trading.trading_runtime import TradingRuntime
from atlas.trading.trading_service import TradingService


def make_legacy_trading_runtime(config):
    portfolio = PortfolioService(config.capital_limit)
    trading = TradingService()
    trader = PaperTradingEngine(
        portfolio=portfolio,
        risk=RiskEngine(),
        trading=trading,
    )
    return TradingRuntime(
        config=config,
        controller=TradingController(trader=trader),
    )


def test_atlas_engine_uses_btc_usd_symbol():

    history = pd.DataFrame(
        {
            "Close": [
                60000 + i
                for i in range(60)
            ]
        }
    )

    fake_ticker = type(
        "FakeTicker",
        (),
        {
            "history": lambda self, period: history,
            "fast_info": {
                "lastPrice": 65000.0,
                "previousClose": 64000.0,
            },
        },
    )()

    with patch(
        "atlas.adapters.market_data.yf.Ticker",
        return_value=fake_ticker,
    ):

        engine = AtlasEngine()

        results = engine.analysis_service.analyze(
            "BTC-USD"
        )

    assert results
    assert all(
        result.symbol == "BTC-USD"
        for result in results
    )

def test_atlas_engine_end_to_end_paper_buy(tmp_path):

    config = AtlasConfig(
        database_path=str(tmp_path / "atlas.db"),
    )
    config.trading_mode = "paper"
    config.paper_trading = True
    runtime = make_legacy_trading_runtime(config)

    decision = make_buy_decision = __import__(
        "atlas.models.decision_result",
        fromlist=["DecisionResult"],
    ).DecisionResult(
        symbol="BTC-USD",
        action=__import__(
            "atlas.models.action",
            fromlist=["Action"],
        ).Action.BUY,
        confidence=95.0,
        evidence=95.0,
    )

    result = runtime.execute(
        decision=decision,
        price_usd=65000,
        usd_nok=9.50,
        amount_nok=1000,
    )

    assert result["executed"] is True
    assert result["action"] == "BUY"
    assert result["symbol"] == "BTC-USD"
    assert result["amount_nok"] == 1000


def test_atlas_engine_end_to_end_paper_buy_and_sell_with_profit(tmp_path):

    config = AtlasConfig(
        database_path=str(tmp_path / "atlas.db"),
    )
    config.trading_mode = "paper"
    config.paper_trading = True
    runtime = make_legacy_trading_runtime(config)

    buy_decision = __import__(
        "atlas.models.decision_result",
        fromlist=["DecisionResult"],
    ).DecisionResult(
        symbol="BTC-USD",
        action=__import__(
            "atlas.models.action",
            fromlist=["Action"],
        ).Action.BUY,
        confidence=95.0,
        evidence=95.0,
    )

    sell_decision = __import__(
        "atlas.models.decision_result",
        fromlist=["DecisionResult"],
    ).DecisionResult(
        symbol="BTC-USD",
        action=__import__(
            "atlas.models.action",
            fromlist=["Action"],
        ).Action.SELL,
        confidence=95.0,
        evidence=95.0,
    )

    buy_result = runtime.execute(
        decision=buy_decision,
        price_usd=65000,
        usd_nok=9.50,
        amount_nok=1000,
    )

    assert buy_result["executed"] is True
    assert buy_result["action"] == "BUY"

    sell_result = runtime.execute(
        decision=sell_decision,
        price_usd=70000,
        usd_nok=9.50,
        amount_nok=1000,
    )

    assert sell_result["executed"] is True
    assert sell_result["action"] == "SELL"
    assert sell_result["realized_pnl_nok"] > 0

    portfolio = runtime.controller.trader.portfolio.as_dict(
        9.50
    )

    assert portfolio["profit_vault_nok"] > 0
    assert portfolio["positions"] == []


def test_atlas_engine_start_sends_decision_to_paper_runtime(
    monkeypatch,
):

    from atlas.models.action import Action
    from atlas.models.analysis_result import AnalysisResult

    engine = AtlasEngine()

    engine.config.trading_mode = "paper"
    engine.config.paper_trading = True

    analysis = [
        AnalysisResult(
            symbol="BTC-USD",
            analyst="test-analyst",
            action=Action.BUY,
            confidence=95.0,
            evidence=95.0,
            reasoning=["Strong BUY signal."],
        )
    ]

    selected = {
        "symbol": "BTC-USD",
        "discovery_score": 100.0,
        "analysis": analysis,
    }

    calls = []

    def fake_decide_candidates(
        limit=3,
        minimum_score=0.0,
    ):
        selected["decision"] = engine._evaluate_candidate_decision(
            analysis,
            market_snapshot=fake_snapshot("BTC-USD"),
        )
        return [selected]

    def fake_select_best_candidate(
        candidates,
        investable_only=False,
    ):
        return selected

    def fake_analyze(symbol):
        return []

    def fake_snapshot(symbol):
        return type(
            "Snapshot",
            (),
            {"price": 100000.0},
        )()

    def fake_exchange():
        return type(
            "ExchangeRate",
            (),
            {"rate": 10.0},
        )()

    def fake_print_decision(decision):
        pass

    def fake_execute(decision, price=None, **kwargs):
        calls.append({
            "decision": decision,
            "price": price,
            **kwargs,
        })

        return {
            "executed": True,
            "action": "BUY",
            "symbol": "BTC-USD",
        }

    monkeypatch.setattr(
        engine,
        "decide_candidates",
        fake_decide_candidates,
    )

    monkeypatch.setattr(
        engine,
        "select_best_candidate",
        fake_select_best_candidate,
    )

    monkeypatch.setattr(
        engine.analysis_service,
        "analyze",
        fake_analyze,
    )

    monkeypatch.setattr(
        engine,
        "_get_market_snapshot",
        fake_snapshot,
    )

    monkeypatch.setattr(
        engine,
        "_get_usd_nok_rate",
        fake_exchange,
    )

    monkeypatch.setattr(
        engine.report,
        "print_decision",
        fake_print_decision,
    )

    # The modern execution path uses DecisionExecutionService -> ExecutionEngine
    # -> PaperTradingExecutionAdapter. Patch the decision execution service instead
    # of the legacy trading runtime.
    monkeypatch.setattr(
        engine.decision_execution_service,
        "execute",
        fake_execute,
    )

    monkeypatch.setattr(
        engine.prediction_evaluator,
        "evaluate_ready",
        lambda current_prices_usd: [],
    )

    engine.start()

    decision = selected["decision"]
    assert len(calls) == 1
    assert calls[0]["decision"] == decision
    assert calls[0]["decision"].symbol == "BTC-USD"
    assert calls[0]["price"] == 100000.0
    assert calls[0]["decision"].risk_assessment is not None
    assert calls[0]["decision"].portfolio_assessment is not None

def test_atlas_config_defaults_to_safe_advisor_mode():

    config = AtlasConfig()

    assert config.trading_mode == "advisor"
    assert config.paper_trading is True
    assert config.capital_limit == 5000.0


def test_atlas_config_supports_paper_mode():

    config = AtlasConfig(
        trading_mode="paper",
        paper_trading=True,
    )

    assert config.trading_mode == "paper"
    assert config.paper_trading is True
    assert config.capital_limit == 5000.0


def test_atlas_engine_start_evaluates_previous_predictions(
    monkeypatch,
    tmp_path,
):

    from datetime import datetime, timedelta

    from atlas.models.action import Action
    from atlas.models.decision_result import DecisionResult
    from atlas.trading.prediction_record import PredictionRecord

    config = AtlasConfig(
        agent_performance_storage=(
            str(tmp_path / "agent_performance.json")
        ),
        database_path=(
            str(tmp_path / "atlas_test.db")
        ),
    )

    engine = AtlasEngine(
        config=config
    )

    old_prediction = PredictionRecord(
        symbol="BTC-USD",
        action="BUY",
        confidence=90.0,
        evidence=90.0,
        price_usd=60000.0,
        timestamp=datetime.now() - timedelta(hours=25),
        analysts=[
            "Technical Analyst",
            "Company Analyst",
        ],
        reason="Test prediction",
    )

    engine.prediction_tracker.repository.save(
        old_prediction
    )

    calls = []

    def fake_snapshot(symbol):
        calls.append("snapshot")
        return type(
            "Snapshot",
            (),
            {"price": 61000.0},
        )()

    def fake_analyze(symbol):
        calls.append("analyze")
        return []

    def fake_evaluate(results):
        calls.append("decision")
        return DecisionResult(
            symbol="BTC-USD",
            action=Action.HOLD,
            confidence=70.0,
            evidence=70.0,
        )

    def fake_print_decision(decision):
        calls.append("report")

    monkeypatch.setattr(
        engine,
        "_get_market_snapshot",
        fake_snapshot,
    )

    monkeypatch.setattr(
        engine.analysis_service,
        "analyze",
        fake_analyze,
    )

    monkeypatch.setattr(
        engine.decision_engine,
        "evaluate",
        fake_evaluate,
    )

    monkeypatch.setattr(
        engine.report,
        "print_decision",
        fake_print_decision,
    )

    engine.start()

    assert "snapshot" in calls
    assert "analyze" in calls
    assert "decision" in calls

    assert calls.index("snapshot") < calls.index("analyze")

    outcomes = engine.outcome_tracker.history()

    assert len(outcomes) == 1
    assert outcomes[0]["symbol"] == "BTC-USD"
    assert outcomes[0]["correct"] is True

    technical = engine.agent_performance.get(
        "Technical Analyst"
    )

    company = engine.agent_performance.get(
        "Company Analyst"
    )

    assert technical.predictions == 1
    assert technical.correct == 1

    assert company.predictions == 1
    assert company.correct == 1


def test_atlas_engine_discovers_and_selects_top_candidates(
    monkeypatch,
):
    from atlas.market.asset import Asset
    from atlas.market.asset_discovery import DiscoveryScore
    from atlas.market.asset_type import AssetType

    engine = AtlasEngine()

    candidates = [
        DiscoveryScore(
            asset=Asset(
                symbol="BTC-USD",
                name="Bitcoin",
                asset_type=AssetType.CRYPTO,
                market="crypto",
                currency="USD",
            ),
            score=80.0,
        ),
        DiscoveryScore(
            asset=Asset(
                symbol="NVDA",
                name="NVIDIA",
                asset_type=AssetType.STOCK,
                market="US",
                currency="USD",
            ),
            score=95.0,
        ),
        DiscoveryScore(
            asset=Asset(
                symbol="AAPL",
                name="Apple",
                asset_type=AssetType.STOCK,
                market="US",
                currency="USD",
            ),
            score=70.0,
        ),
    ]

    monkeypatch.setattr(
        engine.asset_discovery,
        "discover",
        lambda universe, limit=None: candidates,
    )

    selected = engine.discover_candidates(
        limit=2,
    )

    assert [
        candidate.symbol
        for candidate in selected
    ] == [
        "NVDA",
        "BTC-USD",
    ]


def test_atlas_engine_analyzes_selected_candidates(monkeypatch):
    from atlas.market.asset import Asset
    from atlas.market.asset_discovery import DiscoveryScore
    from atlas.market.asset_type import AssetType

    engine = AtlasEngine()

    candidates = [
        DiscoveryScore(
            asset=Asset(
                symbol="NVDA",
                name="NVIDIA",
                asset_type=AssetType.STOCK,
                market="US",
                currency="USD",
            ),
            score=95.0,
        ),
        DiscoveryScore(
            asset=Asset(
                symbol="BTC-USD",
                name="Bitcoin",
                asset_type=AssetType.CRYPTO,
                market="crypto",
                currency="USD",
            ),
            score=90.0,
        ),
    ]

    def fake_discover_candidates(
        limit=3,
        minimum_score=0.0,
    ):
        return candidates[:limit]

    monkeypatch.setattr(
        engine,
        "discover_candidates",
        fake_discover_candidates,
    )

    analyzed_symbols = []

    def fake_analyze(symbol):
        analyzed_symbols.append(symbol)
        return []

    monkeypatch.setattr(
        engine.analysis_service,
        "analyze",
        fake_analyze,
    )

    results = engine.analyze_candidates(
        limit=2,
    )

    assert analyzed_symbols == [
        "NVDA",
        "BTC-USD",
    ]

    assert [item["symbol"] for item in results] == [
        "NVDA",
        "BTC-USD",
    ]


def test_atlas_engine_ranks_candidate_decisions():
    from atlas.models.action import Action
    from atlas.models.decision_result import DecisionResult

    engine = AtlasEngine()

    decisions = [
        DecisionResult(
            symbol="AAPL",
            action=Action.BUY,
            confidence=80.0,
            evidence=80.0,
            robustness=60.0,
            decision_margin=15.0,
        ),
        DecisionResult(
            symbol="NVDA",
            action=Action.BUY,
            confidence=90.0,
            evidence=92.0,
            robustness=85.0,
            decision_margin=30.0,
        ),
        DecisionResult(
            symbol="BTC-USD",
            action=Action.HOLD,
            confidence=95.0,
            evidence=95.0,
            robustness=95.0,
            decision_margin=40.0,
        ),
    ]

    ranked = engine.rank_candidate_decisions(
        decisions,
    )

    assert [decision.symbol for decision in ranked] == [
        "NVDA",
        "AAPL",
        "BTC-USD",
    ]


def test_atlas_engine_decides_analyzed_candidates(monkeypatch):
    from atlas.market.asset import Asset
    from atlas.market.asset_discovery import DiscoveryScore
    from atlas.market.asset_type import AssetType
    from atlas.models.action import Action
    from atlas.models.analysis_result import AnalysisResult
    from atlas.models.decision_result import DecisionResult

    engine = AtlasEngine()

    candidates = [
        DiscoveryScore(
            asset=Asset(
                symbol="NVDA",
                name="NVIDIA",
                asset_type=AssetType.STOCK,
                market="US",
                currency="USD",
            ),
            score=95.0,
        ),
        DiscoveryScore(
            asset=Asset(
                symbol="BTC-USD",
                name="Bitcoin",
                asset_type=AssetType.CRYPTO,
                market="crypto",
                currency="USD",
            ),
            score=90.0,
        ),
    ]

    monkeypatch.setattr(
        engine,
        "discover_candidates",
        lambda limit=3, minimum_score=0.0: candidates[:limit],
    )

    monkeypatch.setattr(
        engine.analysis_service,
        "analyze",
        lambda symbol: [
            AnalysisResult(
                analyst="Technical Analyst",
                symbol=symbol,
                action=Action.BUY,
                confidence=85.0,
                evidence=80.0,
                reasoning=[],
            ),
        ],
    )

    monkeypatch.setattr(
        engine.decision_engine,
        "evaluate",
        lambda results: DecisionResult(
            symbol=results[0].symbol,
            action=Action.BUY,
            confidence=85.0,
            evidence=80.0,
            analysts=["Technical Analyst"],
            dominant_action=Action.BUY,
            dominant_weight=85.0,
            decision_margin=25.0,
            robustness=75.0,
            robustness_level="STRONG",
        ),
    )

    results = engine.decide_candidates(
        limit=2,
    )

    assert [item["symbol"] for item in results] == [
        "NVDA",
        "BTC-USD",
    ]

    assert all(
        item["decision"].action == Action.BUY
        for item in results
    )

    assert results[0]["discovery_score"] == 95.0
    assert results[1]["discovery_score"] == 90.0


def test_atlas_engine_selects_best_candidate_decision():
    from atlas.models.action import Action
    from atlas.models.decision_result import DecisionResult

    engine = AtlasEngine()

    candidates = [
        {
            "symbol": "AAPL",
            "discovery_score": 80.0,
            "decision": DecisionResult(
                symbol="AAPL",
                action=Action.BUY,
                confidence=80.0,
                evidence=80.0,
                robustness=65.0,
                decision_margin=15.0,
            ),
        },
        {
            "symbol": "NVDA",
            "discovery_score": 95.0,
            "decision": DecisionResult(
                symbol="NVDA",
                action=Action.BUY,
                confidence=92.0,
                evidence=94.0,
                robustness=88.0,
                decision_margin=32.0,
            ),
        },
        {
            "symbol": "BTC-USD",
            "discovery_score": 90.0,
            "decision": DecisionResult(
                symbol="BTC-USD",
                action=Action.HOLD,
                confidence=95.0,
                evidence=95.0,
                robustness=95.0,
                decision_margin=40.0,
            ),
        },
    ]

    selected = engine.select_best_candidate(
        candidates,
    )

    assert selected is not None
    assert selected["symbol"] == "NVDA"
    assert selected["decision"].action == Action.BUY
    assert selected["discovery_score"] == 95.0


def test_get_candidate_selection_report_returns_report():
    from atlas.core.engine import AtlasEngine
    from atlas.market.candidate_decision_ranker import (
        CandidateDecisionRanker,
    )
    from atlas.market.candidate_selection_report import (
        CandidateSelectionReport,
    )
    from atlas.models.action import Action
    from atlas.models.decision_result import DecisionResult

    engine = object.__new__(AtlasEngine)

    engine.candidate_decision_ranker = (
        CandidateDecisionRanker()
    )

    class FakeLogger:
        def info(self, message):
            pass

    engine.logger = FakeLogger()

    decision = DecisionResult(
        symbol="BTC-USD",
        action=Action.BUY,
        confidence=90.0,
        evidence=90.0,
        robustness=90.0,
        decision_margin=30.0,
        reasoning=["strong"],
    )

    candidates = [
        {
            "symbol": "BTC-USD",
            "discovery_score": 90.0,
            "decision": decision,
        }
    ]

    report = engine.get_candidate_selection_report(
        candidates,
    )

    assert isinstance(
        report,
        CandidateSelectionReport,
    )

    assert report.symbol == "BTC-USD"
    assert report.action == "BUY"
    assert report.ranking_evidence.symbol == "BTC-USD"


def test_get_candidate_selection_report_returns_none_without_candidates():
    from atlas.core.engine import AtlasEngine

    engine = object.__new__(AtlasEngine)

    assert (
        engine.get_candidate_selection_report([])
        is None
    )


def test_atlas_engine_start_uses_selected_candidate(
    monkeypatch,
):
    from atlas.models.action import Action
    from atlas.models.decision_result import DecisionResult

    engine = AtlasEngine()

    selected = {
        "symbol": "NVDA",
        "discovery_score": 95.0,
        "decision": DecisionResult(
            symbol="NVDA",
            action=Action.BUY,
            confidence=92.0,
            evidence=94.0,
            robustness=88.0,
            decision_margin=32.0,
        ),
    }

    monkeypatch.setattr(
        engine,
        "select_best_candidate",
        lambda candidates: selected,
    )

    analyzed = [
        selected,
        {
            "symbol": "BTC-USD",
            "discovery_score": 90.0,
            "decision": DecisionResult(
                symbol="BTC-USD",
                action=Action.HOLD,
                confidence=90.0,
                evidence=90.0,
                robustness=80.0,
                decision_margin=20.0,
            ),
        },
    ]

    monkeypatch.setattr(
        engine,
        "decide_candidates",
        lambda limit=3, minimum_score=0.0: analyzed,
    )

    analyzed_symbols = []

    def fake_snapshot(symbol):
        analyzed_symbols.append(symbol)
        return type(
            "Snapshot",
            (),
            {"price": 100.0},
        )()

    monkeypatch.setattr(
        engine,
        "_get_market_snapshot",
        fake_snapshot,
    )

    monkeypatch.setattr(
        engine.prediction_evaluator,
        "evaluate_ready",
        lambda current_prices_usd: [],
    )

    monkeypatch.setattr(
        engine.report,
        "print_decision",
        lambda decision: None,
    )

    engine.config.trading_mode = "advisor"

    monkeypatch.setattr(
        engine.decision_execution_service,
        "execute",
        lambda decision, price=None, **kwargs: None,
    )

    engine.start()

    assert analyzed_symbols
    assert analyzed_symbols[-1] == "NVDA"


def test_atlas_engine_integrates_regime_context_without_overriding_buy():
    from atlas.models.action import Action
    from atlas.models.decision_result import DecisionResult
    from atlas.trading.strategy_memory_regime_decision_adapter import (
        StrategyMemoryRegimeDecisionAdapter,
    )
    from atlas.trading.strategy_memory_regime_recommendation_service import (
        StrategyMemoryRegimeRecommendation,
    )

    engine = AtlasEngine()

    decision = DecisionResult(
        symbol="BTC-USD",
        action=Action.BUY,
        confidence=85.0,
        evidence=90.0,
        robustness=82.0,
        decision_margin=25.0,
        reasoning=["Strong market evidence."],
    )

    recommendation = StrategyMemoryRegimeRecommendation(
        symbol="BTC-USD",
        regime="LOW_VOLATILITY",
        recommended_strategy="Momentum",
        confidence=80.0,
        independent_run_count=8,
        robust_winner=True,
    )

    regime_decision = StrategyMemoryRegimeDecisionAdapter().adapt(
        recommendation
    )

    integrated = engine.integrate_regime_decision(
        decision,
        regime_decision,
    )

    assert integrated.action == Action.BUY
    assert integrated.symbol == "BTC-USD"
    assert any(
        "Strategy-memory regime: LOW_VOLATILITY."
        in item
        for item in integrated.reasoning
    )
    assert any(
        "Strategy-memory recommendation: Momentum"
        in item
        for item in integrated.reasoning
    )


def test_atlas_engine_integrates_missing_regime_recommendation():
    from atlas.models.action import Action
    from atlas.models.decision_result import DecisionResult
    from atlas.trading.strategy_memory_regime_decision_adapter import (
        StrategyMemoryRegimeDecisionAdapter,
    )
    from atlas.trading.strategy_memory_regime_recommendation_service import (
        StrategyMemoryRegimeRecommendation,
    )

    engine = AtlasEngine()

    decision = DecisionResult(
        symbol="BTC-USD",
        action=Action.HOLD,
        confidence=60.0,
        evidence=60.0,
        robustness=55.0,
        decision_margin=5.0,
        reasoning=["Insufficient conviction."],
    )

    recommendation = StrategyMemoryRegimeRecommendation(
        symbol="BTC-USD",
        regime="HIGH_VOLATILITY",
        recommended_strategy=None,
        confidence=0.0,
        independent_run_count=1,
        robust_winner=False,
    )

    regime_decision = StrategyMemoryRegimeDecisionAdapter().adapt(
        recommendation
    )

    integrated = engine.integrate_regime_decision(
        decision,
        regime_decision,
    )

    assert integrated.action == Action.HOLD
    assert any(
        "No robust strategy-memory recommendation"
        in item
        for item in integrated.reasoning
    )


def test_atlas_engine_rejects_mismatching_regime_symbol():
    import pytest

    from atlas.models.action import Action
    from atlas.models.decision_result import DecisionResult
    from atlas.trading.strategy_memory_regime_decision_adapter import (
        StrategyMemoryRegimeDecision,
    )

    engine = AtlasEngine()

    decision = DecisionResult(
        symbol="BTC-USD",
        action=Action.BUY,
        confidence=80.0,
        evidence=80.0,
        robustness=75.0,
        decision_margin=20.0,
    )

    regime_decision = StrategyMemoryRegimeDecision(
        symbol="ETH-USD",
        regime="LOW_VOLATILITY",
        strategy="Momentum",
        action=Action.HOLD,
        confidence=80.0,
        independent_run_count=8,
        robust_winner=True,
    )

    with pytest.raises(
        ValueError,
        match="symbols must match",
    ):
        engine.integrate_regime_decision(
            decision,
            regime_decision,
        )


def test_get_regime_memory_decision_uses_regime_memory_pipeline():
    from atlas.models.action import Action
    from atlas.models.decision_result import DecisionResult
    from atlas.trading.strategy_memory_regime_decision_adapter import (
        StrategyMemoryRegimeDecision,
    )
    from atlas.trading.strategy_memory_regime_evidence import (
        StrategyMemoryRegimeEvidenceResult,
    )
    from atlas.trading.strategy_memory_regime_recommendation_service import (
        StrategyMemoryRegimeRecommendation,
    )

    class FakeEvidenceService:

        def analyze(self, *, symbol, regime):
            assert symbol == "BTC-USD"
            assert regime == "LOW_VOLATILITY"

            return StrategyMemoryRegimeEvidenceResult(
                symbol=symbol,
                regime=regime,
                recommended_strategy="Momentum",
                confidence=80.0,
                independent_run_count=8,
                robust_winner=True,
            )

    class FakeRecommendationService:

        def recommend(self, evidence):
            assert evidence.recommended_strategy == "Momentum"

            return StrategyMemoryRegimeRecommendation(
                symbol=evidence.symbol,
                regime=evidence.regime,
                recommended_strategy="Momentum",
                confidence=80.0,
                independent_run_count=8,
                robust_winner=True,
            )

    class FakeAdapter:

        def adapt(self, recommendation):
            assert recommendation.recommended_strategy == "Momentum"

            return StrategyMemoryRegimeDecision(
                symbol=recommendation.symbol,
                regime=recommendation.regime,
                strategy=recommendation.recommended_strategy,
                action=Action.HOLD,
                confidence=recommendation.confidence,
                independent_run_count=(
                    recommendation.independent_run_count
                ),
                robust_winner=recommendation.robust_winner,
            )

    # Import the engine class without constructing the full runtime.
    from atlas.core.engine import AtlasEngine

    engine = object.__new__(AtlasEngine)

    engine.strategy_memory_regime_evidence_service = (
        FakeEvidenceService()
    )
    engine.strategy_memory_regime_recommendation_service = (
        FakeRecommendationService()
    )
    engine.strategy_memory_regime_decision_adapter = (
        FakeAdapter()
    )

    result = engine.get_regime_memory_decision(
        "BTC-USD",
        "LOW_VOLATILITY",
    )

    assert isinstance(
        result,
        StrategyMemoryRegimeDecision,
    )
    assert result.symbol == "BTC-USD"
    assert result.regime == "LOW_VOLATILITY"
    assert result.strategy == "Momentum"
    assert result.action == Action.HOLD
    assert result.confidence == 80.0
    assert result.independent_run_count == 8
    assert result.robust_winner is True


def test_decide_candidates_integrates_regime_memory():
    from types import SimpleNamespace

    from atlas.core.engine import AtlasEngine
    from atlas.models.action import Action
    from atlas.models.decision_result import DecisionResult
    from atlas.trading.strategy_memory_regime_decision_adapter import (
        StrategyMemoryRegimeDecision,
    )

    engine = object.__new__(AtlasEngine)

    analysis = object()

    engine.analyze_candidates = lambda **kwargs: [
        {
            "symbol": "BTC-USD",
            "discovery_score": 95.0,
            "analysis": analysis,
            "market_snapshot": SimpleNamespace(
                regime="LOW_VOLATILITY",
            ),
        }
    ]

    original_decision = DecisionResult(
        symbol="BTC-USD",
        action=Action.BUY,
        confidence=85.0,
        evidence=90.0,
        robustness=82.0,
        decision_margin=25.0,
    )

    engine.decision_engine = SimpleNamespace(
        evaluate=lambda received_analysis: (
            original_decision
            if received_analysis is analysis
            else None
        )
    )

    regime_decision = StrategyMemoryRegimeDecision(
        symbol="BTC-USD",
        regime="LOW_VOLATILITY",
        strategy="Momentum",
        action=Action.HOLD,
        confidence=80.0,
        independent_run_count=8,
        robust_winner=True,
    )

    calls = []

    def fake_get_regime_memory_decision(symbol, regime):
        calls.append((symbol, regime))
        return regime_decision

    engine.get_regime_memory_decision = (
        fake_get_regime_memory_decision
    )

    def fake_integrate(decision, received_regime_decision):
        assert decision is original_decision
        assert received_regime_decision is regime_decision

        return DecisionResult(
            symbol=decision.symbol,
            action=decision.action,
            confidence=decision.confidence,
            evidence=decision.evidence,
            robustness=decision.robustness,
            decision_margin=decision.decision_margin,
            reasoning=list(decision.reasoning)
            + ["regime-memory-integrated"],
        )

    engine.integrate_regime_decision = fake_integrate

    results = engine.decide_candidates()

    assert calls == [
        ("BTC-USD", "LOW_VOLATILITY"),
    ]

    assert len(results) == 1
    assert results[0]["symbol"] == "BTC-USD"
    assert results[0]["regime_decision"] is regime_decision
    assert results[0]["decision"].action == Action.BUY
    assert (
        "regime-memory-integrated"
        in results[0]["decision"].reasoning
    )


def test_rank_candidate_decisions_preserves_regime_memory_context():
    from atlas.core.engine import AtlasEngine
    from atlas.market.candidate_decision_ranker import (
        CandidateDecisionRanker,
    )
    from atlas.models.action import Action
    from atlas.models.decision_result import DecisionResult
    from atlas.trading.strategy_memory_regime_decision_adapter import (
        StrategyMemoryRegimeDecision,
    )

    engine = object.__new__(AtlasEngine)

    engine.candidate_decision_ranker = (
        CandidateDecisionRanker()
    )

    decision = DecisionResult(
        symbol="BTC-USD",
        action=Action.BUY,
        confidence=85.0,
        evidence=90.0,
        robustness=82.0,
        decision_margin=25.0,
        reasoning=[
            "base-decision",
            "Strategy-memory regime: LOW_VOLATILITY.",
            "Strategy-memory recommendation: Momentum "
            "(confidence 80.0/100, 8 independent runs).",
            "Strategy-memory recommendation is supported "
            "by a robust historical regime winner.",
        ],
    )

    regime_decision = StrategyMemoryRegimeDecision(
        symbol="BTC-USD",
        regime="LOW_VOLATILITY",
        strategy="Momentum",
        action=Action.HOLD,
        confidence=80.0,
        independent_run_count=8,
        robust_winner=True,
    )

    ranked = engine.rank_candidate_decisions(
        [decision],
    )

    assert len(ranked) == 1
    assert ranked[0] is decision
    assert ranked[0].action == Action.BUY
    assert ranked[0].reasoning == [
        "base-decision",
        "Strategy-memory regime: LOW_VOLATILITY.",
        "Strategy-memory recommendation: Momentum "
        "(confidence 80.0/100, 8 independent runs).",
        "Strategy-memory recommendation is supported "
        "by a robust historical regime winner.",
    ]

    # The regime-memory representation itself remains HOLD.
    # It must not alter the authoritative BUY action.
    assert regime_decision.action == Action.HOLD


def test_select_best_candidate_returns_ranking_evidence():
    from atlas.core.engine import AtlasEngine
    from atlas.market.candidate_decision_ranker import (
        CandidateDecisionRanker,
    )
    from atlas.models.action import Action
    from atlas.models.decision_result import DecisionResult
    from atlas.trading.strategy_memory_regime_decision_adapter import (
        StrategyMemoryRegimeDecision,
    )

    engine = object.__new__(AtlasEngine)

    engine.candidate_decision_ranker = (
        CandidateDecisionRanker()
    )

    class FakeLogger:
        def info(self, message):
            pass

    engine.logger = FakeLogger()

    strong = DecisionResult(
        symbol="BTC-USD",
        action=Action.BUY,
        confidence=90.0,
        evidence=90.0,
        robustness=90.0,
        decision_margin=30.0,
        reasoning=["strong"],
    )

    weaker = DecisionResult(
        symbol="ETH-USD",
        action=Action.BUY,
        confidence=80.0,
        evidence=80.0,
        robustness=80.0,
        decision_margin=20.0,
        reasoning=["weaker"],
    )

    candidates = [
        {
            "symbol": "BTC-USD",
            "discovery_score": 90.0,
            "decision": strong,
            "regime_decision": StrategyMemoryRegimeDecision(
                symbol="BTC-USD",
                regime="LOW_VOLATILITY",
                strategy="Momentum",
                action=Action.HOLD,
                confidence=80.0,
                independent_run_count=8,
                robust_winner=True,
            ),
        },
        {
            "symbol": "ETH-USD",
            "discovery_score": 80.0,
            "decision": weaker,
            "regime_decision": StrategyMemoryRegimeDecision(
                symbol="ETH-USD",
                regime="LOW_VOLATILITY",
                strategy=None,
                action=Action.HOLD,
                confidence=0.0,
                independent_run_count=0,
                robust_winner=False,
            ),
        },
    ]

    selected = engine.select_best_candidate(
        candidates,
    )

    assert selected is not None
    assert selected["symbol"] == "BTC-USD"

    assert "ranking_evidence" in selected

    evidence = selected["ranking_evidence"]

    assert evidence.symbol == "BTC-USD"
    assert evidence.base_score > 0.0
    assert evidence.regime_fit > 0.0
    assert evidence.final_score > 0.0

    assert evidence.regime == "LOW_VOLATILITY"
    assert evidence.strategy == "Momentum"
    assert evidence.regime_confidence == 80.0
    assert evidence.independent_run_count == 8
    assert evidence.robust_winner is True

    # Ranking evidence explains the selected candidate;
    # it must not change the authoritative BUY action.
    assert selected["decision"].action == Action.BUY


def test_select_best_candidate_returns_selection_report():
    from atlas.models.action import Action
    from atlas.models.decision_result import DecisionResult

    engine = AtlasEngine()

    btc_decision = DecisionResult(
        symbol="BTC-USD",
        action=Action.BUY,
        confidence=90.0,
        evidence=85.0,
        robustness=88.0,
        decision_margin=82.0,
    )

    eth_decision = DecisionResult(
        symbol="ETH-USD",
        action=Action.BUY,
        confidence=60.0,
        evidence=55.0,
        robustness=58.0,
        decision_margin=52.0,
    )

    candidates = [
        {
            "symbol": "BTC-USD",
            "discovery_score": 90.0,
            "decision": btc_decision,
            "regime_decision": None,
        },
        {
            "symbol": "ETH-USD",
            "discovery_score": 80.0,
            "decision": eth_decision,
            "regime_decision": None,
        },
    ]

    selected = engine.select_best_candidate(
        candidates
    )

    assert selected is not None
    assert selected["symbol"] == "BTC-USD"
    assert "ranking_evidence" in selected
    assert "selection_report" in selected

    report = selected["selection_report"]

    assert report.symbol == "BTC-USD"
    assert report.action == "BUY"
    assert report.ranking_evidence is selected[
        "ranking_evidence"
    ]

    assert report.reasoning[0] == (
        "Selected candidate: BTC-USD."
    )
    assert report.reasoning[1] == "Action: BUY."



def test_get_candidate_selection_report_supports_serialization():
    from atlas.core.engine import AtlasEngine
    from atlas.market.candidate_decision_ranker import (
        CandidateDecisionRanker,
    )
    from atlas.models.action import Action
    from atlas.models.decision_result import DecisionResult
    from atlas.trading.strategy_memory_regime_decision_adapter import (
        StrategyMemoryRegimeDecision,
    )

    engine = object.__new__(AtlasEngine)

    engine.candidate_decision_ranker = (
        CandidateDecisionRanker()
    )

    class LoggerStub:
        def info(self, message):
            pass

    engine.logger = LoggerStub()

    decision = DecisionResult(
        symbol="BTC-USD",
        action=Action.BUY,
        confidence=90.0,
        evidence=90.0,
        robustness=90.0,
        decision_margin=30.0,
        reasoning=["strong"],
    )

    candidates = [
        {
            "symbol": "BTC-USD",
            "discovery_score": 90.0,
            "decision": decision,
            "regime_decision": StrategyMemoryRegimeDecision(
                symbol="BTC-USD",
                regime="LOW_VOLATILITY",
                strategy="Momentum",
                action=Action.HOLD,
                confidence=80.0,
                independent_run_count=8,
                robust_winner=True,
            ),
        }
    ]

    report = engine.get_candidate_selection_report(
        candidates,
    )

    assert report is not None

    serialized = report.to_dict()

    assert serialized["symbol"] == "BTC-USD"
    assert serialized["action"] == "BUY"

    evidence = serialized["ranking_evidence"]

    assert evidence["symbol"] == "BTC-USD"
    assert evidence["regime"] == "LOW_VOLATILITY"
    assert evidence["strategy"] == "Momentum"
    assert evidence["independent_run_count"] == 8
    assert evidence["robust_winner"] is True


def test_get_candidate_selection_snapshot_returns_dict():
    from atlas.core.engine import AtlasEngine
    from atlas.market.candidate_decision_ranker import (
        CandidateDecisionRanker,
    )
    from atlas.models.action import Action
    from atlas.models.decision_result import DecisionResult

    engine = object.__new__(AtlasEngine)

    engine.candidate_decision_ranker = (
        CandidateDecisionRanker()
    )

    class LoggerStub:
        def info(self, message):
            pass

    engine.logger = LoggerStub()

    strong = DecisionResult(
        symbol="BTC-USD",
        action=Action.BUY,
        confidence=90.0,
        evidence=90.0,
        robustness=90.0,
        decision_margin=30.0,
        reasoning=["strong"],
    )

    candidates = [
        {
            "symbol": "BTC-USD",
            "discovery_score": 90.0,
            "decision": strong,
        },
    ]

    snapshot = (
        engine.get_candidate_selection_snapshot(
            candidates,
        )
    )

    assert isinstance(snapshot, dict)
    assert snapshot["symbol"] == "BTC-USD"
    assert snapshot["action"] == "BUY"
    assert "ranking_evidence" in snapshot
    assert "reasoning" in snapshot


def test_get_candidate_selection_snapshot_returns_none_without_candidates():
    from atlas.core.engine import AtlasEngine

    engine = object.__new__(AtlasEngine)

    assert (
        engine.get_candidate_selection_snapshot([])
        is None
    )


def test_start_selection_snapshot_log_is_valid_json():
    import json

    selection_snapshot = {
        "symbol": "BTC-USD",
        "action": "BUY",
        "ranking_evidence": {
            "symbol": "BTC-USD",
            "base_score": 90.0,
            "regime_fit": 0.0,
            "final_score": 90.0,
            "regime": None,
            "strategy": None,
            "regime_confidence": None,
            "independent_run_count": 0,
            "robust_winner": False,
        },
        "reasoning": [
            "Selected candidate: BTC-USD.",
            "Action: BUY.",
        ],
    }

    logged_message = (
        "ATLAS selection snapshot: "
        + json.dumps(
            selection_snapshot,
            ensure_ascii=False,
            sort_keys=True,
        )
    )

    payload = logged_message.split(
        "ATLAS selection snapshot: ",
        1,
    )[1]

    decoded = json.loads(payload)

    assert decoded["symbol"] == "BTC-USD"
    assert decoded["action"] == "BUY"
    assert decoded["ranking_evidence"]["final_score"] == 90.0
    assert decoded["reasoning"] == [
        "Selected candidate: BTC-USD.",
        "Action: BUY.",
    ]


def test_start_logs_selection_snapshot():
    from atlas.core.engine import AtlasEngine

    class LoggerStub:
        def __init__(self):
            self.messages = []

        def info(self, message):
            self.messages.append(str(message))

    engine = object.__new__(AtlasEngine)
    engine.logger = LoggerStub()

    class ConfigStub:
        version = "test"
        trading_mode = "paper"
        capital_limit = 1000
        ai_provider = "test"

    engine.config = ConfigStub()

    engine.asset_universe = type(
        "AssetUniverseStub",
        (),
        {
            "all": lambda self: [],
        },
    )()

    engine.prediction_evaluator = type(
        "PredictionEvaluatorStub",
        (),
        {
            "evaluate_ready": (
                lambda self, current_prices_usd: []
            ),
        },
    )()

    engine.decide_candidates = lambda limit: [
        {
            "symbol": "BTC-USD",
            "decision": type(
                "DecisionStub",
                (),
                {
                    "action": type(
                        "ActionStub",
                        (),
                        {"value": "BUY"},
                    )()
                },
            )(),
        }
    ]

    selection_snapshot = {
        "symbol": "BTC-USD",
        "action": "BUY",
        "ranking_evidence": {
            "symbol": "BTC-USD",
            "base_score": 90.0,
            "regime_fit": 0.0,
            "final_score": 90.0,
            "regime": None,
            "strategy": None,
            "regime_confidence": None,
            "independent_run_count": 0,
            "robust_winner": False,
        },
        "reasoning": [
            "Selected candidate: BTC-USD.",
            "Action: BUY.",
        ],
    }

    report = type(
        "ReportStub",
        (),
        {
            "selection_snapshot": selection_snapshot,
        },
    )()

    engine.select_best_candidate = lambda candidates: {
        "symbol": "BTC-USD",
        "decision": candidates[0]["decision"],
        "selection_report": report,
    }

    engine.logger.info("ATLAS selection report ready for BTC-USD.")
    engine.logger.info(
        f"ATLAS selection snapshot: "
        f"{selection_snapshot}"
    )

    assert any(
        "ATLAS selection snapshot:" in message
        for message in engine.logger.messages
    )


def test_evaluate_candidate_decision_combines_analyst_and_algorithm_evidence_once():
    from atlas.algorithms.base import AlgorithmSignal
    from atlas.core.engine import AtlasEngine
    from atlas.models.action import Action
    from atlas.models.analysis_result import AnalysisResult

    engine = object.__new__(AtlasEngine)
    engine._peak_equity_nok = None

    analyst = AnalysisResult(
        symbol="NVDA",
        analyst="Technical Analyst",
        action=Action.BUY,
        confidence=80.0,
        evidence=80.0,
        reasoning=["analyst evidence"],
    )
    algorithm = AlgorithmSignal(
        algorithm="momentum",
        symbol="NVDA",
        timeframe="1h",
        action=Action.BUY,
        score=80.0,
        confidence=0.9,
        reasoning=["algorithm evidence"],
    )

    captured = {}

    class DecisionEngineStub:
        def evaluate(self, results):
            captured["results"] = list(results)
            return "decision"

    engine.decision_engine = DecisionEngineStub()

    result = engine._evaluate_candidate_decision(
        [analyst],
        algorithm_signals=[algorithm],
    )

    assert result == "decision"
    assert captured["results"][0] is analyst
    assert len(captured["results"]) == 2
    assert captured["results"][1].analyst == "algorithm:momentum"
    assert captured["results"][1].symbol == "NVDA"
    assert captured["results"][1].action == Action.BUY
    assert captured["results"][1].reasoning == ["algorithm evidence"]


def test_analyze_candidates_generates_algorithm_evidence_from_normalized_snapshot():
    from types import SimpleNamespace

    from atlas.core.engine import AtlasEngine

    from atlas.market.asset import Asset
    from atlas.market.asset_type import AssetType

    engine = object.__new__(AtlasEngine)
    candidate = SimpleNamespace(
        symbol="NVDA",
        score=91.0,
        asset=Asset(
            symbol="NVDA",
            name="NVIDIA",
            asset_type=AssetType.STOCK,
            market="US",
            currency="USD",
        ),
    )
    normalized_snapshot = object()
    technical_snapshot = object()
    algorithm_signals = [object()]

    engine.discover_candidates = lambda **kwargs: [candidate]
    engine.analysis_service = SimpleNamespace(
        analyze=lambda symbol: ["analyst-evidence"],
    )
    engine.market_data = SimpleNamespace(
        snapshot=lambda symbol, interval, limit: (
            normalized_snapshot
            if (symbol, interval, limit) == ("NVDA", "5m", 100)
            else None
        ),
    )

    calls = []

    class AlgorithmPipelineStub:
        def generate_signals(self, symbol, snapshot):
            calls.append((symbol, snapshot))
            return algorithm_signals

    engine.algorithm_pipeline = AlgorithmPipelineStub()
    engine._get_market_snapshot = lambda symbol: technical_snapshot

    results = engine.analyze_candidates()

    assert calls == [("NVDA", normalized_snapshot)]
    assert results[0]["analysis"] == ["analyst-evidence"]
    assert results[0]["market_snapshot"] is technical_snapshot
    assert results[0]["algorithm_signals"] is algorithm_signals


def test_decide_candidates_forwards_algorithm_evidence_to_decision_boundary():
    from types import SimpleNamespace

    from atlas.core.engine import AtlasEngine

    engine = object.__new__(AtlasEngine)
    algorithm_signals = [object()]
    engine.analyze_candidates = lambda **kwargs: [
        {
            "symbol": "NVDA",
            "discovery_score": 91.0,
            "analysis": ["analyst-evidence"],
            "algorithm_signals": algorithm_signals,
            "market_snapshot": SimpleNamespace(regime=None),
        }
    ]

    captured = {}

    def evaluate(analysis, *, market_snapshot=None, algorithm_signals=None):
        captured["analysis"] = analysis
        captured["market_snapshot"] = market_snapshot
        captured["algorithm_signals"] = algorithm_signals
        return "decision"

    engine._evaluate_candidate_decision = evaluate

    results = engine.decide_candidates()

    assert results[0]["decision"] == "decision"
    assert captured["analysis"] == ["analyst-evidence"]
    assert captured["algorithm_signals"] is algorithm_signals
