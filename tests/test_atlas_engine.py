from atlas.core.engine import AtlasEngine
from atlas.trading.trading_runtime import TradingRuntime


def test_atlas_engine_uses_btc_usd_symbol():

    engine = AtlasEngine()

    results = engine.analysis_service.analyze("BTC-USD")

    assert results
    assert all(
        result.symbol == "BTC-USD"
        for result in results
    )


def test_atlas_engine_has_trading_runtime():

    engine = AtlasEngine()

    assert isinstance(
        engine.trading_runtime,
        TradingRuntime,
    )


def test_atlas_engine_end_to_end_paper_buy():

    engine = AtlasEngine()

    engine.config.trading_mode = "paper"
    engine.config.paper_trading = True

    decision = make_buy_decision = __import__(
        "atlas.models.decision_result",
        fromlist=["DecisionResult"],
    ).DecisionResult(
        symbol="BTC-USD",
        action=__import__(
            "atlas.models.action",
            fromlist=["Action"],
        ).Action.BUY,
        confidence=95.0,
        evidence=95.0,
    )

    result = engine.trading_runtime.execute(
        decision=decision,
        price_usd=65000,
        usd_nok=9.50,
        amount_nok=1000,
    )

    assert result["executed"] is True
    assert result["action"] == "BUY"
    assert result["symbol"] == "BTC-USD"
    assert result["amount_nok"] == 1000


def test_atlas_engine_end_to_end_paper_buy_and_sell_with_profit():

    engine = AtlasEngine()

    engine.config.trading_mode = "paper"
    engine.config.paper_trading = True

    buy_decision = __import__(
        "atlas.models.decision_result",
        fromlist=["DecisionResult"],
    ).DecisionResult(
        symbol="BTC-USD",
        action=__import__(
            "atlas.models.action",
            fromlist=["Action"],
        ).Action.BUY,
        confidence=95.0,
        evidence=95.0,
    )

    sell_decision = __import__(
        "atlas.models.decision_result",
        fromlist=["DecisionResult"],
    ).DecisionResult(
        symbol="BTC-USD",
        action=__import__(
            "atlas.models.action",
            fromlist=["Action"],
        ).Action.SELL,
        confidence=95.0,
        evidence=95.0,
    )

    buy_result = engine.trading_runtime.execute(
        decision=buy_decision,
        price_usd=65000,
        usd_nok=9.50,
        amount_nok=1000,
    )

    assert buy_result["executed"] is True
    assert buy_result["action"] == "BUY"

    sell_result = engine.trading_runtime.execute(
        decision=sell_decision,
        price_usd=70000,
        usd_nok=9.50,
        amount_nok=1000,
    )

    assert sell_result["executed"] is True
    assert sell_result["action"] == "SELL"
    assert sell_result["realized_pnl_nok"] > 0

    portfolio = engine.trading_runtime.controller.trader.portfolio.as_dict(
        9.50
    )

    assert portfolio["profit_vault_nok"] > 0
    assert portfolio["positions"] == []


def test_atlas_engine_start_sends_decision_to_paper_runtime(monkeypatch):

    from atlas.models.action import Action
    from atlas.models.decision_result import DecisionResult

    engine = AtlasEngine()

    engine.config.trading_mode = "paper"
    engine.config.paper_trading = True

    decision = DecisionResult(
        symbol="BTC-USD",
        action=Action.BUY,
        confidence=95.0,
        evidence=95.0,
    )

    calls = []

    def fake_analyze(symbol):
        return []

    def fake_evaluate(results):
        return decision

    def fake_print_decision(decision):
        pass

    def fake_execute(
        decision,
        price_usd,
        usd_nok,
        amount_nok=1000.0,
    ):
        calls.append({
            "decision": decision,
            "price_usd": price_usd,
            "usd_nok": usd_nok,
            "amount_nok": amount_nok,
        })

        return {
            "executed": True,
            "action": "BUY",
            "symbol": "BTC-USD",
        }

    monkeypatch.setattr(
        engine.analysis_service,
        "analyze",
        fake_analyze,
    )

    monkeypatch.setattr(
        engine.decision_engine,
        "evaluate",
        fake_evaluate,
    )

    monkeypatch.setattr(
        engine.report,
        "print_decision",
        fake_print_decision,
    )

    monkeypatch.setattr(
        engine.trading_runtime,
        "execute",
        fake_execute,
    )

    engine.start()

    assert len(calls) == 1
    assert calls[0]["decision"] == decision
    assert calls[0]["decision"].symbol == "BTC-USD"
