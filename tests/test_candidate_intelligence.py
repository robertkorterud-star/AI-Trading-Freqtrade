from atlas.market.candidate_intelligence import (
    CandidateIntelligenceInput,
    CandidateIntelligenceService,
)
from atlas.market.market_scout import AssetType, MarketObservation, MarketScout


def _evidence():
    observation = MarketObservation(
        symbol="TEST",
        asset_type=AssetType.STOCK,
        price=10.0,
        volume=1_000_000.0,
        average_volume=100_000.0,
        change_percent=12.0,
        relative_volume_5m=6.0,
        breakout_percent=7.0,
        news_catalyst=True,
    )
    return MarketScout().evidence(observation)


def test_candidate_intelligence_is_explainable_and_not_a_trade_decision():
    result = CandidateIntelligenceService().analyze(_evidence())

    assert result.symbol == "TEST"
    assert 0.0 <= result.overall_score <= 100.0
    assert 0.0 <= result.confidence <= 100.0
    assert result.catalyst_score == 100.0
    assert result.reasons
    assert "TEST:" in result.explanation
    assert "score" in result.explanation


def test_deeper_evidence_improves_intelligence_when_positive():
    service = CandidateIntelligenceService()
    base = service.analyze(_evidence())
    enriched = service.analyze(
        _evidence(),
        CandidateIntelligenceInput(
            prediction_accuracy=90.0,
            strategy_evidence=85.0,
            robustness=90.0,
            downside_risk=10.0,
            confidence=88.0,
        ),
    )

    assert enriched.overall_score > base.overall_score
    assert enriched.prediction_accuracy == 90.0
    assert enriched.robustness == 90.0
    assert enriched.confidence == 88.0
    assert "strong historical prediction accuracy" in enriched.reasons
    assert "strong strategy evidence" in enriched.reasons
    assert "robust across independent evidence" in enriched.reasons


def test_rank_orders_candidates_by_intelligence_score():
    scout = MarketScout()
    service = CandidateIntelligenceService()
    weak = scout.evidence(
        MarketObservation(
            symbol="WEAK",
            asset_type=AssetType.STOCK,
            price=10.0,
            volume=100_000.0,
            average_volume=100_000.0,
            change_percent=1.0,
        )
    )
    strong = _evidence()

    ranked = service.rank([weak, strong])

    assert [item.symbol for item in ranked] == ["TEST", "WEAK"]
