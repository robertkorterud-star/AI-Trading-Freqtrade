from atlas.decision.intelligence_layer import IntelligenceLayer
from atlas.models.action import Action
from atlas.models.analysis_result import AnalysisResult


def result(analyst, action, confidence, evidence):
    return AnalysisResult(
        analyst=analyst,
        symbol="NVDA",
        action=action,
        confidence=confidence,
        evidence=evidence,
        reasoning=[f"{analyst} test reasoning"],
    )


def test_intelligence_layer_detects_unanimous_buy():

    layer = IntelligenceLayer()

    results = [
        result("News Analyst", Action.BUY, 95, 95),
        result("Technical Analyst", Action.BUY, 88, 85),
        result("Company Analyst", Action.BUY, 85, 85),
        result("Intelligence Analyst", Action.BUY, 85, 95),
    ]

    summary = layer.summarize(results)

    assert summary.symbol == "NVDA"
    assert summary.action == Action.BUY

    assert summary.buy_count == 4
    assert summary.hold_count == 0
    assert summary.sell_count == 0

    assert summary.agreement == 100.0
    assert summary.conflict is False

    assert summary.evidence == 90.0
    assert summary.confidence == 88.25


def test_intelligence_layer_detects_conflict():

    layer = IntelligenceLayer()

    results = [
        result("News Analyst", Action.BUY, 90, 90),
        result("Technical Analyst", Action.BUY, 80, 80),
        result("Company Analyst", Action.SELL, 70, 60),
        result("Intelligence Analyst", Action.HOLD, 60, 50),
    ]

    summary = layer.summarize(results)

    assert summary.symbol == "NVDA"

    assert summary.buy_count == 2
    assert summary.hold_count == 1
    assert summary.sell_count == 1

    assert summary.agreement == 50.0
    assert summary.conflict is True

    assert summary.action == Action.BUY


def test_intelligence_layer_handles_single_analyst():

    layer = IntelligenceLayer()

    results = [
        result("News Analyst", Action.SELL, 70, 45),
    ]

    summary = layer.summarize(results)

    assert summary.action == Action.SELL
    assert summary.buy_count == 0
    assert summary.hold_count == 0
    assert summary.sell_count == 1

    assert summary.agreement == 100.0
    assert summary.conflict is False


def test_intelligence_layer_rejects_empty_results():

    layer = IntelligenceLayer()

    try:
        layer.summarize([])
    except ValueError:
        return

    raise AssertionError(
        "IntelligenceLayer must reject empty results"
    )


def test_intelligence_layer_calculates_weighted_signals():

    layer = IntelligenceLayer()

    results = [
        result(
            "Technical Analyst",
            Action.BUY,
            100,
            100,
        ),
        result(
            "News Analyst",
            Action.SELL,
            100,
            0,
        ),
        result(
            "Company Analyst",
            Action.SELL,
            100,
            0,
        ),
    ]

    weights = {
        "Technical Analyst": 0.60,
        "News Analyst": 0.20,
        "Company Analyst": 0.20,
    }

    summary = layer.summarize(
        results,
        weights=weights,
    )

    assert summary.weighted_buy == 60.0
    assert summary.weighted_hold == 0.0
    assert summary.weighted_sell == 40.0

    assert summary.weighted_agreement == 60.0
    assert summary.weighted_conflict is True


def test_intelligence_layer_weighted_signals_fallback_to_equal():

    layer = IntelligenceLayer()

    results = [
        result(
            "Technical Analyst",
            Action.BUY,
            100,
            100,
        ),
        result(
            "News Analyst",
            Action.SELL,
            100,
            0,
        ),
    ]

    summary = layer.summarize(results)

    assert summary.weighted_buy == 50.0
    assert summary.weighted_hold == 0.0
    assert summary.weighted_sell == 50.0

    assert summary.weighted_agreement == 50.0
    assert summary.weighted_conflict is True
