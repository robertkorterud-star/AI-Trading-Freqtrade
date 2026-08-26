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


def test_recommends_best_strategy():
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
        == "Momentum"
    )

    assert recommendation.trade_count == 8
    assert (
        recommendation.average_trade_return_percent
        == 2.0
    )
    assert recommendation.total_return_percent == 16.0


def test_confidence_is_bounded():
    recommendation = (
        StrategyRegimeRecommender()
        .recommend(
            _summary(),
            "TRENDING_UP",
        )
    )

    assert 0.0 <= recommendation.confidence <= 100.0


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
    assert recommendation.trade_count == 0


def test_reason_contains_evidence():
    recommendation = (
        StrategyRegimeRecommender()
        .recommend(
            _summary(),
            "TRENDING_UP",
        )
    )

    assert "Momentum" in recommendation.reason
    assert "8 trades" in recommendation.reason
    assert "2.000%" in recommendation.reason


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
