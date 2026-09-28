from atlas.core.engine import AtlasEngine
from atlas.core.logger import get_logger
from atlas.market.candidate_decision_ranker import CandidateDecisionRanker
from atlas.models.action import Action
from atlas.models.decision_result import DecisionResult


def make_candidate(symbol, expected_return):
    decision = DecisionResult(
        symbol=symbol,
        action=Action.BUY,
        confidence=80.0,
        evidence=80.0,
        robustness=80.0,
        decision_margin=20.0,
        expected_return=expected_return,
    )

    return {
        "symbol": symbol,
        "discovery_score": 90.0,
        "decision": decision,
        "regime_decision": None,
    }


def test_atlas_engine_selects_candidate_with_best_risk_adjusted_net_return():
    engine = AtlasEngine.__new__(AtlasEngine)
    engine.candidate_decision_ranker = CandidateDecisionRanker()
    engine.logger = get_logger("ATLAS-test")

    candidates = [
        make_candidate("LOW-RETURN", 0.0030),
        make_candidate("HIGH-RETURN", 0.0200),
    ]

    selected = engine.select_best_candidate(candidates)

    assert selected is not None
    assert selected["symbol"] == "HIGH-RETURN"
    assert selected["decision"].expected_return == 0.0200
    assert selected["ranking_evidence"].symbol == "HIGH-RETURN"
    assert selected["ranking_evidence"].net_expected_return > 0.0
    assert selected["ranking_evidence"].risk_adjusted_net_return > 0.0
    assert selected["selection_report"].symbol == "HIGH-RETURN"

def test_atlas_engine_can_filter_only_known_economically_ineligible_buy():
    engine = AtlasEngine.__new__(AtlasEngine)
    engine.candidate_decision_ranker = CandidateDecisionRanker()
    engine.logger = get_logger("ATLAS-test")

    known_unprofitable = make_candidate(
        "KNOWN-UNPROFITABLE",
        0.0024,
    )
    known_unprofitable["decision"].expected_return_ready = True

    unknown = make_candidate(
        "UNKNOWN",
        0.0,
    )
    unknown["decision"].expected_return_ready = False

    selected = engine.select_best_candidate(
        [known_unprofitable, unknown],
        economically_eligible_only=True,
    )

    assert selected is not None
    assert selected["symbol"] == "UNKNOWN"

