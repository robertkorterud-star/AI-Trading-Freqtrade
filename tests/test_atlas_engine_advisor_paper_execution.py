from types import SimpleNamespace

from atlas.core.engine import AtlasEngine
from atlas.models.action import Action


def test_advisor_mode_with_paper_trading_executes_modern_path(monkeypatch):
    engine = AtlasEngine()
    engine.config.trading_mode = "advisor"
    engine.config.paper_trading = True

    decision = SimpleNamespace(
        symbol="BTC-USD",
        action=Action.BUY,
        confidence=95.0,
    )
    selected = {
        "symbol": "BTC-USD",
        "decision": decision,
        "analysis": [SimpleNamespace()],
    }
    calls = []

    monkeypatch.setattr(engine, "decide_candidates", lambda limit=3: [selected])
    monkeypatch.setattr(
        engine,
        "select_best_candidate",
        lambda candidates, investable_only=False: selected,
    )
    monkeypatch.setattr(
        engine,
        "_get_market_snapshot",
        lambda symbol: SimpleNamespace(price=100000.0),
    )
    monkeypatch.setattr(
        engine.prediction_evaluator,
        "evaluate_ready",
        lambda current_prices_usd: [],
    )
    monkeypatch.setattr(engine.report, "print_decision", lambda decision: None)
    monkeypatch.setattr(engine.prediction_tracker, "record", lambda **kwargs: None)
    monkeypatch.setattr(engine.event_repository, "publish", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        engine.analysis_snapshot_builder,
        "build",
        lambda **kwargs: SimpleNamespace(database_id=1),
    )
    monkeypatch.setattr(
        engine.analysis_snapshot_repository,
        "save",
        lambda snapshot: None,
    )

    def fake_execute(decision, price=None, **kwargs):
        calls.append((decision, price))
        return {"executed": True, "symbol": decision.symbol, "action": "BUY"}

    monkeypatch.setattr(engine.decision_execution_service, "execute", fake_execute)

    engine.start()

    assert calls == [(decision, 100000.0)]
