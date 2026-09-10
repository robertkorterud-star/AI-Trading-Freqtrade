from atlas.core.engine import AtlasEngine
from atlas.core.config import AtlasConfig
from atlas.models.analysis_result import AnalysisResult
from atlas.models.action import Action


def buy_result() -> AnalysisResult:
    return AnalysisResult(
        symbol="BTC-USD",
        analyst="Technical Analyst",
        action=Action.BUY,
        confidence=100.0,
        evidence=100.0,
        reasoning=["Strong BUY signal."],
    )


def test_atlas_engine_modern_paper_execution_chain():
    """Ensure AtlasEngine wires the modern decision->risk->execution paper path."""
    config = AtlasConfig(trading_mode="paper", capital_limit=1_000_000.0)
    engine = AtlasEngine(config=config)

    # modern managers should be available on the engine and assigned to DecisionEngine
    assert getattr(engine, "risk_manager", None) is not None
    assert getattr(engine, "portfolio_manager", None) is not None
    assert getattr(engine.decision_engine, "risk_manager", None) is not None
    assert getattr(engine.decision_engine, "portfolio_manager", None) is not None

    # DecisionEngine should compute assessments itself when provided runtime context
    decision = engine.decision_engine.evaluate(
        [buy_result()],
        price=100_000.0,
        equity=100_000.0,
    )

    assert decision.action is Action.BUY
    assert decision.risk_assessment is not None
    assert decision.portfolio_assessment is not None

    # Use the modern DecisionExecutionService wired on the engine
    service = getattr(engine, "decision_execution_service", None)
    assert service is not None

    result = service.execute(decision, price=100_000.0)

    assert result is not None
    assert result.status.value == "SIMULATED"
    assert result.symbol == decision.symbol
    assert result.action is Action.BUY
    assert result.quantity == decision.risk_assessment.position_size

    # Verify portfolio accounting and trade record were created
    # engine.portfolio_service and engine.trading_service were exposed during wiring
    # Use engine.exchange to fetch USD/NOK at runtime (adapter will do same)
    # Provide a fake rate for test stability.
    class FakeExchange:
        def get_rate(self, base, target):
            return type("R", (), {"rate": 10.0})()

    engine.exchange = FakeExchange()

    portfolio_snapshot = engine.portfolio_service.as_dict(engine.exchange.get_rate("USD", "NOK").rate)
    assert portfolio_snapshot["position_count"] >= 1
    assert engine.trading_service.count() >= 1


def test_atlas_engine_persists_trade_history_across_instances(tmp_path):
    """Modern AtlasEngine instances share persisted paper-trade history."""
    config = AtlasConfig(
        trading_mode="paper",
        capital_limit=1_000_000.0,
        database_path=str(tmp_path / "atlas.db"),
    )

    first = AtlasEngine(config=config)

    first.trading_service.record_buy(
        symbol="BTC-USD",
        quantity=0.001,
        price_usd=65000.0,
        amount_nok=1000.0,
        reason="Persistence test.",
    )

    assert first.trading_service.count() == 1

    second = AtlasEngine(config=config)

    assert second.trading_service.count() == 1

    history = second.trading_service.history()

    assert history[0]["symbol"] == "BTC-USD"
    assert history[0]["action"] == "BUY"
    assert history[0]["amount_nok"] == 1000.0
    assert history[0]["reason"] == "Persistence test."
