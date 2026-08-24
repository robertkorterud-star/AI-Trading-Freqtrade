from unittest.mock import patch

import pandas as pd

from atlas.core.config import AtlasConfig
from atlas.core.engine import AtlasEngine
from atlas.trading.trading_runtime import TradingRuntime


def test_atlas_engine_uses_btc_usd_symbol():

    history = pd.DataFrame(
        {
            "Close": [
                60000 + i
                for i in range(60)
            ]
        }
    )

    fake_ticker = type(
        "FakeTicker",
        (),
        {
            "history": lambda self, period: history,
            "fast_info": {
                "lastPrice": 65000.0,
                "previousClose": 64000.0,
            },
        },
    )()

    with patch(
        "atlas.adapters.market_data.yf.Ticker",
        return_value=fake_ticker,
    ):

        engine = AtlasEngine()

        results = engine.analysis_service.analyze(
            "BTC-USD"
        )

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


def test_atlas_config_defaults_to_safe_advisor_mode():

    config = AtlasConfig()

    assert config.trading_mode == "advisor"
    assert config.paper_trading is True
    assert config.capital_limit == 5000.0


def test_atlas_config_supports_paper_mode():

    config = AtlasConfig(
        trading_mode="paper",
        paper_trading=True,
    )

    assert config.trading_mode == "paper"
    assert config.paper_trading is True
    assert config.capital_limit == 5000.0


def test_atlas_engine_start_evaluates_previous_predictions(
    monkeypatch,
    tmp_path,
):

    from datetime import datetime, timedelta

    from atlas.models.action import Action
    from atlas.models.decision_result import DecisionResult
    from atlas.trading.prediction_record import PredictionRecord

    config = AtlasConfig(
        agent_performance_storage=(
            str(tmp_path / "agent_performance.json")
        ),
        database_path=(
            str(tmp_path / "atlas_test.db")
        ),
    )

    engine = AtlasEngine(
        config=config
    )

    old_prediction = PredictionRecord(
        symbol="BTC-USD",
        action="BUY",
        confidence=90.0,
        evidence=90.0,
        price_usd=60000.0,
        timestamp=datetime.now() - timedelta(hours=25),
        analysts=[
            "Technical Analyst",
            "Company Analyst",
        ],
        reason="Test prediction",
    )

    engine.prediction_tracker.repository.save(
        old_prediction
    )

    calls = []

    def fake_snapshot(symbol):
        calls.append("snapshot")
        return type(
            "Snapshot",
            (),
            {"price": 61000.0},
        )()

    def fake_analyze(symbol):
        calls.append("analyze")
        return []

    def fake_evaluate(results):
        calls.append("decision")
        return DecisionResult(
            symbol="BTC-USD",
            action=Action.HOLD,
            confidence=70.0,
            evidence=70.0,
        )

    def fake_print_decision(decision):
        calls.append("report")

    monkeypatch.setattr(
        engine,
        "_get_market_snapshot",
        fake_snapshot,
    )

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

    engine.start()

    assert "snapshot" in calls
    assert "analyze" in calls
    assert "decision" in calls

    assert calls.index("snapshot") < calls.index("analyze")

    outcomes = engine.outcome_tracker.history()

    assert len(outcomes) == 1
    assert outcomes[0]["symbol"] == "BTC-USD"
    assert outcomes[0]["correct"] is True

    technical = engine.agent_performance.get(
        "Technical Analyst"
    )

    company = engine.agent_performance.get(
        "Company Analyst"
    )

    assert technical.predictions == 1
    assert technical.correct == 1

    assert company.predictions == 1
    assert company.correct == 1
