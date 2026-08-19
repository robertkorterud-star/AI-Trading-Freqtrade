from atlas.decision.engine import DecisionEngine
from atlas.models.action import Action
from atlas.models.analysis_result import AnalysisResult


def result(analyst, action, confidence, evidence):
    return AnalysisResult(
        analyst=analyst,
        symbol="NVDA",
        action=action,
        confidence=confidence,
        evidence=evidence,
        reasoning=[f"{analyst} reasoning"],
    )


def test_decision_engine_uses_unanimous_buy():
    engine = DecisionEngine()

    results = [
        result("News Analyst", Action.BUY, 95, 95),
        result("Technical Analyst", Action.BUY, 90, 90),
        result("Company Analyst", Action.BUY, 85, 85),
    ]

    decision = engine.evaluate(results)

    assert decision.action == Action.BUY


def test_decision_engine_downgrades_conflicting_buy_to_hold():
    engine = DecisionEngine()

    results = [
        result("News Analyst", Action.BUY, 95, 95),
        result("Technical Analyst", Action.BUY, 90, 90),
        result("Company Analyst", Action.SELL, 60, 80),
    ]

    decision = engine.evaluate(results)

    assert decision.action == Action.HOLD


def test_decision_engine_allows_clear_sell():
    engine = DecisionEngine()

    results = [
        result("News Analyst", Action.SELL, 90, 40),
        result("Technical Analyst", Action.SELL, 85, 40),
        result("Company Analyst", Action.SELL, 80, 45),
    ]

    decision = engine.evaluate(results)

    assert decision.action == Action.SELL


def test_decision_engine_holds_mixed_signals():
    engine = DecisionEngine()

    results = [
        result("News Analyst", Action.BUY, 80, 70),
        result("Technical Analyst", Action.HOLD, 70, 65),
        result("Company Analyst", Action.SELL, 70, 65),
    ]

    decision = engine.evaluate(results)

    assert decision.action == Action.HOLD
