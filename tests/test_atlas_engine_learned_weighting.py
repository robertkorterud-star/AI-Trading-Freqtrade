from datetime import datetime

from atlas.algorithms.base import Action
from atlas.core.config import AtlasConfig
from atlas.core.engine import AtlasEngine
from atlas.models.analysis_result import AnalysisResult
from atlas.market.asset import Asset
from atlas.market.asset_type import AssetType
from atlas.trading.agent_performance_tracker import (
    AgentPerformanceTracker,
)


def test_atlas_engine_uses_persisted_learned_agent_weights(
    monkeypatch,
    tmp_path,
):
    storage = tmp_path / "agent_performance.json"
    database = tmp_path / "atlas.db"

    tracker = AgentPerformanceTracker(
        storage_path=storage,
    )

    for _ in range(20):
        tracker.record(
            "Technical Analyst",
            True,
            action="BUY",
        )

    for _ in range(20):
        tracker.record(
            "News Analyst",
            False,
            action="BUY",
        )

    # Simulate a fresh ATLAS process with isolated persistence.
    config = AtlasConfig(
        agent_performance_storage=str(storage),
        database_path=str(database),
    )

    engine = AtlasEngine(config=config)

    def fake_analyze(symbol, exclude=None):
        return [
            AnalysisResult(
                symbol=symbol,
                analyst="Technical Analyst",
                action=Action.BUY,
                confidence=90.0,
                evidence=90.0,
                reasoning=["Strong technical evidence."],
            ),
            AnalysisResult(
                symbol=symbol,
                analyst="News Analyst",
                action=Action.BUY,
                confidence=90.0,
                evidence=90.0,
                reasoning=["News signal."],
            ),
        ]

    monkeypatch.setattr(
        engine.analysis_service,
        "analyze",
        fake_analyze,
    )

    monkeypatch.setattr(
        engine,
        "discover_candidates",
        lambda limit=3, minimum_score=0.0: [
            type(
                "Candidate",
                (),
                {
                    "symbol": "BTC-USD",
                    "score": 1.0,
                    "asset": Asset(
                        symbol="BTC-USD",
                        name="Bitcoin",
                        asset_type=AssetType.CRYPTO,
                        market="crypto",
                        currency="USD",
                    ),
                },
            )()
        ],
    )

    engine.market_data.snapshot = lambda symbol, interval="5m", limit=100: object()
    engine.algorithm_pipeline.analyze = lambda symbol, snapshot: (None, [])

    results = engine.decide_candidates(
        limit=1,
    )

    assert len(results) == 1

    decision = results[0]["decision"]

    assert decision.agent_weights

    assert (
        decision.agent_weights["Technical Analyst"]
        > decision.agent_weights["News Analyst"]
    )

    assert decision.action.value == "BUY"
    assert decision.confidence > 0.0
    assert decision.dominant_action == Action.BUY
    assert decision.dominant_weight > 0.0
