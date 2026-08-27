from atlas.trading.regime_strategy_backtest import (
    RegimeStrategyBacktestSummary,
    RegimeTradeResult,
)
from atlas.trading.strategy_regime_recommendation import (
    StrategyRegimeRecommendation,
    StrategyRegimeRecommender,
)


def _summary():
    return RegimeStrategyBacktestSummary(
        results=(
            RegimeTradeResult(
                strategy_name="Trend Following",
                regime="TRENDING_UP",
                trade_count=10,
                winning_trades=7,
                losing_trades=3,
                total_return_percent=12.0,
                average_trade_return_percent=1.2,
            ),
            RegimeTradeResult(
                strategy_name="Momentum",
                regime="TRENDING_UP",
                trade_count=8,
                winning_trades=6,
                losing_trades=2,
                total_return_percent=16.0,
                average_trade_return_percent=2.0,
            ),
            RegimeTradeResult(
                strategy_name="Mean Reversion",
                regime="TRENDING_UP",
                trade_count=5,
                winning_trades=2,
                losing_trades=3,
                total_return_percent=-4.0,
                average_trade_return_percent=-0.8,
            ),
        )
    )


def test_historical_winner_is_not_automatically_robust():
    recommendation = (
        StrategyRegimeRecommender()
        .recommend(
            _summary(),
            "TRENDING_UP",
        )
    )

    assert isinstance(
        recommendation,
        StrategyRegimeRecommendation,
    )

    assert (
        recommendation.recommended_strategy
        is None
    )

    assert recommendation.robust_winner is False
    assert recommendation.trade_count == 8
    assert recommendation.win_rate_percent == 75.0
    assert recommendation.evidence_strength == "WEAK"


def test_robust_winner_requires_sufficient_evidence():
    summary = RegimeStrategyBacktestSummary(
        results=(
            RegimeTradeResult(
                strategy_name="Momentum",
                regime="TRENDING_UP",
                trade_count=20,
                winning_trades=15,
                losing_trades=5,
                total_return_percent=40.0,
                average_trade_return_percent=2.0,
            ),
        )
    )

    recommendation = (
        StrategyRegimeRecommender()
        .recommend(
            summary,
            "TRENDING_UP",
        )
    )

    assert (
        recommendation.recommended_strategy
        == "Momentum"
    )

    assert recommendation.robust_winner is True
    assert recommendation.evidence_strength == "STRONG"
    assert recommendation.confidence >= 30.0


def test_small_sample_is_not_high_confidence():
    summary = RegimeStrategyBacktestSummary(
        results=(
            RegimeTradeResult(
                strategy_name="Momentum",
                regime="LOW_VOLATILITY",
                trade_count=3,
                winning_trades=3,
                losing_trades=0,
                total_return_percent=23.619,
                average_trade_return_percent=7.873,
            ),
        )
    )

    recommendation = (
        StrategyRegimeRecommender()
        .recommend(
            summary,
            "LOW_VOLATILITY",
        )
    )

    assert (
        recommendation.recommended_strategy
        is None
    )

    assert recommendation.robust_winner is False
    assert recommendation.trade_count == 3
    assert recommendation.win_rate_percent == 100.0
    assert recommendation.evidence_strength == "WEAK"
    assert recommendation.confidence < 30.0


def test_one_trade_is_very_weak_evidence():
    summary = RegimeStrategyBacktestSummary(
        results=(
            RegimeTradeResult(
                strategy_name="Mean Reversion",
                regime="RANGING",
                trade_count=1,
                winning_trades=1,
                losing_trades=0,
                total_return_percent=1.353,
                average_trade_return_percent=1.353,
            ),
        )
    )

    recommendation = (
        StrategyRegimeRecommender()
        .recommend(
            summary,
            "RANGING",
        )
    )

    assert (
        recommendation.recommended_strategy
        is None
    )

    assert recommendation.robust_winner is False
    assert recommendation.evidence_strength == (
        "VERY_WEAK"
    )

    assert recommendation.confidence < 15.0


def test_unknown_regime_returns_no_recommendation():
    recommendation = (
        StrategyRegimeRecommender()
        .recommend(
            _summary(),
            "RANGING",
        )
    )

    assert recommendation.recommended_strategy is None
    assert recommendation.confidence == 0.0
    assert recommendation.evidence_strength == (
        "VERY_WEAK"
    )
    assert recommendation.robust_winner is False
    assert recommendation.trade_count == 0


def test_reason_contains_weak_evidence():
    recommendation = (
        StrategyRegimeRecommender()
        .recommend(
            _summary(),
            "TRENDING_UP",
        )
    )

    assert "Momentum" in recommendation.reason
    assert "8 trades" in recommendation.reason
    assert "75.0% win rate" in recommendation.reason
    assert "2.000%" in recommendation.reason
    assert "WEAK" in recommendation.reason


def test_evidence_strength_scales_with_sample_size():
    recommender = StrategyRegimeRecommender()

    assert (
        recommender._evidence_strength(1)
        == "VERY_WEAK"
    )

    assert (
        recommender._evidence_strength(3)
        == "WEAK"
    )

    assert (
        recommender._evidence_strength(10)
        == "MODERATE"
    )

    assert (
        recommender._evidence_strength(20)
        == "STRONG"
    )


def test_deterministic():
    recommender = StrategyRegimeRecommender()
    summary = _summary()

    first = recommender.recommend(
        summary,
        "TRENDING_UP",
    )

    second = recommender.recommend(
        summary,
        "TRENDING_UP",
    )

    assert first == second
