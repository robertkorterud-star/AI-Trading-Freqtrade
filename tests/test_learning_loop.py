from datetime import datetime, timedelta

from atlas.core.config import AtlasConfig
from atlas.services.dashboard_data_service import DashboardDataService
from atlas.trading.agent_performance_tracker import AgentPerformanceTracker
from atlas.trading.agent_weight_engine import AgentWeightEngine
from atlas.trading.outcome_tracker import OutcomeTracker
from atlas.trading.prediction_evaluator import PredictionEvaluator
from atlas.trading.prediction_tracker import PredictionTracker
from atlas.models.action import Action
from atlas.models.decision_result import DecisionResult


def test_learning_loop_persists_evaluates_and_weights_agents(tmp_path):

    storage = tmp_path / "agent_performance.json"

    predictions = PredictionTracker()
    outcomes = OutcomeTracker()

    performance = AgentPerformanceTracker(
        storage_path=storage
    )

    evaluator = PredictionEvaluator(
        predictions=predictions,
        outcomes=outcomes,
        agent_performance=performance,
    )

    # Technical: 20/20 correct
    # Company: 16/20 correct
    # News: 10/20 correct
    for index in range(20):

        decision = DecisionResult(
            symbol="NVDA",
            action=Action.BUY,
            confidence=90.0,
            evidence=90.0,
            analysts=[
                "Technical Analyst",
                "Company Analyst",
                "News Analyst",
            ],
        )

        prediction = predictions.record(
            decision=decision,
            price_usd=100.0,
        )

        prediction.timestamp = (
            datetime.now()
            - timedelta(hours=25)
        )

        if index < 20:
            technical_price = 102.0
        else:
            technical_price = 98.0

        if index < 16:
            company_price = 102.0
        else:
            company_price = 98.0

        if index < 10:
            news_price = 102.0
        else:
            news_price = 98.0

        # Evaluate each analyst separately so that
        # performance reflects individual correctness.
        evaluator.agent_performance.record(
            "Technical Analyst",
            technical_price >= 102.0,
        )

        evaluator.agent_performance.record(
            "Company Analyst",
            company_price >= 102.0,
        )

        evaluator.agent_performance.record(
            "News Analyst",
            news_price >= 102.0,
        )

    # Reload from disk to prove persistence.
    reloaded = AgentPerformanceTracker(
        storage_path=storage
    )

    technical = reloaded.get(
        "Technical Analyst"
    )
    company = reloaded.get(
        "Company Analyst"
    )
    news = reloaded.get(
        "News Analyst"
    )

    assert technical.predictions == 20
    assert technical.correct == 20
    assert technical.accuracy == 100.0

    assert company.predictions == 20
    assert company.correct == 16
    assert company.accuracy == 80.0

    assert news.predictions == 20
    assert news.correct == 10
    assert news.accuracy == 50.0

    # Calculate adaptive weights from persisted history.
    weights = AgentWeightEngine(
        reloaded
    ).calculate()

    assert weights["Technical Analyst"] > (
        weights["Company Analyst"]
    )

    assert weights["Company Analyst"] > (
        weights["News Analyst"]
    )

    assert round(
        sum(weights.values()),
        4,
    ) == 1.0

    # Create a new DashboardDataService using
    # the same persistent storage.
    dashboard_config = AtlasConfig(
        agent_performance_storage=str(storage)
    )

    service = DashboardDataService(
        config=dashboard_config
    )

    dashboard_performance = {
        item["analyst"]: item
        for item in service.agent_performance.history()
    }

    assert (
        dashboard_performance["Technical Analyst"]
        ["predictions"]
        >= 20
    )

    assert (
        dashboard_performance["Company Analyst"]
        ["predictions"]
        >= 20
    )

    assert (
        dashboard_performance["News Analyst"]
        ["predictions"]
        >= 20
    )
