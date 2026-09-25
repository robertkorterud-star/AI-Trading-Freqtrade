from atlas.core.config import AtlasConfig
from atlas.core.engine import AtlasEngine
from atlas.models.action import Action
from atlas.models.decision_result import DecisionResult


def test_atlas_engine_records_prediction_before_modern_execution(monkeypatch):
    config = AtlasConfig(trading_mode="paper", paper_trading=True)
    engine = AtlasEngine(config=config)

    decision = DecisionResult(
        symbol="BTC-USD",
        action=Action.BUY,
        confidence=95.0,
        evidence=95.0,
    )

    events = []

    selected = {
        "symbol": "BTC-USD",
        "discovery_score": 100.0,
        "analysis": [],
        "decision": decision,
    }

    monkeypatch.setattr(
        engine,
        "decide_candidates",
        lambda limit=3, minimum_score=0.0: [selected],
    )
    monkeypatch.setattr(
        engine,
        "select_best_candidate",
        lambda candidates, investable_only=False: selected,
    )
    monkeypatch.setattr(
        engine,
        "_get_market_snapshot",
        lambda symbol: type("Snapshot", (), {"price": 100000.0})(),
    )
    monkeypatch.setattr(
        engine.prediction_evaluator,
        "evaluate_ready",
        lambda current_prices_usd: [],
    )
    monkeypatch.setattr(
        engine.analysis_snapshot_builder,
        "build",
        lambda **kwargs: type("Snapshot", (), {})(),
    )
    monkeypatch.setattr(
        engine.analysis_snapshot_repository,
        "save",
        lambda snapshot: None,
    )
    monkeypatch.setattr(
        engine.report,
        "print_decision",
        lambda decision: events.append("report"),
    )
    monkeypatch.setattr(
        engine.prediction_tracker,
        "record",
        lambda **kwargs: events.append("prediction"),
    )
    monkeypatch.setattr(
        engine.decision_execution_service,
        "execute",
        lambda decision, price=None, analysis_snapshot_id=None: events.append("execution"),
    )

    engine.start()

    assert events == ["report", "prediction", "execution"]


def test_atlas_engine_passes_saved_snapshot_id_to_modern_execution(monkeypatch):
    config = AtlasConfig(trading_mode="paper", paper_trading=True)
    engine = AtlasEngine(config=config)

    decision = DecisionResult(
        symbol="BTC-USD",
        action=Action.BUY,
        confidence=95.0,
        evidence=95.0,
    )

    selected = {
        "symbol": "BTC-USD",
        "discovery_score": 100.0,
        "analysis": [],
        "decision": decision,
    }

    monkeypatch.setattr(
        engine,
        "decide_candidates",
        lambda limit=3, minimum_score=0.0: [selected],
    )
    monkeypatch.setattr(
        engine,
        "select_best_candidate",
        lambda candidates, investable_only=False: selected,
    )
    monkeypatch.setattr(
        engine,
        "_get_market_snapshot",
        lambda symbol: type("Snapshot", (), {"price": 100000.0})(),
    )
    monkeypatch.setattr(
        engine.prediction_evaluator,
        "evaluate_ready",
        lambda current_prices_usd: [],
    )
    monkeypatch.setattr(
        engine.analysis_snapshot_builder,
        "build",
        lambda **kwargs: type("Snapshot", (), {"database_id": None})(),
    )

    def save_snapshot(snapshot):
        snapshot.database_id = 321
        decision.analysis_snapshot_id = 321

    monkeypatch.setattr(
        engine.analysis_snapshot_repository,
        "save",
        save_snapshot,
    )
    monkeypatch.setattr(
        engine.report,
        "print_decision",
        lambda decision: None,
    )
    monkeypatch.setattr(
        engine.prediction_tracker,
        "record",
        lambda **kwargs: None,
    )

    executions = []

    monkeypatch.setattr(
        engine.decision_execution_service,
        "execute",
        lambda decision, price=None, analysis_snapshot_id=None: executions.append(
            (decision, price, analysis_snapshot_id)
        ),
    )

    engine.start()

    assert executions == [(decision, 100000.0, 321)]
