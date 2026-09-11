from atlas.database.analysis_snapshot_repository import AnalysisSnapshotRepository
from atlas.database.connection import Database
from atlas.database.schema import initialize_database
from atlas.models.action import Action
from atlas.models.analysis_result import AnalysisResult
from atlas.models.decision_result import DecisionResult
from atlas.services.analysis_snapshot_builder import AnalysisSnapshotBuilder


def test_analysis_snapshot_persists_news_items_used_by_news_analyst(tmp_path):
    database = Database(tmp_path / "atlas.db")
    initialize_database(database)
    repository = AnalysisSnapshotRepository(database)

    news_items = [
        {
            "title": "BTC institutional demand rises",
            "source": "Example News",
            "summary": "Institutional demand increased.",
            "url": "https://example.com/btc",
            "sentiment": "BUY",
        }
    ]

    result = AnalysisResult(
        analyst="News Analyst",
        symbol="BTC-USD",
        action=Action.BUY,
        confidence=91.0,
        evidence=95.0,
        reasoning=["Positive news supports BUY."],
        metadata={"news_items": news_items},
    )

    decision = DecisionResult(
        symbol="BTC-USD",
        action=Action.BUY,
        confidence=91.0,
        evidence=95.0,
        analysts=["News Analyst"],
        agent_weights={"News Analyst": 1.0},
        dominant_action=Action.BUY,
        dominant_weight=1.0,
        reasoning=["News supports BUY."],
    )

    snapshot = AnalysisSnapshotBuilder().build(
        symbol="BTC-USD",
        results=[result],
        decision=decision,
    )
    snapshot_id = repository.save(snapshot)
    restored = repository.get_by_id(snapshot_id)

    assert restored is not None
    restored_news = restored.results[0]["metadata"]["news_items"]
    assert restored_news == news_items
    assert restored_news[0]["title"] == "BTC institutional demand rises"
    assert restored_news[0]["url"] == "https://example.com/btc"
