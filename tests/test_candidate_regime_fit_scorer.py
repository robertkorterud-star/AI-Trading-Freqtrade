from atlas.market.candidate_regime_fit_scorer import (
    CandidateRegimeFitScorer,
)
from atlas.models.action import Action
from atlas.models.decision_result import DecisionResult
from atlas.trading.strategy_memory_regime_decision_adapter import (
    StrategyMemoryRegimeDecision,
)


def make_decision(
    symbol="BTC-USD",
    action=Action.BUY,
):
    return DecisionResult(
        symbol=symbol,
        action=action,
        confidence=85.0,
        evidence=90.0,
        robustness=82.0,
        decision_margin=25.0,
    )


def make_regime_decision(
    symbol="BTC-USD",
    strategy="Momentum",
    confidence=80.0,
    robust_winner=True,
):
    return StrategyMemoryRegimeDecision(
        symbol=symbol,
        regime="LOW_VOLATILITY",
        strategy=strategy,
        action=Action.HOLD,
        confidence=confidence,
        independent_run_count=8,
        robust_winner=robust_winner,
    )


def test_missing_regime_decision_is_neutral():
    score = CandidateRegimeFitScorer.score(
        make_decision(),
        None,
    )

    assert score == 50.0


def test_non_robust_regime_recommendation_is_neutral():
    score = CandidateRegimeFitScorer.score(
        make_decision(),
        make_regime_decision(
            robust_winner=False,
        ),
    )

    assert score == 50.0


def test_missing_strategy_is_neutral():
    score = CandidateRegimeFitScorer.score(
        make_decision(),
        make_regime_decision(
            strategy=None,
        ),
    )

    assert score == 50.0


def test_hold_decision_remains_neutral():
    score = CandidateRegimeFitScorer.score(
        make_decision(
            action=Action.HOLD,
        ),
        make_regime_decision(
            confidence=95.0,
        ),
    )

    assert score == 50.0


def test_robust_regime_memory_provides_contextual_fit_score():
    score = CandidateRegimeFitScorer.score(
        make_decision(),
        make_regime_decision(
            confidence=80.0,
        ),
    )

    assert score == 80.0


def test_regime_fit_score_is_clamped_to_100():
    score = CandidateRegimeFitScorer.score(
        make_decision(),
        make_regime_decision(
            confidence=150.0,
        ),
    )

    assert score == 100.0


def test_symbol_mismatch_is_rejected():
    try:
        CandidateRegimeFitScorer.score(
            make_decision(
                symbol="BTC-USD",
            ),
            make_regime_decision(
                symbol="ETH-USD",
            ),
        )
    except ValueError as exc:
        assert (
            str(exc)
            == "Decision and regime decision symbols must match."
        )
    else:
        raise AssertionError(
            "Expected ValueError for symbol mismatch."
        )
