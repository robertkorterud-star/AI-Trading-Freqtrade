from unittest.mock import patch

import pandas as pd

from atlas.core.config import AtlasConfig
from atlas.core.engine import AtlasEngine
from atlas.trading.trading_runtime import TradingRuntime


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


def test_atlas_engine_has_trading_runtime():

    engine = AtlasEngine()

    assert isinstance(
        engine.trading_runtime,
        TradingRuntime,
    )


def test_atlas_engine_end_to_end_paper_buy():

    engine = AtlasEngine()

    engine.config.trading_mode = "paper"
    engine.config.paper_trading = True

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

    result = engine.trading_runtime.execute(
        decision=decision,
        price_usd=65000,
        usd_nok=9.50,
        amount_nok=1000,
    )

    assert result["executed"] is True
    assert result["action"] == "BUY"
    assert result["symbol"] == "BTC-USD"
    assert result["amount_nok"] == 1000


def test_atlas_engine_end_to_end_paper_buy_and_sell_with_profit():

    engine = AtlasEngine()

    engine.config.trading_mode = "paper"
    engine.config.paper_trading = True

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

    buy_result = engine.trading_runtime.execute(
        decision=buy_decision,
        price_usd=65000,
        usd_nok=9.50,
        amount_nok=1000,
    )

    assert buy_result["executed"] is True
    assert buy_result["action"] == "BUY"

    sell_result = engine.trading_runtime.execute(
        decision=sell_decision,
        price_usd=70000,
        usd_nok=9.50,
        amount_nok=1000,
    )

    assert sell_result["executed"] is True
    assert sell_result["action"] == "SELL"
    assert sell_result["realized_pnl_nok"] > 0

    portfolio = engine.trading_runtime.controller.trader.portfolio.as_dict(
        9.50
    )

    assert portfolio["profit_vault_nok"] > 0
    assert portfolio["positions"] == []


def test_atlas_engine_start_sends_decision_to_paper_runtime(
    monkeypatch,
):

    from atlas.models.action import Action
    from atlas.models.decision_result import DecisionResult

    engine = AtlasEngine()

    engine.config.trading_mode = "paper"
    engine.config.paper_trading = True

    decision = DecisionResult(
        symbol="BTC-USD",
        action=Action.BUY,
        confidence=95.0,
        evidence=95.0,
    )

    selected = {
        "symbol": "BTC-USD",
        "discovery_score": 100.0,
        "analysis": [],
        "decision": decision,
    }

    calls = []

    def fake_decide_candidates(
        limit=3,
        minimum_score=0.0,
    ):
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

    def fake_execute(
        decision,
        price_usd,
        usd_nok,
        amount_nok=1000.0,
    ):
        calls.append({
            "decision": decision,
            "price_usd": price_usd,
            "usd_nok": usd_nok,
            "amount_nok": amount_nok,
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

    monkeypatch.setattr(
        engine.trading_runtime,
        "execute",
        fake_execute,
    )

    monkeypatch.setattr(
        engine.prediction_evaluator,
        "evaluate_ready",
        lambda current_prices_usd: [],
    )

    engine.start()

    assert len(calls) == 1
    assert calls[0]["decision"] == decision
    assert calls[0]["decision"].symbol == "BTC-USD"
    assert calls[0]["price_usd"] == 100000.0
    assert calls[0]["usd_nok"] == 10.0
    assert calls[0]["amount_nok"] == 1000.0

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
