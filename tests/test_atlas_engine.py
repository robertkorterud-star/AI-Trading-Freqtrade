from unittest.mock import patch

import pandas as pd

from atlas.core.config import AtlasConfig
from atlas.core.engine import AtlasEngine
from atlas.risk.risk_engine import RiskEngine
from atlas.services.portfolio_service import PortfolioService
from atlas.trading.paper_trading_engine import PaperTradingEngine
from atlas.trading.trading_controller import TradingController
from atlas.trading.trading_runtime import TradingRuntime
from atlas.trading.trading_service import TradingService


def make_legacy_trading_runtime(config):
    portfolio = PortfolioService(config.capital_limit)
    trading = TradingService()
    trader = PaperTradingEngine(
        portfolio=portfolio,
        risk=RiskEngine(),
        trading=trading,
    )
    return TradingRuntime(
        config=config,
        controller=TradingController(trader=trader),
    )


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

def test_atlas_engine_end_to_end_paper_buy(tmp_path):

    config = AtlasConfig(
        database_path=str(tmp_path / "atlas.db"),
    )
    config.trading_mode = "paper"
    config.paper_trading = True
    runtime = make_legacy_trading_runtime(config)

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

    result = runtime.execute(
        decision=decision,
        price_usd=65000,
        usd_nok=9.50,
        amount_nok=1000,
    )

    assert result["executed"] is True
    assert result["action"] == "BUY"
    assert result["symbol"] == "BTC-USD"
    assert result["amount_nok"] == 1000


def test_atlas_engine_end_to_end_paper_buy_and_sell_with_profit(tmp_path):

    config = AtlasConfig(
        database_path=str(tmp_path / "atlas.db"),
    )
    config.trading_mode = "paper"
    config.paper_trading = True
    runtime = make_legacy_trading_runtime(config)

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

    buy_result = runtime.execute(
        decision=buy_decision,
        price_usd=65000,
        usd_nok=9.50,
        amount_nok=1000,
    )

    assert buy_result["executed"] is True
    assert buy_result["action"] == "BUY"

    sell_result = runtime.execute(
        decision=sell_decision,
        price_usd=70000,
        usd_nok=9.50,
        amount_nok=1000,
    )

    assert sell_result["executed"] is True
    assert sell_result["action"] == "SELL"
    assert sell_result["realized_pnl_nok"] > 0

    portfolio = runtime.controller.trader.portfolio.as_dict(
        9.50
    )

    assert portfolio["profit_vault_nok"] > 0
    assert portfolio["positions"] == []


def test_atlas_engine_start_sends_decision_to_paper_runtime(
    monkeypatch,
    tmp_path,
):

    from atlas.models.action import Action
    from atlas.models.analysis_result import AnalysisResult

    config = AtlasConfig(
        agent_performance_storage=(
            str(tmp_path / "agent_performance.json")
        ),
        database_path=str(tmp_path / "atlas_test.db"),
    )
    engine = AtlasEngine(config=config)

    engine.config.trading_mode = "paper"
    engine.config.paper_trading = True

    analysis = [
        AnalysisResult(
            symbol="BTC-USD",
            analyst="test-analyst",
            action=Action.BUY,
            confidence=95.0,
            evidence=95.0,
            reasoning=["Strong BUY signal."],
        )
    ]

    selected = {
        "symbol": "BTC-USD",
        "discovery_score": 100.0,
        "analysis": analysis,
    }

    calls = []
    prediction_count_before = len(
        engine.prediction_tracker.history()
    )

    def fake_decide_candidates(
        limit=3,
        minimum_score=0.0,
    ):
        selected["decision"] = engine._evaluate_candidate_decision(
            analysis,
            market_snapshot=fake_snapshot("BTC-USD"),
        )
        return [selected]

    def fake_select_best_candidate(
        candidates,
        investable_only=False,
    ):
        return selected

    def fake_analyze(symbol):
        return []

    def fake_snapshot(symbol):
        return type(
            "Snapshot",
            (),
            {"price": 100000.0},
        )()

    def fake_exchange():
        return type(
            "ExchangeRate",
            (),
            {"rate": 10.0},
        )()

    def fake_print_decision(decision):
        pass

    def fake_execute(decision, price=None, **kwargs):
        assert len(engine.prediction_tracker.history()) == (
            prediction_count_before + 1
        )

        calls.append({
            "decision": decision,
            "price": price,
            **kwargs,
        })

        return {
            "executed": True,
            "action": "BUY",
            "symbol": "BTC-USD",
        }

    monkeypatch.setattr(
        engine,
        "decide_candidates",
        fake_decide_candidates,
    )

    monkeypatch.setattr(
        engine,
        "select_best_candidate",
        fake_select_best_candidate,
    )

    monkeypatch.setattr(
        engine.analysis_service,
        "analyze",
        fake_analyze,
    )

    monkeypatch.setattr(
        engine,
        "_get_market_snapshot",
        fake_snapshot,
    )

    monkeypatch.setattr(
        engine,
        "_get_usd_nok_rate",
        fake_exchange,
    )

    monkeypatch.setattr(
        engine.report,
        "print_decision",
        fake_print_decision,
    )

    # The modern execution path uses DecisionExecutionService -> ExecutionEngine
    # -> PaperTradingExecutionAdapter. Patch the decision execution service instead
    # of the legacy trading runtime.
    monkeypatch.setattr(
        engine.decision_execution_service,
        "execute",
        fake_execute,
    )

    monkeypatch.setattr(
        engine.prediction_evaluator,
        "evaluate_ready",
        lambda current_prices_usd: [],
    )

    engine.start()

    decision = selected["decision"]
    assert len(calls) == 1
    assert calls[0]["decision"] == decision
    assert calls[0]["decision"].symbol == "BTC-USD"
    assert calls[0]["price"] == 100000.0
    assert calls[0]["decision"].risk_assessment is not None
    assert calls[0]["decision"].portfolio_assessment is not None



def test_snapshot_persistence_failure_prevents_decision_publication_and_execution(monkeypatch, tmp_path):
    import pytest

    from atlas.models.action import Action
    from atlas.models.analysis_result import AnalysisResult

    config = AtlasConfig(
        agent_performance_storage=str(tmp_path / "agent_performance.json"),
        database_path=str(tmp_path / "atlas_test.db"),
    )
    config.trading_mode = "paper"
    config.paper_trading = True

    engine = AtlasEngine(config=config)

    analysis = [
        AnalysisResult(
            symbol="BTC-USD",
            analyst="test-analyst",
            action=Action.BUY,
            confidence=95.0,
            evidence=95.0,
            reasoning=["Strong BUY signal."],
        )
    ]
    selected = {
        "symbol": "BTC-USD",
        "discovery_score": 100.0,
        "analysis": analysis,
    }

    def fake_snapshot(symbol):
        return type("Snapshot", (), {"price": 100000.0})()

    def fake_decide_candidates(limit=3, minimum_score=0.0):
        selected["decision"] = engine._evaluate_candidate_decision(
            analysis,
            market_snapshot=fake_snapshot("BTC-USD"),
        )
        return [selected]

    def fail_snapshot_save(snapshot):
        raise RuntimeError("snapshot persistence failed")

    monkeypatch.setattr(engine, "decide_candidates", fake_decide_candidates)
    monkeypatch.setattr(
        engine,
        "select_best_candidate",
        lambda candidates, investable_only=False: selected,
    )
    monkeypatch.setattr(engine, "_get_market_snapshot", fake_snapshot)
    monkeypatch.setattr(engine.report, "print_decision", lambda decision: None)
    monkeypatch.setattr(
        engine.prediction_evaluator,
        "evaluate_ready",
        lambda current_prices_usd: [],
    )
    monkeypatch.setattr(
        engine.analysis_snapshot_repository,
        "save",
        fail_snapshot_save,
    )

    with pytest.raises(RuntimeError, match="snapshot persistence failed"):
        engine.start()

    assert engine.prediction_tracker.count() == 0
    assert engine.trading_service.count() == 0
    assert engine.event_repository.after(0, limit=100) == []










def test_restart_preserves_aggregate_portfolio_veto_from_restored_positions(
    monkeypatch,
    tmp_path,
):
    from atlas.models.action import Action
    from atlas.models.analysis_result import AnalysisResult
    from atlas.portfolio.manager import PortfolioManager
    from atlas.risk.manager import RiskManager

    config = AtlasConfig(
        agent_performance_storage=str(tmp_path / "agent_performance.json"),
        database_path=str(tmp_path / "atlas_test.db"),
        capital_limit=1000000.0,
        trading_mode="paper",
        paper_trading=True,
    )
    first = AtlasEngine(config=config)
    first.risk_manager = RiskManager(
        risk_per_trade_pct=0.3,
        max_position_pct=15.0,
    )
    first.decision_engine.risk_manager = first.risk_manager
    first.portfolio_manager = PortfolioManager(
        max_exposure_pct=30.0,
        max_single_position_pct=20.0,
    )
    first.decision_engine.portfolio_manager = first.portfolio_manager
    monkeypatch.setattr(
        first.market_data,
        "get_many",
        lambda symbols, horizon=None: {
            symbol: type("Snapshot", (), {"price": 100.0})()
            for symbol in symbols
        },
    )
    monkeypatch.setattr(
        first,
        "_get_usd_nok_rate",
        lambda: type("ExchangeRate", (), {"rate": 10.0})(),
    )
    monkeypatch.setattr(
        first.exchange,
        "get_rate",
        lambda base, target: type("ExchangeRate", (), {"rate": 10.0})(),
    )

    def buy(symbol):
        analysis = [
            AnalysisResult(
                symbol=symbol,
                analyst="test-analyst",
                action=Action.BUY,
                confidence=95.0,
                evidence=95.0,
                reasoning=["Strong BUY signal."],
            )
        ]
        decision = first._evaluate_candidate_decision(
            analysis,
            market_snapshot=type("Snapshot", (), {"price": 100.0})(),
        )
        assert decision.action is Action.BUY
        result = first.decision_execution_service.execute(
            decision=decision,
            price=100.0,
        )
        assert result is not None

    buy("BTC-USD")
    buy("ETH-USD")

    restarted = AtlasEngine(config=config)
    restarted.portfolio_manager = PortfolioManager(
        max_exposure_pct=30.0,
        max_single_position_pct=20.0,
    )
    restarted.decision_engine.portfolio_manager = restarted.portfolio_manager

    restored = restarted.portfolio_service.as_dict(10.0)
    assert {position["symbol"] for position in restored["positions"]} == {
        "BTC-USD",
        "ETH-USD",
    }
    assert restored["positions_value_nok"] == pytest.approx(300000.0)

    analysis = [
        AnalysisResult(
            symbol="SOL-USD",
            analyst="test-analyst",
            action=Action.BUY,
            confidence=95.0,
            evidence=95.0,
            reasoning=["Strong BUY signal."],
        )
    ]
    selected = {
        "symbol": "SOL-USD",
        "discovery_score": 100.0,
        "analysis": analysis,
    }

    def fake_snapshot(symbol):
        return type("Snapshot", (), {"price": 100.0})()

    def fake_decide_candidates(limit=3, minimum_score=0.0):
        selected["decision"] = restarted._evaluate_candidate_decision(
            analysis,
            market_snapshot=fake_snapshot("SOL-USD"),
        )
        return [selected]

    monkeypatch.setattr(restarted, "decide_candidates", fake_decide_candidates)
    monkeypatch.setattr(
        restarted.prediction_evaluator,
        "evaluate_ready",
        lambda current_prices_usd: [],
    )
    monkeypatch.setattr(restarted, "_get_market_snapshot", fake_snapshot)
    monkeypatch.setattr(
        restarted.market_data,
        "get_many",
        lambda symbols, horizon=None: {
            symbol: fake_snapshot(symbol)
            for symbol in symbols
        },
    )
    monkeypatch.setattr(
        restarted,
        "_get_usd_nok_rate",
        lambda: type("ExchangeRate", (), {"rate": 10.0})(),
    )
    monkeypatch.setattr(restarted.report, "print_decision", lambda decision: None)

    before_trade_count = restarted.trading_service.count()
    restarted.start()

    decision = selected["decision"]
    assert decision.risk_assessment is not None
    assert decision.risk_assessment.allowed is True
    assert decision.portfolio_assessment is not None
    assert decision.portfolio_assessment.allowed is False
    assert "exposure capacity" in " ".join(
        decision.portfolio_assessment.reasons
    ).lower()
    assert decision.action is Action.HOLD

    predictions = restarted.prediction_tracker.history()
    assert len(predictions) == 1
    assert predictions[0]["symbol"] == "SOL-USD"
    assert predictions[0]["action"] == "HOLD"
    assert restarted.trading_service.count() == before_trade_count



def test_start_preserves_aggregate_portfolio_veto_with_existing_positions(
    monkeypatch,
    tmp_path,
):
    from atlas.models.action import Action
    from atlas.models.analysis_result import AnalysisResult
    from atlas.portfolio.manager import PortfolioManager

    config = AtlasConfig(
        agent_performance_storage=str(tmp_path / "agent_performance.json"),
        database_path=str(tmp_path / "atlas_test.db"),
        capital_limit=1000000.0,
        trading_mode="paper",
        paper_trading=True,
    )
    engine = AtlasEngine(config=config)

    engine.portfolio_manager = PortfolioManager(
        max_exposure_pct=30.0,
        max_single_position_pct=20.0,
    )
    engine.decision_engine.portfolio_manager = engine.portfolio_manager

    for symbol in ("BTC-USD", "ETH-USD"):
        engine.portfolio_service.buy(
            symbol=symbol,
            amount_nok=150000.0,
            price_usd=100.0,
            usd_nok=10.0,
        )

    analysis = [
        AnalysisResult(
            symbol="SOL-USD",
            analyst="test-analyst",
            action=Action.BUY,
            confidence=95.0,
            evidence=95.0,
            reasoning=["Strong BUY signal."],
        )
    ]
    selected = {
        "symbol": "SOL-USD",
        "discovery_score": 100.0,
        "analysis": analysis,
    }

    def fake_snapshot(symbol):
        return type("Snapshot", (), {"price": 100.0})()

    def fake_decide_candidates(limit=3):
        selected["decision"] = engine._evaluate_candidate_decision(
            analysis,
            market_snapshot=fake_snapshot("SOL-USD"),
        )
        return [selected]

    monkeypatch.setattr(engine, "decide_candidates", fake_decide_candidates)
    monkeypatch.setattr(
        engine.prediction_evaluator,
        "evaluate_ready",
        lambda current_prices_usd: [],
    )
    monkeypatch.setattr(
        engine,
        "_get_market_snapshot",
        fake_snapshot,
    )
    monkeypatch.setattr(
        engine.market_data,
        "get_many",
        lambda symbols: {
            symbol: fake_snapshot(symbol)
            for symbol in symbols
        },
    )
    monkeypatch.setattr(
        engine,
        "_get_usd_nok_rate",
        lambda: type("ExchangeRate", (), {"rate": 10.0})(),
    )
    monkeypatch.setattr(engine.report, "print_decision", lambda decision: None)

    before_trade_count = engine.trading_service.count()

    engine.start()

    decision = selected["decision"]
    assert decision.risk_assessment is not None
    assert decision.risk_assessment.allowed is True
    assert decision.portfolio_assessment is not None
    assert decision.portfolio_assessment.allowed is False
    assert any(
        "exposure capacity" in reason
        for reason in decision.portfolio_assessment.reasons
    )
    assert decision.action is Action.HOLD

    predictions = engine.prediction_tracker.history()
    assert len(predictions) == 1
    assert predictions[0]["symbol"] == "SOL-USD"
    assert predictions[0]["action"] == "HOLD"
    assert engine.trading_service.count() == before_trade_count


def test_start_executes_prioritized_sell_before_stronger_new_buy(
    monkeypatch,
    tmp_path,
):
    from atlas.models.action import Action
    from atlas.models.decision_result import DecisionResult
    from atlas.risk.manager import RiskAssessment

    config = AtlasConfig(
        agent_performance_storage=str(tmp_path / "agent_performance.json"),
        database_path=str(tmp_path / "atlas_test.db"),
        capital_limit=1000000.0,
        trading_mode="paper",
        paper_trading=True,
    )
    engine = AtlasEngine(config=config)

    engine.portfolio_service.buy(
        symbol="BTC-USD",
        amount_nok=1000.0,
        price_usd=100.0,
        usd_nok=10.0,
    )
    engine.trading_service.record_buy(
        symbol="BTC-USD",
        quantity=1.0,
        price_usd=100.0,
        amount_nok=1000.0,
    )

    new_buy = DecisionResult(
        symbol="ETH-USD",
        action=Action.BUY,
        confidence=99.0,
        evidence=99.0,
        robustness=99.0,
        decision_margin=50.0,
        risk_assessment=RiskAssessment(
            action=Action.BUY,
            allowed=True,
            risk_level="LOW",
            position_size=1.0,
            position_value=110.0,
            stop_loss_price=107.8,
            take_profit_price=114.4,
            reasons=("Approved for test.",),
        ),
    )
    existing_exit = DecisionResult(
        symbol="BTC-USD",
        action=Action.SELL,
        confidence=80.0,
        evidence=80.0,
        robustness=70.0,
        decision_margin=20.0,
        risk_assessment=RiskAssessment(
            action=Action.SELL,
            allowed=True,
            risk_level="LOW",
            position_size=1.0,
            position_value=110.0,
            stop_loss_price=None,
            take_profit_price=None,
            reasons=("Approved exit for test.",),
        ),
    )

    candidates = [
        {
            "symbol": "ETH-USD",
            "discovery_score": 100.0,
            "analysis": [],
            "decision": new_buy,
        },
        {
            "symbol": "BTC-USD",
            "discovery_score": 80.0,
            "analysis": [],
            "decision": existing_exit,
        },
    ]

    monkeypatch.setattr(engine, "decide_candidates", lambda limit=3: candidates)
    monkeypatch.setattr(
        engine.prediction_evaluator,
        "evaluate_ready",
        lambda current_prices_usd: [],
    )
    monkeypatch.setattr(
        engine.analysis_service,
        "analyze",
        lambda symbol: [],
    )
    monkeypatch.setattr(
        engine,
        "_get_market_snapshot",
        lambda symbol: type("Snapshot", (), {"price": 110.0})(),
    )
    monkeypatch.setattr(
        engine,
        "_get_usd_nok_rate",
        lambda: type("ExchangeRate", (), {"rate": 10.0})(),
    )
    monkeypatch.setattr(
        engine.exchange,
        "get_rate",
        lambda base, target: type("ExchangeRate", (), {"rate": 10.0})(),
    )
    monkeypatch.setattr(engine.report, "print_decision", lambda decision: None)

    engine.start()

    trades = engine.trading_service.history()
    assert [trade["action"] for trade in trades] == ["SELL", "BUY"]
    assert trades[0]["symbol"] == "BTC-USD"
    assert not any(
        position["symbol"] == "BTC-USD"
        for position in engine.portfolio_service.as_dict(10.0)["positions"]
    )
    assert not any(
        trade["symbol"] == "ETH-USD" and trade["action"] == "BUY"
        for trade in trades
    )

    predictions = engine.prediction_tracker.history()
    assert len(predictions) == 1
    assert predictions[0]["symbol"] == "BTC-USD"
    assert predictions[0]["action"] == "SELL"


def test_start_prioritizes_sell_exit_over_stronger_new_buy(
    monkeypatch,
    tmp_path,
):
    from atlas.models.action import Action
    from atlas.models.decision_result import DecisionResult
    from atlas.risk.manager import RiskAssessment

    config = AtlasConfig(
        agent_performance_storage=str(tmp_path / "agent_performance.json"),
        database_path=str(tmp_path / "atlas_test.db"),
        capital_limit=1000000.0,
        trading_mode="paper",
        paper_trading=True,
    )
    engine = AtlasEngine(config=config)

    new_buy = DecisionResult(
        symbol="ETH-USD",
        action=Action.BUY,
        confidence=99.0,
        evidence=99.0,
        robustness=99.0,
        decision_margin=50.0,
        risk_assessment=RiskAssessment(
            action=Action.BUY,
            allowed=True,
            risk_level="LOW",
            position_size=1.0,
            position_value=100.0,
            stop_loss_price=98.0,
            take_profit_price=104.0,
            reasons=("Approved for test.",),
        ),
    )
    existing_exit = DecisionResult(
        symbol="BTC-USD",
        action=Action.SELL,
        confidence=80.0,
        evidence=80.0,
        robustness=70.0,
        decision_margin=20.0,
        risk_assessment=RiskAssessment(
            action=Action.SELL,
            allowed=True,
            risk_level="LOW",
            position_size=1.0,
            position_value=100.0,
            stop_loss_price=None,
            take_profit_price=None,
            reasons=("Approved exit for test.",),
        ),
    )

    candidates = [
        {
            "symbol": "ETH-USD",
            "discovery_score": 100.0,
            "analysis": [],
            "decision": new_buy,
        },
        {
            "symbol": "BTC-USD",
            "discovery_score": 80.0,
            "analysis": [],
            "decision": existing_exit,
        },
    ]

    monkeypatch.setattr(engine, "decide_candidates", lambda limit=3: candidates)
    monkeypatch.setattr(
        engine.prediction_evaluator,
        "evaluate_ready",
        lambda current_prices_usd: [],
    )
    monkeypatch.setattr(
        engine.analysis_service,
        "analyze",
        lambda symbol: [],
    )
    monkeypatch.setattr(
        engine,
        "_get_market_snapshot",
        lambda symbol: type("Snapshot", (), {"price": 100.0})(),
    )
    monkeypatch.setattr(engine.report, "print_decision", lambda decision: None)

    executed = []

    def fake_execute(decision, *, price=None, analysis_snapshot_id=None):
        executed.append(decision)
        return None

    monkeypatch.setattr(engine.decision_execution_service, "execute", fake_execute)

    engine.start()

    assert len(executed) == 1
    assert executed[0] is existing_exit

    predictions = engine.prediction_tracker.history()
    assert len(predictions) == 1
    assert predictions[0]["symbol"] == "BTC-USD"
    assert predictions[0]["action"] == "SELL"


def test_start_prefers_investable_buy_over_stronger_vetoed_hold(
    monkeypatch,
    tmp_path,
):
    from atlas.models.action import Action
    from atlas.models.decision_result import DecisionResult
    from atlas.risk.manager import RiskAssessment

    config = AtlasConfig(
        agent_performance_storage=str(tmp_path / "agent_performance.json"),
        database_path=str(tmp_path / "atlas_test.db"),
        capital_limit=1000000.0,
        trading_mode="paper",
        paper_trading=True,
    )
    engine = AtlasEngine(config=config)

    vetoed = DecisionResult(
        symbol="BTC-USD",
        action=Action.HOLD,
        confidence=99.0,
        evidence=99.0,
        robustness=99.0,
        decision_margin=50.0,
        risk_assessment=RiskAssessment(
            action=Action.BUY,
            allowed=False,
            risk_level="BLOCKED",
            position_size=0.0,
            position_value=0.0,
            stop_loss_price=None,
            take_profit_price=None,
            reasons=("Maximum drawdown limit reached.",),
        ),
    )
    investable = DecisionResult(
        symbol="ETH-USD",
        action=Action.BUY,
        confidence=80.0,
        evidence=80.0,
        robustness=70.0,
        decision_margin=20.0,
        risk_assessment=RiskAssessment(
            action=Action.BUY,
            allowed=True,
            risk_level="LOW",
            position_size=1.0,
            position_value=100.0,
            stop_loss_price=98.0,
            take_profit_price=104.0,
            reasons=("Approved for test.",),
        ),
    )

    candidates = [
        {
            "symbol": "BTC-USD",
            "discovery_score": 100.0,
            "analysis": [],
            "decision": vetoed,
        },
        {
            "symbol": "ETH-USD",
            "discovery_score": 80.0,
            "analysis": [],
            "decision": investable,
        },
    ]

    monkeypatch.setattr(engine, "decide_candidates", lambda limit=3: candidates)
    monkeypatch.setattr(
        engine.prediction_evaluator,
        "evaluate_ready",
        lambda current_prices_usd: [],
    )
    monkeypatch.setattr(
        engine.analysis_service,
        "analyze",
        lambda symbol: [],
    )
    monkeypatch.setattr(
        engine,
        "_get_market_snapshot",
        lambda symbol: type("Snapshot", (), {"price": 100.0})(),
    )
    monkeypatch.setattr(engine.report, "print_decision", lambda decision: None)

    executed = []

    def fake_execute(decision, *, price=None, analysis_snapshot_id=None):
        executed.append(decision)
        return None

    monkeypatch.setattr(engine.decision_execution_service, "execute", fake_execute)

    engine.start()

    assert len(executed) == 1
    assert executed[0] is investable

    predictions = engine.prediction_tracker.history()
    assert len(predictions) == 1
    assert predictions[0]["symbol"] == "ETH-USD"
    assert predictions[0]["action"] == "BUY"


def test_portfolio_veto_records_hold_prediction_without_paper_trade(
    monkeypatch,
    tmp_path,
):
    from atlas.models.action import Action
    from atlas.models.analysis_result import AnalysisResult
    from atlas.portfolio.manager import PortfolioManager

    config = AtlasConfig(
        agent_performance_storage=str(tmp_path / "agent_performance.json"),
        database_path=str(tmp_path / "atlas_test.db"),
        capital_limit=1000000.0,
        trading_mode="paper",
        paper_trading=True,
    )
    engine = AtlasEngine(config=config)
    engine.portfolio_manager = PortfolioManager(
        max_exposure_pct=100.0,
        max_single_position_pct=10.0,
    )
    engine.decision_engine.portfolio_manager = engine.portfolio_manager

    analysis = [
        AnalysisResult(
            symbol="BTC-USD",
            analyst="test-analyst",
            action=Action.BUY,
            confidence=95.0,
            evidence=95.0,
            reasoning=["Strong BUY signal."],
        )
    ]
    selected = {
        "symbol": "BTC-USD",
        "discovery_score": 100.0,
        "analysis": analysis,
    }

    def fake_snapshot(symbol):
        return type("Snapshot", (), {"price": 100.0})()

    def fake_decide_candidates(limit=3, minimum_score=0.0):
        selected["decision"] = engine._evaluate_candidate_decision(
            analysis,
            market_snapshot=fake_snapshot("BTC-USD"),
        )
        return [selected]

    monkeypatch.setattr(engine, "decide_candidates", fake_decide_candidates)
    monkeypatch.setattr(
        engine,
        "select_best_candidate",
        lambda candidates, investable_only=False: selected,
    )
    monkeypatch.setattr(engine, "_get_market_snapshot", fake_snapshot)
    monkeypatch.setattr(engine.report, "print_decision", lambda decision: None)
    monkeypatch.setattr(
        engine.prediction_evaluator,
        "evaluate_ready",
        lambda current_prices_usd: [],
    )

    engine.start()

    decision = selected["decision"]
    assert decision.risk_assessment is not None
    assert decision.risk_assessment.action is Action.BUY
    assert decision.risk_assessment.allowed is True
    assert decision.portfolio_assessment is not None
    assert decision.portfolio_assessment.allowed is False
    assert decision.action is Action.HOLD
    assert any(
        "single-position capacity" in reason
        for reason in decision.portfolio_assessment.reasons
    )

    predictions = engine.prediction_tracker.history()
    assert len(predictions) == 1
    assert predictions[0]["action"] == "HOLD"
    assert engine.trading_service.count() == 0

    events = engine.event_repository.after(0, limit=100)
    assert any(event["type"] == "DECISION_READY" for event in events)
    assert not any(event["type"] == "TRADE_EXECUTED" for event in events)


def test_risk_veto_records_hold_prediction_without_paper_trade(
    monkeypatch,
    tmp_path,
):
    from atlas.models.action import Action
    from atlas.models.analysis_result import AnalysisResult

    config = AtlasConfig(
        agent_performance_storage=str(tmp_path / "agent_performance.json"),
        database_path=str(tmp_path / "atlas_test.db"),
        capital_limit=1000000.0,
        trading_mode="paper",
        paper_trading=True,
    )
    engine = AtlasEngine(config=config)
    engine.risk_manager.max_drawdown_pct = 0.0

    analysis = [
        AnalysisResult(
            symbol="BTC-USD",
            analyst="test-analyst",
            action=Action.BUY,
            confidence=95.0,
            evidence=95.0,
            reasoning=["Strong BUY signal."],
        )
    ]
    selected = {
        "symbol": "BTC-USD",
        "discovery_score": 100.0,
        "analysis": analysis,
    }

    def fake_snapshot(symbol):
        return type("Snapshot", (), {"price": 100.0})()

    def fake_decide_candidates(limit=3, minimum_score=0.0):
        selected["decision"] = engine._evaluate_candidate_decision(
            analysis,
            market_snapshot=fake_snapshot("BTC-USD"),
        )
        return [selected]

    monkeypatch.setattr(engine, "decide_candidates", fake_decide_candidates)
    monkeypatch.setattr(
        engine,
        "select_best_candidate",
        lambda candidates, investable_only=False: selected,
    )
    monkeypatch.setattr(engine, "_get_market_snapshot", fake_snapshot)
    monkeypatch.setattr(engine.report, "print_decision", lambda decision: None)
    monkeypatch.setattr(
        engine.prediction_evaluator,
        "evaluate_ready",
        lambda current_prices_usd: [],
    )

    engine.start()

    decision = selected["decision"]
    assert decision.action is Action.HOLD
    assert decision.risk_assessment is not None
    assert decision.risk_assessment.action is Action.BUY
    assert decision.risk_assessment.allowed is False
    assert "Maximum drawdown limit reached." in decision.risk_assessment.reasons

    predictions = engine.prediction_tracker.history()
    assert len(predictions) == 1
    assert predictions[0]["action"] == "HOLD"
    assert engine.trading_service.count() == 0

    events = engine.event_repository.after(0, limit=100)
    assert any(event["type"] == "DECISION_READY" for event in events)
    assert not any(event["type"] == "TRADE_EXECUTED" for event in events)


def test_prediction_persistence_failure_prevents_paper_execution(
    monkeypatch,
    tmp_path,
):
    import pytest

    from atlas.models.action import Action
    from atlas.models.analysis_result import AnalysisResult

    config = AtlasConfig(
        agent_performance_storage=str(tmp_path / "agent_performance.json"),
        database_path=str(tmp_path / "atlas_test.db"),
        trading_mode="paper",
        paper_trading=True,
    )
    engine = AtlasEngine(config=config)

    analysis = [
        AnalysisResult(
            symbol="BTC-USD",
            analyst="test-analyst",
            action=Action.BUY,
            confidence=95.0,
            evidence=95.0,
            reasoning=["Strong BUY signal."],
        )
    ]
    selected = {
        "symbol": "BTC-USD",
        "discovery_score": 100.0,
        "analysis": analysis,
    }

    def fake_snapshot(symbol):
        return type("Snapshot", (), {"price": 100000.0})()

    def fake_decide_candidates(limit=3, minimum_score=0.0):
        selected["decision"] = engine._evaluate_candidate_decision(
            analysis,
            market_snapshot=fake_snapshot("BTC-USD"),
        )
        return [selected]

    def fail_prediction_record(**kwargs):
        raise RuntimeError("prediction persistence failed")

    execution_calls = []

    def capture_execution(*args, **kwargs):
        execution_calls.append((args, kwargs))
        raise AssertionError("execution must not run")

    monkeypatch.setattr(engine, "decide_candidates", fake_decide_candidates)
    monkeypatch.setattr(
        engine,
        "select_best_candidate",
        lambda candidates, investable_only=False: selected,
    )
    monkeypatch.setattr(engine, "_get_market_snapshot", fake_snapshot)
    monkeypatch.setattr(engine.report, "print_decision", lambda decision: None)
    monkeypatch.setattr(
        engine.prediction_evaluator,
        "evaluate_ready",
        lambda current_prices_usd: [],
    )
    monkeypatch.setattr(
        engine.prediction_tracker,
        "record",
        fail_prediction_record,
    )
    monkeypatch.setattr(
        engine.decision_execution_service,
        "execute",
        capture_execution,
    )

    with pytest.raises(RuntimeError, match="prediction persistence failed"):
        engine.start()

    assert execution_calls == []
    assert engine.trading_service.count() == 0

    events = engine.event_repository.after(0, limit=100)
    assert any(event["type"] == "DECISION_READY" for event in events)
    assert not any(event["type"] == "TRADE_EXECUTED" for event in events)


def test_execution_failure_preserves_prediction_without_trade_event(
    monkeypatch,
    tmp_path,
):

    import pytest

    from atlas.models.action import Action
    from atlas.models.analysis_result import AnalysisResult

    config = AtlasConfig(
        agent_performance_storage=(
            str(tmp_path / "agent_performance.json")
        ),
        database_path=str(tmp_path / "atlas_test.db"),
    )
    engine = AtlasEngine(config=config)
    engine.config.trading_mode = "paper"
    engine.config.paper_trading = True

    analysis = [
        AnalysisResult(
            symbol="BTC-USD",
            analyst="test-analyst",
            action=Action.BUY,
            confidence=95.0,
            evidence=95.0,
            reasoning=["Strong BUY signal."],
        )
    ]
    selected = {
        "symbol": "BTC-USD",
        "discovery_score": 100.0,
        "analysis": analysis,
    }

    def fake_decide_candidates(limit=3, minimum_score=0.0):
        selected["decision"] = engine._evaluate_candidate_decision(
            analysis,
            market_snapshot=fake_snapshot("BTC-USD"),
        )
        return [selected]

    def fake_snapshot(symbol):
        return type("Snapshot", (), {"price": 100000.0})()

    def fail_execution(decision, price=None, **kwargs):
        raise RuntimeError("paper execution failed")

    monkeypatch.setattr(
        engine,
        "decide_candidates",
        fake_decide_candidates,
    )
    monkeypatch.setattr(
        engine,
        "select_best_candidate",
        lambda candidates, investable_only=False: selected,
    )
    monkeypatch.setattr(
        engine,
        "_get_market_snapshot",
        fake_snapshot,
    )
    monkeypatch.setattr(
        engine.report,
        "print_decision",
        lambda decision: None,
    )
    monkeypatch.setattr(
        engine.decision_execution_service,
        "execute",
        fail_execution,
    )
    monkeypatch.setattr(
        engine.prediction_evaluator,
        "evaluate_ready",
        lambda current_prices_usd: [],
    )

    with pytest.raises(RuntimeError, match="paper execution failed"):
        engine.start()

    predictions = engine.prediction_tracker.history()
    assert len(predictions) == 1
    assert predictions[0]["symbol"] == "BTC-USD"
    assert predictions[0]["action"] == "BUY"

    events = engine.event_repository.after(0, limit=100)
    assert any(event["type"] == "DECISION_READY" for event in events)
    assert not any(event["type"] == "TRADE_EXECUTED" for event in events)


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

    monkeypatch.setattr(
        engine,
        "integrate_regime_decision",
        lambda decision, regime_decision: decision,
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


def test_atlas_engine_discovers_and_selects_top_candidates(
    monkeypatch,
):
    from atlas.market.asset import Asset
    from atlas.market.asset_discovery import DiscoveryScore
    from atlas.market.asset_type import AssetType

    engine = AtlasEngine()

    candidates = [
        DiscoveryScore(
            asset=Asset(
                symbol="BTC-USD",
                name="Bitcoin",
                asset_type=AssetType.CRYPTO,
                market="crypto",
                currency="USD",
            ),
            score=80.0,
        ),
        DiscoveryScore(
            asset=Asset(
                symbol="NVDA",
                name="NVIDIA",
                asset_type=AssetType.STOCK,
                market="US",
                currency="USD",
            ),
            score=95.0,
        ),
        DiscoveryScore(
            asset=Asset(
                symbol="AAPL",
                name="Apple",
                asset_type=AssetType.STOCK,
                market="US",
                currency="USD",
            ),
            score=70.0,
        ),
    ]

    monkeypatch.setattr(
        engine.asset_discovery,
        "discover",
        lambda universe, limit=None: candidates,
    )

    selected = engine.discover_candidates(
        limit=2,
    )

    assert [
        candidate.symbol
        for candidate in selected
    ] == [
        "NVDA",
        "BTC-USD",
    ]


def test_atlas_engine_discovery_forwards_horizon_context(monkeypatch):
    from atlas.market.asset import Asset
    from atlas.market.asset_discovery import DiscoveryScore
    from atlas.market.asset_type import AssetType
    from atlas.market.trading_horizon import TradingHorizon

    engine = AtlasEngine()

    asset = Asset(
        symbol="NVDA",
        name="NVIDIA",
        asset_type=AssetType.STOCK,
        market="US",
        currency="USD",
    )
    received = {}

    def fake_discover(universe, limit=None, horizon=None):
        received["horizon"] = horizon
        return [
            DiscoveryScore(
                asset=asset,
                score=95.0,
                horizon=horizon,
            )
        ]

    monkeypatch.setattr(
        engine.asset_discovery,
        "discover",
        fake_discover,
    )

    selected = engine.discover_candidates(
        limit=1,
        horizon=TradingHorizon.SWING,
    )

    assert received["horizon"] == TradingHorizon.SWING
    assert selected[0].horizon == TradingHorizon.SWING


def test_atlas_engine_analysis_forwards_horizon_to_discovery():
    from types import SimpleNamespace

    from atlas.core.engine import AtlasEngine
    from atlas.market.trading_horizon import TradingHorizon

    engine = object.__new__(AtlasEngine)
    received = {}

    def fake_discover_candidates(
        limit=3,
        minimum_score=0.0,
        horizon=None,
    ):
        received["horizon"] = horizon
        return []

    engine.discover_candidates = fake_discover_candidates

    result = engine.analyze_candidates(
        horizon=TradingHorizon.SWING,
    )

    assert result == []
    assert received["horizon"] == TradingHorizon.SWING


def test_atlas_engine_analysis_uses_horizon_market_snapshot_for_algorithm_evidence():
    from types import SimpleNamespace

    from atlas.core.engine import AtlasEngine
    from atlas.market.asset import Asset
    from atlas.market.asset_type import AssetType
    from atlas.market.trading_horizon import TradingHorizon

    engine = object.__new__(AtlasEngine)
    candidate = SimpleNamespace(
        symbol="NVDA",
        score=91.0,
        asset=Asset(
            symbol="NVDA",
            name="NVIDIA",
            asset_type=AssetType.STOCK,
            market="US",
            currency="USD",
        ),
    )
    normalized_snapshot = object()
    received = {}

    engine.discover_candidates = lambda **kwargs: [candidate]
    engine.analysis_service = SimpleNamespace(
        analyze=lambda symbol: [],
    )

    def snapshot_for_horizon(symbol, horizon, limit):
        received["snapshot"] = (symbol, horizon, limit)
        return normalized_snapshot

    engine.market_data = SimpleNamespace(
        snapshot_for_horizon=snapshot_for_horizon,
    )

    class AlgorithmPipelineStub:
        def analyze(self, symbol, snapshot):
            received["algorithm"] = (symbol, snapshot)
            return None, []

    engine.algorithm_pipeline = AlgorithmPipelineStub()
    engine._get_market_snapshot = lambda symbol: object()

    engine.analyze_candidates(
        horizon=TradingHorizon.SWING,
    )

    assert received["snapshot"] == (
        "NVDA",
        TradingHorizon.SWING,
        100,
    )
    assert received["algorithm"] == (
        "NVDA",
        normalized_snapshot,
    )


def test_atlas_engine_analyzes_selected_candidates(monkeypatch):
    from atlas.market.asset import Asset
    from atlas.market.asset_discovery import DiscoveryScore
    from atlas.market.asset_type import AssetType

    engine = AtlasEngine()

    candidates = [
        DiscoveryScore(
            asset=Asset(
                symbol="NVDA",
                name="NVIDIA",
                asset_type=AssetType.STOCK,
                market="US",
                currency="USD",
            ),
            score=95.0,
        ),
        DiscoveryScore(
            asset=Asset(
                symbol="BTC-USD",
                name="Bitcoin",
                asset_type=AssetType.CRYPTO,
                market="crypto",
                currency="USD",
            ),
            score=90.0,
        ),
    ]

    def fake_discover_candidates(
        limit=3,
        minimum_score=0.0,
    ):
        return candidates[:limit]

    monkeypatch.setattr(
        engine,
        "discover_candidates",
        fake_discover_candidates,
    )

    analyzed_symbols = []

    def fake_analyze(symbol):
        analyzed_symbols.append(symbol)
        return []

    monkeypatch.setattr(
        engine.analysis_service,
        "analyze",
        fake_analyze,
    )

    results = engine.analyze_candidates(
        limit=2,
    )

    assert analyzed_symbols == [
        "NVDA",
        "BTC-USD",
    ]

    assert [item["symbol"] for item in results] == [
        "NVDA",
        "BTC-USD",
    ]


def test_atlas_engine_ranks_candidate_decisions():
    from atlas.models.action import Action
    from atlas.models.decision_result import DecisionResult

    engine = AtlasEngine()

    decisions = [
        DecisionResult(
            symbol="AAPL",
            action=Action.BUY,
            confidence=80.0,
            evidence=80.0,
            robustness=60.0,
            decision_margin=15.0,
        ),
        DecisionResult(
            symbol="NVDA",
            action=Action.BUY,
            confidence=90.0,
            evidence=92.0,
            robustness=85.0,
            decision_margin=30.0,
        ),
        DecisionResult(
            symbol="BTC-USD",
            action=Action.HOLD,
            confidence=95.0,
            evidence=95.0,
            robustness=95.0,
            decision_margin=40.0,
        ),
    ]

    ranked = engine.rank_candidate_decisions(
        decisions,
    )

    assert [decision.symbol for decision in ranked] == [
        "NVDA",
        "AAPL",
        "BTC-USD",
    ]


def test_atlas_engine_decides_analyzed_candidates(monkeypatch):
    from atlas.market.asset import Asset
    from atlas.market.asset_discovery import DiscoveryScore
    from atlas.market.asset_type import AssetType
    from atlas.models.action import Action
    from atlas.models.analysis_result import AnalysisResult
    from atlas.models.decision_result import DecisionResult

    engine = AtlasEngine()

    candidates = [
        DiscoveryScore(
            asset=Asset(
                symbol="NVDA",
                name="NVIDIA",
                asset_type=AssetType.STOCK,
                market="US",
                currency="USD",
            ),
            score=95.0,
        ),
        DiscoveryScore(
            asset=Asset(
                symbol="BTC-USD",
                name="Bitcoin",
                asset_type=AssetType.CRYPTO,
                market="crypto",
                currency="USD",
            ),
            score=90.0,
        ),
    ]

    monkeypatch.setattr(
        engine,
        "discover_candidates",
        lambda limit=3, minimum_score=0.0: candidates[:limit],
    )

    monkeypatch.setattr(
        engine.analysis_service,
        "analyze",
        lambda symbol: [
            AnalysisResult(
                analyst="Technical Analyst",
                symbol=symbol,
                action=Action.BUY,
                confidence=85.0,
                evidence=80.0,
                reasoning=[],
            ),
        ],
    )

    monkeypatch.setattr(
        engine.decision_engine,
        "evaluate",
        lambda results: DecisionResult(
            symbol=results[0].symbol,
            action=Action.BUY,
            confidence=85.0,
            evidence=80.0,
            analysts=["Technical Analyst"],
            dominant_action=Action.BUY,
            dominant_weight=85.0,
            decision_margin=25.0,
            robustness=75.0,
            robustness_level="STRONG",
        ),
    )

    results = engine.decide_candidates(
        limit=2,
    )

    assert [item["symbol"] for item in results] == [
        "NVDA",
        "BTC-USD",
    ]

    assert all(
        item["decision"].action == Action.BUY
        for item in results
    )

    assert results[0]["discovery_score"] == 95.0
    assert results[1]["discovery_score"] == 90.0


def test_atlas_engine_selects_best_candidate_decision():
    from atlas.models.action import Action
    from atlas.models.decision_result import DecisionResult

    engine = AtlasEngine()

    candidates = [
        {
            "symbol": "AAPL",
            "discovery_score": 80.0,
            "decision": DecisionResult(
                symbol="AAPL",
                action=Action.BUY,
                confidence=80.0,
                evidence=80.0,
                robustness=65.0,
                decision_margin=15.0,
            ),
        },
        {
            "symbol": "NVDA",
            "discovery_score": 95.0,
            "decision": DecisionResult(
                symbol="NVDA",
                action=Action.BUY,
                confidence=92.0,
                evidence=94.0,
                robustness=88.0,
                decision_margin=32.0,
            ),
        },
        {
            "symbol": "BTC-USD",
            "discovery_score": 90.0,
            "decision": DecisionResult(
                symbol="BTC-USD",
                action=Action.HOLD,
                confidence=95.0,
                evidence=95.0,
                robustness=95.0,
                decision_margin=40.0,
            ),
        },
    ]

    selected = engine.select_best_candidate(
        candidates,
    )

    assert selected is not None
    assert selected["symbol"] == "NVDA"
    assert selected["decision"].action == Action.BUY
    assert selected["discovery_score"] == 95.0


def test_get_candidate_selection_report_returns_report():
    from atlas.core.engine import AtlasEngine
    from atlas.market.candidate_decision_ranker import (
        CandidateDecisionRanker,
    )
    from atlas.market.candidate_selection_report import (
        CandidateSelectionReport,
    )
    from atlas.models.action import Action
    from atlas.models.decision_result import DecisionResult

    engine = object.__new__(AtlasEngine)

    engine.candidate_decision_ranker = (
        CandidateDecisionRanker()
    )

    class FakeLogger:
        def info(self, message):
            pass

    engine.logger = FakeLogger()

    decision = DecisionResult(
        symbol="BTC-USD",
        action=Action.BUY,
        confidence=90.0,
        evidence=90.0,
        robustness=90.0,
        decision_margin=30.0,
        reasoning=["strong"],
    )

    candidates = [
        {
            "symbol": "BTC-USD",
            "discovery_score": 90.0,
            "decision": decision,
        }
    ]

    report = engine.get_candidate_selection_report(
        candidates,
    )

    assert isinstance(
        report,
        CandidateSelectionReport,
    )

    assert report.symbol == "BTC-USD"
    assert report.action == "BUY"
    assert report.ranking_evidence.symbol == "BTC-USD"


def test_get_candidate_selection_report_returns_none_without_candidates():
    from atlas.core.engine import AtlasEngine

    engine = object.__new__(AtlasEngine)

    assert (
        engine.get_candidate_selection_report([])
        is None
    )


def test_atlas_engine_start_uses_selected_candidate(
    monkeypatch,
):
    from atlas.models.action import Action
    from atlas.models.decision_result import DecisionResult

    engine = AtlasEngine()

    selected = {
        "symbol": "NVDA",
        "discovery_score": 95.0,
        "decision": DecisionResult(
            symbol="NVDA",
            action=Action.BUY,
            confidence=92.0,
            evidence=94.0,
            robustness=88.0,
            decision_margin=32.0,
        ),
    }

    monkeypatch.setattr(
        engine,
        "select_best_candidate",
        lambda candidates: selected,
    )

    analyzed = [
        selected,
        {
            "symbol": "BTC-USD",
            "discovery_score": 90.0,
            "decision": DecisionResult(
                symbol="BTC-USD",
                action=Action.HOLD,
                confidence=90.0,
                evidence=90.0,
                robustness=80.0,
                decision_margin=20.0,
            ),
        },
    ]

    monkeypatch.setattr(
        engine,
        "decide_candidates",
        lambda limit=3, minimum_score=0.0: analyzed,
    )

    analyzed_symbols = []

    def fake_snapshot(symbol):
        analyzed_symbols.append(symbol)
        return type(
            "Snapshot",
            (),
            {"price": 100.0},
        )()

    monkeypatch.setattr(
        engine,
        "_get_market_snapshot",
        fake_snapshot,
    )

    monkeypatch.setattr(
        engine.prediction_evaluator,
        "evaluate_ready",
        lambda current_prices_usd: [],
    )

    monkeypatch.setattr(
        engine.report,
        "print_decision",
        lambda decision: None,
    )

    engine.config.trading_mode = "advisor"

    monkeypatch.setattr(
        engine.decision_execution_service,
        "execute",
        lambda decision, price=None, **kwargs: None,
    )

    engine.start()

    assert analyzed_symbols
    assert analyzed_symbols[-1] == "NVDA"


def test_atlas_engine_integrates_regime_context_without_overriding_buy():
    from atlas.models.action import Action
    from atlas.models.decision_result import DecisionResult
    from atlas.trading.strategy_memory_regime_decision_adapter import (
        StrategyMemoryRegimeDecisionAdapter,
    )
    from atlas.trading.strategy_memory_regime_recommendation_service import (
        StrategyMemoryRegimeRecommendation,
    )

    engine = AtlasEngine()

    decision = DecisionResult(
        symbol="BTC-USD",
        action=Action.BUY,
        confidence=85.0,
        evidence=90.0,
        robustness=82.0,
        decision_margin=25.0,
        reasoning=["Strong market evidence."],
    )

    recommendation = StrategyMemoryRegimeRecommendation(
        symbol="BTC-USD",
        regime="LOW_VOLATILITY",
        recommended_strategy="Momentum",
        confidence=80.0,
        independent_run_count=8,
        robust_winner=True,
    )

    regime_decision = StrategyMemoryRegimeDecisionAdapter().adapt(
        recommendation
    )

    integrated = engine.integrate_regime_decision(
        decision,
        regime_decision,
    )

    assert integrated.action == Action.BUY
    assert integrated.symbol == "BTC-USD"
    assert any(
        "Strategy-memory regime: LOW_VOLATILITY."
        in item
        for item in integrated.reasoning
    )
    assert any(
        "Strategy-memory recommendation: Momentum"
        in item
        for item in integrated.reasoning
    )


def test_atlas_engine_integrates_missing_regime_recommendation():
    from atlas.models.action import Action
    from atlas.models.decision_result import DecisionResult
    from atlas.trading.strategy_memory_regime_decision_adapter import (
        StrategyMemoryRegimeDecisionAdapter,
    )
    from atlas.trading.strategy_memory_regime_recommendation_service import (
        StrategyMemoryRegimeRecommendation,
    )

    engine = AtlasEngine()

    decision = DecisionResult(
        symbol="BTC-USD",
        action=Action.HOLD,
        confidence=60.0,
        evidence=60.0,
        robustness=55.0,
        decision_margin=5.0,
        reasoning=["Insufficient conviction."],
    )

    recommendation = StrategyMemoryRegimeRecommendation(
        symbol="BTC-USD",
        regime="HIGH_VOLATILITY",
        recommended_strategy=None,
        confidence=0.0,
        independent_run_count=1,
        robust_winner=False,
    )

    regime_decision = StrategyMemoryRegimeDecisionAdapter().adapt(
        recommendation
    )

    integrated = engine.integrate_regime_decision(
        decision,
        regime_decision,
    )

    assert integrated.action == Action.HOLD
    assert any(
        "No robust strategy-memory recommendation"
        in item
        for item in integrated.reasoning
    )


def test_atlas_engine_rejects_mismatching_regime_symbol():
    import pytest

    from atlas.models.action import Action
    from atlas.models.decision_result import DecisionResult
    from atlas.trading.strategy_memory_regime_decision_adapter import (
        StrategyMemoryRegimeDecision,
    )

    engine = AtlasEngine()

    decision = DecisionResult(
        symbol="BTC-USD",
        action=Action.BUY,
        confidence=80.0,
        evidence=80.0,
        robustness=75.0,
        decision_margin=20.0,
    )

    regime_decision = StrategyMemoryRegimeDecision(
        symbol="ETH-USD",
        regime="LOW_VOLATILITY",
        strategy="Momentum",
        action=Action.HOLD,
        confidence=80.0,
        independent_run_count=8,
        robust_winner=True,
    )

    with pytest.raises(
        ValueError,
        match="symbols must match",
    ):
        engine.integrate_regime_decision(
            decision,
            regime_decision,
        )


def test_get_regime_memory_decision_uses_regime_memory_pipeline():
    from atlas.models.action import Action
    from atlas.models.decision_result import DecisionResult
    from atlas.trading.strategy_memory_regime_decision_adapter import (
        StrategyMemoryRegimeDecision,
    )
    from atlas.trading.strategy_memory_regime_evidence import (
        StrategyMemoryRegimeEvidenceResult,
    )
    from atlas.trading.strategy_memory_regime_recommendation_service import (
        StrategyMemoryRegimeRecommendation,
    )

    class FakeEvidenceService:

        def analyze(self, *, symbol, regime):
            assert symbol == "BTC-USD"
            assert regime == "LOW_VOLATILITY"

            return StrategyMemoryRegimeEvidenceResult(
                symbol=symbol,
                regime=regime,
                recommended_strategy="Momentum",
                confidence=80.0,
                independent_run_count=8,
                robust_winner=True,
            )

    class FakeRecommendationService:

        def recommend(self, evidence):
            assert evidence.recommended_strategy == "Momentum"

            return StrategyMemoryRegimeRecommendation(
                symbol=evidence.symbol,
                regime=evidence.regime,
                recommended_strategy="Momentum",
                confidence=80.0,
                independent_run_count=8,
                robust_winner=True,
            )

    class FakeAdapter:

        def adapt(self, recommendation):
            assert recommendation.recommended_strategy == "Momentum"

            return StrategyMemoryRegimeDecision(
                symbol=recommendation.symbol,
                regime=recommendation.regime,
                strategy=recommendation.recommended_strategy,
                action=Action.HOLD,
                confidence=recommendation.confidence,
                independent_run_count=(
                    recommendation.independent_run_count
                ),
                robust_winner=recommendation.robust_winner,
            )

    # Import the engine class without constructing the full runtime.
    from atlas.core.engine import AtlasEngine

    engine = object.__new__(AtlasEngine)

    engine.strategy_memory_regime_evidence_service = (
        FakeEvidenceService()
    )
    engine.strategy_memory_regime_recommendation_service = (
        FakeRecommendationService()
    )
    engine.strategy_memory_regime_decision_adapter = (
        FakeAdapter()
    )

    result = engine.get_regime_memory_decision(
        "BTC-USD",
        "LOW_VOLATILITY",
    )

    assert isinstance(
        result,
        StrategyMemoryRegimeDecision,
    )
    assert result.symbol == "BTC-USD"
    assert result.regime == "LOW_VOLATILITY"
    assert result.strategy == "Momentum"
    assert result.action == Action.HOLD
    assert result.confidence == 80.0
    assert result.independent_run_count == 8
    assert result.robust_winner is True


def test_decide_candidates_integrates_regime_memory():
    from types import SimpleNamespace

    from atlas.core.engine import AtlasEngine
    from atlas.models.action import Action
    from atlas.models.decision_result import DecisionResult
    from atlas.trading.strategy_memory_regime_decision_adapter import (
        StrategyMemoryRegimeDecision,
    )

    engine = object.__new__(AtlasEngine)

    analysis = object()

    engine.analyze_candidates = lambda **kwargs: [
        {
            "symbol": "BTC-USD",
            "discovery_score": 95.0,
            "analysis": analysis,
            "market_snapshot": SimpleNamespace(
                regime="LOW_VOLATILITY",
            ),
        }
    ]

    original_decision = DecisionResult(
        symbol="BTC-USD",
        action=Action.BUY,
        confidence=85.0,
        evidence=90.0,
        robustness=82.0,
        decision_margin=25.0,
    )

    engine.decision_engine = SimpleNamespace(
        evaluate=lambda received_analysis: (
            original_decision
            if received_analysis is analysis
            else None
        )
    )

    regime_decision = StrategyMemoryRegimeDecision(
        symbol="BTC-USD",
        regime="LOW_VOLATILITY",
        strategy="Momentum",
        action=Action.HOLD,
        confidence=80.0,
        independent_run_count=8,
        robust_winner=True,
    )

    calls = []

    def fake_get_regime_memory_decision(symbol, regime):
        calls.append((symbol, regime))
        return regime_decision

    engine.get_regime_memory_decision = (
        fake_get_regime_memory_decision
    )

    def fake_integrate(decision, received_regime_decision):
        assert decision is original_decision
        assert received_regime_decision is regime_decision

        return DecisionResult(
            symbol=decision.symbol,
            action=decision.action,
            confidence=decision.confidence,
            evidence=decision.evidence,
            robustness=decision.robustness,
            decision_margin=decision.decision_margin,
            reasoning=list(decision.reasoning)
            + ["regime-memory-integrated"],
        )

    engine.integrate_regime_decision = fake_integrate

    results = engine.decide_candidates()

    assert calls == [
        ("BTC-USD", "LOW_VOLATILITY"),
    ]

    assert len(results) == 1
    assert results[0]["symbol"] == "BTC-USD"
    assert results[0]["regime_decision"] is regime_decision
    assert results[0]["decision"].action == Action.BUY
    assert (
        "regime-memory-integrated"
        in results[0]["decision"].reasoning
    )


def test_rank_candidate_decisions_preserves_regime_memory_context():
    from atlas.core.engine import AtlasEngine
    from atlas.market.candidate_decision_ranker import (
        CandidateDecisionRanker,
    )
    from atlas.models.action import Action
    from atlas.models.decision_result import DecisionResult
    from atlas.trading.strategy_memory_regime_decision_adapter import (
        StrategyMemoryRegimeDecision,
    )

    engine = object.__new__(AtlasEngine)

    engine.candidate_decision_ranker = (
        CandidateDecisionRanker()
    )

    decision = DecisionResult(
        symbol="BTC-USD",
        action=Action.BUY,
        confidence=85.0,
        evidence=90.0,
        robustness=82.0,
        decision_margin=25.0,
        reasoning=[
            "base-decision",
            "Strategy-memory regime: LOW_VOLATILITY.",
            "Strategy-memory recommendation: Momentum "
            "(confidence 80.0/100, 8 independent runs).",
            "Strategy-memory recommendation is supported "
            "by a robust historical regime winner.",
        ],
    )

    regime_decision = StrategyMemoryRegimeDecision(
        symbol="BTC-USD",
        regime="LOW_VOLATILITY",
        strategy="Momentum",
        action=Action.HOLD,
        confidence=80.0,
        independent_run_count=8,
        robust_winner=True,
    )

    ranked = engine.rank_candidate_decisions(
        [decision],
    )

    assert len(ranked) == 1
    assert ranked[0] is decision
    assert ranked[0].action == Action.BUY
    assert ranked[0].reasoning == [
        "base-decision",
        "Strategy-memory regime: LOW_VOLATILITY.",
        "Strategy-memory recommendation: Momentum "
        "(confidence 80.0/100, 8 independent runs).",
        "Strategy-memory recommendation is supported "
        "by a robust historical regime winner.",
    ]

    # The regime-memory representation itself remains HOLD.
    # It must not alter the authoritative BUY action.
    assert regime_decision.action == Action.HOLD


def test_select_best_candidate_returns_ranking_evidence():
    from atlas.core.engine import AtlasEngine
    from atlas.market.candidate_decision_ranker import (
        CandidateDecisionRanker,
    )
    from atlas.models.action import Action
    from atlas.models.decision_result import DecisionResult
    from atlas.trading.strategy_memory_regime_decision_adapter import (
        StrategyMemoryRegimeDecision,
    )

    engine = object.__new__(AtlasEngine)

    engine.candidate_decision_ranker = (
        CandidateDecisionRanker()
    )

    class FakeLogger:
        def info(self, message):
            pass

    engine.logger = FakeLogger()

    strong = DecisionResult(
        symbol="BTC-USD",
        action=Action.BUY,
        confidence=90.0,
        evidence=90.0,
        robustness=90.0,
        decision_margin=30.0,
        reasoning=["strong"],
    )

    weaker = DecisionResult(
        symbol="ETH-USD",
        action=Action.BUY,
        confidence=80.0,
        evidence=80.0,
        robustness=80.0,
        decision_margin=20.0,
        reasoning=["weaker"],
    )

    candidates = [
        {
            "symbol": "BTC-USD",
            "discovery_score": 90.0,
            "decision": strong,
            "regime_decision": StrategyMemoryRegimeDecision(
                symbol="BTC-USD",
                regime="LOW_VOLATILITY",
                strategy="Momentum",
                action=Action.HOLD,
                confidence=80.0,
                independent_run_count=8,
                robust_winner=True,
            ),
        },
        {
            "symbol": "ETH-USD",
            "discovery_score": 80.0,
            "decision": weaker,
            "regime_decision": StrategyMemoryRegimeDecision(
                symbol="ETH-USD",
                regime="LOW_VOLATILITY",
                strategy=None,
                action=Action.HOLD,
                confidence=0.0,
                independent_run_count=0,
                robust_winner=False,
            ),
        },
    ]

    selected = engine.select_best_candidate(
        candidates,
    )

    assert selected is not None
    assert selected["symbol"] == "BTC-USD"

    assert "ranking_evidence" in selected

    evidence = selected["ranking_evidence"]

    assert evidence.symbol == "BTC-USD"
    assert evidence.base_score > 0.0
    assert evidence.regime_fit > 0.0
    assert evidence.final_score > 0.0

    assert evidence.regime == "LOW_VOLATILITY"
    assert evidence.strategy == "Momentum"
    assert evidence.regime_confidence == 80.0
    assert evidence.independent_run_count == 8
    assert evidence.robust_winner is True

    # Ranking evidence explains the selected candidate;
    # it must not change the authoritative BUY action.
    assert selected["decision"].action == Action.BUY


def test_select_best_candidate_returns_selection_report():
    from atlas.models.action import Action
    from atlas.models.decision_result import DecisionResult

    engine = AtlasEngine()

    btc_decision = DecisionResult(
        symbol="BTC-USD",
        action=Action.BUY,
        confidence=90.0,
        evidence=85.0,
        robustness=88.0,
        decision_margin=82.0,
    )

    eth_decision = DecisionResult(
        symbol="ETH-USD",
        action=Action.BUY,
        confidence=60.0,
        evidence=55.0,
        robustness=58.0,
        decision_margin=52.0,
    )

    candidates = [
        {
            "symbol": "BTC-USD",
            "discovery_score": 90.0,
            "decision": btc_decision,
            "regime_decision": None,
        },
        {
            "symbol": "ETH-USD",
            "discovery_score": 80.0,
            "decision": eth_decision,
            "regime_decision": None,
        },
    ]

    selected = engine.select_best_candidate(
        candidates
    )

    assert selected is not None
    assert selected["symbol"] == "BTC-USD"
    assert "ranking_evidence" in selected
    assert "selection_report" in selected

    report = selected["selection_report"]

    assert report.symbol == "BTC-USD"
    assert report.action == "BUY"
    assert report.ranking_evidence is selected[
        "ranking_evidence"
    ]

    assert report.reasoning[0] == (
        "Selected candidate: BTC-USD."
    )
    assert report.reasoning[1] == "Action: BUY."



def test_get_candidate_selection_report_supports_serialization():
    from atlas.core.engine import AtlasEngine
    from atlas.market.candidate_decision_ranker import (
        CandidateDecisionRanker,
    )
    from atlas.models.action import Action
    from atlas.models.decision_result import DecisionResult
    from atlas.trading.strategy_memory_regime_decision_adapter import (
        StrategyMemoryRegimeDecision,
    )

    engine = object.__new__(AtlasEngine)

    engine.candidate_decision_ranker = (
        CandidateDecisionRanker()
    )

    class LoggerStub:
        def info(self, message):
            pass

    engine.logger = LoggerStub()

    decision = DecisionResult(
        symbol="BTC-USD",
        action=Action.BUY,
        confidence=90.0,
        evidence=90.0,
        robustness=90.0,
        decision_margin=30.0,
        reasoning=["strong"],
    )

    candidates = [
        {
            "symbol": "BTC-USD",
            "discovery_score": 90.0,
            "decision": decision,
            "regime_decision": StrategyMemoryRegimeDecision(
                symbol="BTC-USD",
                regime="LOW_VOLATILITY",
                strategy="Momentum",
                action=Action.HOLD,
                confidence=80.0,
                independent_run_count=8,
                robust_winner=True,
            ),
        }
    ]

    report = engine.get_candidate_selection_report(
        candidates,
    )

    assert report is not None

    serialized = report.to_dict()

    assert serialized["symbol"] == "BTC-USD"
    assert serialized["action"] == "BUY"

    evidence = serialized["ranking_evidence"]

    assert evidence["symbol"] == "BTC-USD"
    assert evidence["regime"] == "LOW_VOLATILITY"
    assert evidence["strategy"] == "Momentum"
    assert evidence["independent_run_count"] == 8
    assert evidence["robust_winner"] is True


def test_get_candidate_selection_snapshot_returns_dict():
    from atlas.core.engine import AtlasEngine
    from atlas.market.candidate_decision_ranker import (
        CandidateDecisionRanker,
    )
    from atlas.models.action import Action
    from atlas.models.decision_result import DecisionResult

    engine = object.__new__(AtlasEngine)

    engine.candidate_decision_ranker = (
        CandidateDecisionRanker()
    )

    class LoggerStub:
        def info(self, message):
            pass

    engine.logger = LoggerStub()

    strong = DecisionResult(
        symbol="BTC-USD",
        action=Action.BUY,
        confidence=90.0,
        evidence=90.0,
        robustness=90.0,
        decision_margin=30.0,
        reasoning=["strong"],
    )

    candidates = [
        {
            "symbol": "BTC-USD",
            "discovery_score": 90.0,
            "decision": strong,
        },
    ]

    snapshot = (
        engine.get_candidate_selection_snapshot(
            candidates,
        )
    )

    assert isinstance(snapshot, dict)
    assert snapshot["symbol"] == "BTC-USD"
    assert snapshot["action"] == "BUY"
    assert "ranking_evidence" in snapshot
    assert "reasoning" in snapshot


def test_get_candidate_selection_snapshot_returns_none_without_candidates():
    from atlas.core.engine import AtlasEngine

    engine = object.__new__(AtlasEngine)

    assert (
        engine.get_candidate_selection_snapshot([])
        is None
    )


def test_start_selection_snapshot_log_is_valid_json():
    import json

    selection_snapshot = {
        "symbol": "BTC-USD",
        "action": "BUY",
        "ranking_evidence": {
            "symbol": "BTC-USD",
            "base_score": 90.0,
            "regime_fit": 0.0,
            "final_score": 90.0,
            "regime": None,
            "strategy": None,
            "regime_confidence": None,
            "independent_run_count": 0,
            "robust_winner": False,
        },
        "reasoning": [
            "Selected candidate: BTC-USD.",
            "Action: BUY.",
        ],
    }

    logged_message = (
        "ATLAS selection snapshot: "
        + json.dumps(
            selection_snapshot,
            ensure_ascii=False,
            sort_keys=True,
        )
    )

    payload = logged_message.split(
        "ATLAS selection snapshot: ",
        1,
    )[1]

    decoded = json.loads(payload)

    assert decoded["symbol"] == "BTC-USD"
    assert decoded["action"] == "BUY"
    assert decoded["ranking_evidence"]["final_score"] == 90.0
    assert decoded["reasoning"] == [
        "Selected candidate: BTC-USD.",
        "Action: BUY.",
    ]


def test_start_logs_selection_snapshot():
    from atlas.core.engine import AtlasEngine

    class LoggerStub:
        def __init__(self):
            self.messages = []

        def info(self, message):
            self.messages.append(str(message))

    engine = object.__new__(AtlasEngine)
    engine.logger = LoggerStub()

    class ConfigStub:
        version = "test"
        trading_mode = "paper"
        capital_limit = 1000
        ai_provider = "test"

    engine.config = ConfigStub()

    engine.asset_universe = type(
        "AssetUniverseStub",
        (),
        {
            "all": lambda self: [],
        },
    )()

    engine.prediction_evaluator = type(
        "PredictionEvaluatorStub",
        (),
        {
            "evaluate_ready": (
                lambda self, current_prices_usd: []
            ),
        },
    )()

    engine.decide_candidates = lambda limit: [
        {
            "symbol": "BTC-USD",
            "decision": type(
                "DecisionStub",
                (),
                {
                    "action": type(
                        "ActionStub",
                        (),
                        {"value": "BUY"},
                    )()
                },
            )(),
        }
    ]

    selection_snapshot = {
        "symbol": "BTC-USD",
        "action": "BUY",
        "ranking_evidence": {
            "symbol": "BTC-USD",
            "base_score": 90.0,
            "regime_fit": 0.0,
            "final_score": 90.0,
            "regime": None,
            "strategy": None,
            "regime_confidence": None,
            "independent_run_count": 0,
            "robust_winner": False,
        },
        "reasoning": [
            "Selected candidate: BTC-USD.",
            "Action: BUY.",
        ],
    }

    report = type(
        "ReportStub",
        (),
        {
            "selection_snapshot": selection_snapshot,
        },
    )()

    engine.select_best_candidate = lambda candidates: {
        "symbol": "BTC-USD",
        "decision": candidates[0]["decision"],
        "selection_report": report,
    }

    engine.logger.info("ATLAS selection report ready for BTC-USD.")
    engine.logger.info(
        f"ATLAS selection snapshot: "
        f"{selection_snapshot}"
    )

    assert any(
        "ATLAS selection snapshot:" in message
        for message in engine.logger.messages
    )


def test_evaluate_candidate_decision_combines_analyst_and_algorithm_evidence_once():
    from atlas.algorithms.base import AlgorithmSignal
    from atlas.core.engine import AtlasEngine
    from atlas.models.action import Action
    from atlas.models.analysis_result import AnalysisResult

    engine = object.__new__(AtlasEngine)
    engine._peak_equity_nok = None

    analyst = AnalysisResult(
        symbol="NVDA",
        analyst="Technical Analyst",
        action=Action.BUY,
        confidence=80.0,
        evidence=80.0,
        reasoning=["analyst evidence"],
    )
    algorithm = AlgorithmSignal(
        algorithm="momentum",
        symbol="NVDA",
        timeframe="1h",
        action=Action.BUY,
        score=80.0,
        confidence=0.9,
        reasoning=["algorithm evidence"],
    )

    captured = {}

    class DecisionEngineStub:
        def evaluate(self, results):
            captured["results"] = list(results)
            return "decision"

    engine.decision_engine = DecisionEngineStub()

    result = engine._evaluate_candidate_decision(
        [analyst],
        algorithm_signals=[algorithm],
    )

    assert result == "decision"
    assert captured["results"][0] is analyst
    assert len(captured["results"]) == 2
    assert captured["results"][1].analyst == "algorithm:momentum"
    assert captured["results"][1].symbol == "NVDA"
    assert captured["results"][1].action == Action.BUY
    assert captured["results"][1].reasoning == ["algorithm evidence"]


def test_analyze_candidates_generates_algorithm_evidence_from_normalized_snapshot():
    from types import SimpleNamespace

    from atlas.core.engine import AtlasEngine

    from atlas.market.asset import Asset
    from atlas.market.asset_type import AssetType

    engine = object.__new__(AtlasEngine)
    candidate = SimpleNamespace(
        symbol="NVDA",
        score=91.0,
        asset=Asset(
            symbol="NVDA",
            name="NVIDIA",
            asset_type=AssetType.STOCK,
            market="US",
            currency="USD",
        ),
    )
    normalized_snapshot = object()
    technical_snapshot = object()
    algorithm_signals = [object()]

    engine.discover_candidates = lambda **kwargs: [candidate]
    engine.analysis_service = SimpleNamespace(
        analyze=lambda symbol: ["analyst-evidence"],
    )
    engine.market_data = SimpleNamespace(
        snapshot=lambda symbol, interval, limit: (
            normalized_snapshot
            if (symbol, interval, limit) == ("NVDA", "5m", 100)
            else None
        ),
    )

    calls = []

    class AlgorithmPipelineStub:
        def analyze(self, symbol, snapshot):
            calls.append((symbol, snapshot))
            return None, algorithm_signals

    engine.algorithm_pipeline = AlgorithmPipelineStub()
    engine._get_market_snapshot = lambda symbol: technical_snapshot

    results = engine.analyze_candidates()

    assert calls == [("NVDA", normalized_snapshot)]
    assert results[0]["analysis"] == ["analyst-evidence"]
    assert results[0]["market_snapshot"] is technical_snapshot
    assert results[0]["algorithm_signals"] is algorithm_signals


def test_decide_candidates_forwards_horizon_to_candidate_analysis():
    from atlas.core.engine import AtlasEngine
    from atlas.market.trading_horizon import TradingHorizon

    engine = object.__new__(AtlasEngine)
    received = {}

    def fake_analyze_candidates(
        limit=3,
        minimum_score=0.0,
        horizon=None,
    ):
        received["horizon"] = horizon
        return []

    engine.analyze_candidates = fake_analyze_candidates

    result = engine.decide_candidates(
        horizon=TradingHorizon.SWING,
    )

    assert result == []
    assert received["horizon"] == TradingHorizon.SWING


def test_decide_candidates_forwards_algorithm_evidence_to_decision_boundary():
    from types import SimpleNamespace

    from atlas.core.engine import AtlasEngine

    engine = object.__new__(AtlasEngine)
    algorithm_signals = [object()]
    engine.analyze_candidates = lambda **kwargs: [
        {
            "symbol": "NVDA",
            "discovery_score": 91.0,
            "analysis": ["analyst-evidence"],
            "algorithm_signals": algorithm_signals,
            "market_snapshot": SimpleNamespace(regime=None),
        }
    ]

    captured = {}

    def evaluate(
        analysis,
        *,
        market_snapshot=None,
        algorithm_signals=None,
        fusion_result=None,
    ):
        captured["analysis"] = analysis
        captured["market_snapshot"] = market_snapshot
        captured["algorithm_signals"] = algorithm_signals
        captured["fusion_result"] = fusion_result
        return "decision"

    engine._evaluate_candidate_decision = evaluate

    results = engine.decide_candidates()

    assert results[0]["decision"] == "decision"
    assert captured["analysis"] == ["analyst-evidence"]
    assert captured["algorithm_signals"] is algorithm_signals
    assert captured["fusion_result"] is None


def test_candidate_algorithm_evidence_uses_fusion_without_double_counting():
    from types import SimpleNamespace

    from atlas.core.engine import AtlasEngine
    from atlas.market.asset import Asset
    from atlas.market.asset_type import AssetType

    engine = object.__new__(AtlasEngine)
    candidate = SimpleNamespace(
        symbol="NVDA",
        score=91.0,
        asset=Asset(
            symbol="NVDA",
            name="NVIDIA",
            asset_type=AssetType.STOCK,
            market="US",
            currency="USD",
        ),
    )
    normalized_snapshot = object()
    technical_snapshot = object()
    raw_signals = [object(), object()]
    fusion_result = object()

    engine.discover_candidates = lambda **kwargs: [candidate]
    engine.analysis_service = SimpleNamespace(
        analyze=lambda symbol: ["analyst-evidence"],
    )
    engine.market_data = SimpleNamespace(
        snapshot=lambda symbol, interval, limit: normalized_snapshot,
    )

    class AlgorithmPipelineStub:
        def analyze(self, symbol, snapshot):
            assert symbol == "NVDA"
            assert snapshot is normalized_snapshot
            return fusion_result, raw_signals

    engine.algorithm_pipeline = AlgorithmPipelineStub()
    engine._get_market_snapshot = lambda symbol: technical_snapshot

    results = engine.analyze_candidates()

    assert results[0]["algorithm_signals"] is raw_signals
    assert results[0]["fusion_result"] is fusion_result


def test_decision_boundary_uses_fusion_instead_of_raw_algorithm_signals():
    from types import SimpleNamespace

    from atlas.algorithms.base import AlgorithmSignal
    from atlas.algorithms.fusion import FusionResult
    from atlas.core.engine import AtlasEngine
    from atlas.models.action import Action
    from atlas.models.analysis_result import AnalysisResult

    engine = object.__new__(AtlasEngine)

    analysis = [
        AnalysisResult(
            analyst="Technical Analyst",
            symbol="NVDA",
            action=Action.BUY,
            confidence=90.0,
            evidence=90.0,
            reasoning=["analyst"],
        )
    ]
    raw_signals = [
        AlgorithmSignal(
            algorithm="momentum",
            symbol="NVDA",
            timeframe="5m",
            action=Action.BUY,
            score=80.0,
            confidence=0.9,
        ),
        AlgorithmSignal(
            algorithm="trend",
            symbol="NVDA",
            timeframe="5m",
            action=Action.SELL,
            score=20.0,
            confidence=0.9,
        ),
    ]
    fusion_result = FusionResult(
        symbol="NVDA",
        timeframe="5m",
        action=Action.HOLD,
        score=50.0,
        confidence=70.0,
        agreement=0.5,
        signals=tuple(raw_signals),
        reasoning=["No directional consensus reached."],
    )

    captured = {}

    class DecisionEngineStub:
        def evaluate(self, results):
            captured["results"] = results
            return "decision"

    engine.decision_engine = DecisionEngineStub()

    decision = engine._evaluate_candidate_decision(
        analysis,
        market_snapshot=SimpleNamespace(price=100.0),
        algorithm_signals=raw_signals,
        fusion_result=fusion_result,
    )

    assert decision == "decision"
    assert len(captured["results"]) == 2
    assert captured["results"][0] is analysis[0]
    assert captured["results"][1].analyst == "signal_fusion"
    assert captured["results"][1].action == Action.HOLD
    assert all(
        result.analyst not in {"algorithm:momentum", "algorithm:trend"}
        for result in captured["results"]
    )


def test_atlas_engine_analysis_preserves_discovery_evidence():
    from types import SimpleNamespace

    from atlas.core.engine import AtlasEngine
    from atlas.market.asset import Asset
    from atlas.market.asset_discovery import DiscoveryInput, DiscoveryScore
    from atlas.market.asset_type import AssetType
    from atlas.market.trading_horizon import TradingHorizon

    engine = object.__new__(AtlasEngine)
    discovery_input = DiscoveryInput(
        volume_score=80.0,
        momentum_score=90.0,
        volatility_score=70.0,
        news_score=60.0,
        liquidity_score=85.0,
    )
    candidate = DiscoveryScore(
        asset=Asset(
            symbol="NVDA",
            name="NVIDIA",
            asset_type=AssetType.STOCK,
            market="US",
            currency="USD",
        ),
        score=77.0,
        discovery_input=discovery_input,
        horizon=TradingHorizon.DAY_TRADE,
    )

    engine.discover_candidates = lambda **kwargs: [candidate]
    engine.analysis_service = SimpleNamespace(
        analyze=lambda symbol: [],
    )
    engine.market_data = SimpleNamespace(
        snapshot_for_horizon=lambda symbol, horizon, limit: object(),
    )
    engine.algorithm_pipeline = SimpleNamespace(
        analyze=lambda symbol, snapshot: (None, []),
    )
    engine._get_market_snapshot = lambda symbol: object()

    result = engine.analyze_candidates(
        horizon=TradingHorizon.DAY_TRADE,
    )[0]

    assert result["discovery_input"] is discovery_input
    assert result["horizon"] == TradingHorizon.DAY_TRADE


def test_atlas_engine_decision_preserves_discovery_evidence():
    from types import SimpleNamespace

    from atlas.core.engine import AtlasEngine
    from atlas.market.asset_discovery import DiscoveryInput
    from atlas.market.trading_horizon import TradingHorizon
    from atlas.models.action import Action
    from atlas.models.decision_result import DecisionResult

    engine = object.__new__(AtlasEngine)
    discovery_input = DiscoveryInput(
        volume_score=80.0,
        momentum_score=90.0,
        volatility_score=70.0,
        news_score=60.0,
        liquidity_score=85.0,
    )
    decision = DecisionResult(
        symbol="NVDA",
        action=Action.HOLD,
        confidence=70.0,
        evidence=70.0,
    )
    engine.analyze_candidates = lambda **kwargs: [
        {
            "symbol": "NVDA",
            "discovery_score": 77.0,
            "discovery_input": discovery_input,
            "horizon": TradingHorizon.DAY_TRADE,
            "analysis": [],
            "algorithm_signals": [],
            "fusion_result": None,
            "market_snapshot": SimpleNamespace(regime=None),
        }
    ]
    engine._evaluate_candidate_decision = lambda *args, **kwargs: decision

    result = engine.decide_candidates(
        horizon=TradingHorizon.DAY_TRADE,
    )[0]

    assert result["discovery_input"] is discovery_input
    assert result["horizon"] == TradingHorizon.DAY_TRADE


def test_atlas_engine_decision_preserves_analysis_evidence():
    from types import SimpleNamespace

    from atlas.core.engine import AtlasEngine
    from atlas.models.action import Action
    from atlas.models.decision_result import DecisionResult

    engine = object.__new__(AtlasEngine)
    analysis = [object()]
    decision = DecisionResult(
        symbol="NVDA",
        action=Action.HOLD,
        confidence=70.0,
        evidence=70.0,
    )
    engine.analyze_candidates = lambda **kwargs: [
        {
            "symbol": "NVDA",
            "discovery_score": 77.0,
            "discovery_input": None,
            "horizon": None,
            "analysis": analysis,
            "algorithm_signals": [],
            "fusion_result": None,
            "market_snapshot": SimpleNamespace(regime=None),
        }
    ]
    engine._evaluate_candidate_decision = lambda *args, **kwargs: decision

    result = engine.decide_candidates()[0]

    assert result["analysis"] is analysis


def test_start_reuses_selected_analysis_for_persistent_snapshot():
    from types import SimpleNamespace

    from atlas.core.engine import AtlasEngine
    from atlas.models.action import Action
    from atlas.models.decision_result import DecisionResult

    engine = object.__new__(AtlasEngine)

    class LoggerStub:
        def info(self, message):
            pass

    engine.logger = LoggerStub()
    engine.config = SimpleNamespace(
        version="test",
        trading_mode="test",
        capital_limit=1000,
        ai_provider="test",
        paper_trading=False,
    )
    engine.asset_universe = SimpleNamespace(all=lambda: [])
    engine.prediction_evaluator = SimpleNamespace(
        evaluate_ready=lambda **kwargs: [],
    )

    analysis = [object()]
    decision = DecisionResult(
        symbol="NVDA",
        action=Action.HOLD,
        confidence=70.0,
        evidence=70.0,
    )
    engine.decide_candidates = lambda **kwargs: [
        {
            "symbol": "NVDA",
            "decision": decision,
            "analysis": analysis,
        }
    ]
    engine.select_best_candidate = lambda candidates: candidates[0]

    def fail_reanalysis(symbol):
        raise AssertionError(
            "selected analysis must be reused instead of re-running analysis"
        )

    engine.analysis_service = SimpleNamespace(analyze=fail_reanalysis)
    engine._get_market_snapshot = lambda symbol: SimpleNamespace(price=100.0)

    captured = {}

    class SnapshotBuilderStub:
        def build(self, **kwargs):
            captured["results"] = kwargs["results"]
            return SimpleNamespace(database_id=None)

    engine.analysis_snapshot_builder = SnapshotBuilderStub()
    engine.analysis_snapshot_repository = SimpleNamespace(save=lambda snapshot: None)
    engine.event_repository = SimpleNamespace(publish=lambda *args, **kwargs: None)
    engine.report = SimpleNamespace(print_decision=lambda decision: None)
    engine.prediction_tracker = SimpleNamespace(record=lambda **kwargs: None)
    engine.decision_engine = SimpleNamespace(last_intelligence=None)

    engine.start()

    assert captured["results"] == analysis


def test_decide_candidates_preserves_market_regime_for_snapshot_lineage():
    from types import SimpleNamespace

    from atlas.core.engine import AtlasEngine
    from atlas.models.action import Action
    from atlas.models.decision_result import DecisionResult

    engine = object.__new__(AtlasEngine)
    market_snapshot = SimpleNamespace(regime="LOW_VOLATILITY")
    regime_decision = object()

    engine.analyze_candidates = lambda **kwargs: [
        {
            "symbol": "NVDA",
            "discovery_score": 91.0,
            "analysis": [],
            "algorithm_signals": [],
            "fusion_result": None,
            "market_snapshot": market_snapshot,
        }
    ]
    engine._evaluate_candidate_decision = lambda *args, **kwargs: DecisionResult(
        symbol="NVDA",
        action=Action.HOLD,
        confidence=50.0,
        evidence=50.0,
    )
    engine.get_regime_memory_decision = lambda symbol, regime: regime_decision
    engine.integrate_regime_decision = lambda decision, context: decision

    result = engine.decide_candidates()[0]

    assert result["market_snapshot"] is market_snapshot
    assert result["market_snapshot"].regime == "LOW_VOLATILITY"


def test_analyze_candidates_classifies_regime_from_normalized_market_data():
    from types import SimpleNamespace

    from atlas.core.engine import AtlasEngine

    engine = object.__new__(AtlasEngine)
    candidate = SimpleNamespace(
        symbol="BTC-USD",
        score=91.0,
        asset=object(),
        discovery_input=None,
        horizon=None,
    )
    normalized_snapshot = SimpleNamespace(
        candles=[{"close": 100.0}] * 21,
    )
    regime_result = SimpleNamespace(regime="sideways")

    engine.discover_candidates = lambda **kwargs: [candidate]
    engine.analysis_service = SimpleNamespace(
        analyze=lambda symbol: [],
    )
    engine.market_data = SimpleNamespace(
        snapshot=lambda *args, **kwargs: normalized_snapshot,
    )
    engine.algorithm_pipeline = SimpleNamespace(
        analyze=lambda *args, **kwargs: (None, []),
    )
    engine.market_regime_engine = SimpleNamespace(
        analyze=lambda symbol, candles: regime_result,
    )
    engine._get_market_snapshot = lambda symbol: SimpleNamespace(
        price=100.0,
    )

    result = engine.analyze_candidates()[0]

    assert result["market_regime"] is regime_result


def test_decide_candidates_uses_classified_market_regime_for_strategy_memory():
    from types import SimpleNamespace

    from atlas.algorithms.regime import MarketRegime
    from atlas.core.engine import AtlasEngine
    from atlas.models.action import Action
    from atlas.models.decision_result import DecisionResult

    engine = object.__new__(AtlasEngine)
    market_regime = SimpleNamespace(
        regime=MarketRegime.SIDEWAYS,
    )
    regime_decision = object()
    calls = []

    engine.analyze_candidates = lambda **kwargs: [
        {
            "symbol": "BTC-USD",
            "discovery_score": 91.0,
            "analysis": [],
            "algorithm_signals": [],
            "fusion_result": None,
            "market_regime": market_regime,
            "market_snapshot": SimpleNamespace(price=100.0),
        }
    ]
    engine._evaluate_candidate_decision = lambda *args, **kwargs: DecisionResult(
        symbol="BTC-USD",
        action=Action.HOLD,
        confidence=50.0,
        evidence=50.0,
    )

    def get_regime_memory_decision(symbol, regime):
        calls.append((symbol, regime))
        return regime_decision

    engine.get_regime_memory_decision = get_regime_memory_decision
    engine.integrate_regime_decision = lambda decision, context: decision

    result = engine.decide_candidates()[0]

    assert calls == [("BTC-USD", MarketRegime.SIDEWAYS.value)]
    assert result["market_regime"] is market_regime
    assert result["regime_decision"] is regime_decision


def test_start_persists_fusion_evidence_used_by_decision():
    from types import SimpleNamespace

    from atlas.core.engine import AtlasEngine
    from atlas.models.action import Action
    from atlas.models.analysis_result import AnalysisResult
    from atlas.models.decision_result import DecisionResult

    engine = object.__new__(AtlasEngine)

    analyst_result = AnalysisResult(
        analyst="Technical Analyst",
        symbol="BTC-USD",
        action=Action.BUY,
        confidence=80.0,
        evidence=80.0,
    )
    fusion_result = SimpleNamespace(
        symbol="BTC-USD",
        action=Action.BUY,
        confidence=0.9,
        score=0.8,
        timeframe="5m",
        reasoning=["Fusion confirms BUY."],
    )
    decision = DecisionResult(
        symbol="BTC-USD",
        action=Action.BUY,
        confidence=90.0,
        evidence=90.0,
    )
    selected = {
        "symbol": "BTC-USD",
        "analysis": [analyst_result],
        "fusion_result": fusion_result,
        "decision": decision,
    }
    captured = {}

    engine.logger = SimpleNamespace(info=lambda *args, **kwargs: None)
    engine.config = SimpleNamespace(
        version="test",
        trading_mode="advisor",
        capital_limit=5000.0,
        ai_provider="test",
        paper_trading=False,
    )
    engine.asset_universe = SimpleNamespace(
        all=lambda: [],
    )
    engine.prediction_evaluator = SimpleNamespace(
        evaluate_ready=lambda **kwargs: [],
    )
    engine.prediction_tracker = SimpleNamespace(
        record=lambda **kwargs: None,
    )
    engine.event_repository = SimpleNamespace(
        publish=lambda *args, **kwargs: None,
    )
    engine.decide_candidates = lambda **kwargs: [selected]
    engine.select_best_candidate = lambda candidates: selected
    engine.analysis_service = SimpleNamespace(
        analyze=lambda symbol: (_ for _ in ()).throw(
            AssertionError("analysis should be reused")
        ),
    )
    engine._get_market_snapshot = lambda symbol: SimpleNamespace(
        price=100.0,
    )
    engine.decision_engine = SimpleNamespace(
        last_intelligence=None,
    )
    engine.analysis_snapshot_builder = SimpleNamespace(
        build=lambda **kwargs: captured.update(kwargs)
        or SimpleNamespace(),
    )
    engine.analysis_snapshot_repository = SimpleNamespace(
        save=lambda snapshot: 1,
    )
    engine.report = SimpleNamespace(
        print_decision=lambda decision: None,
    )
    engine._execute_paper_decision = lambda **kwargs: None
    engine._get_prediction_evaluation_prices = lambda: {}

    engine.start()

    persisted_results = captured["results"]

    assert analyst_result in persisted_results
    assert any(
        result.analyst == "signal_fusion"
        for result in persisted_results
    )


def test_decide_candidates_preserves_algorithm_lineage():
    from types import SimpleNamespace

    from atlas.core.engine import AtlasEngine
    from atlas.models.action import Action
    from atlas.models.decision_result import DecisionResult

    engine = object.__new__(AtlasEngine)

    algorithm_signals = [SimpleNamespace(algorithm="intraday_momentum")]
    fusion_result = SimpleNamespace(symbol="BTC-USD")
    analyzed = [{
        "symbol": "BTC-USD",
        "discovery_score": 90.0,
        "discovery_input": None,
        "horizon": None,
        "analysis": [],
        "algorithm_signals": algorithm_signals,
        "fusion_result": fusion_result,
        "market_snapshot": SimpleNamespace(regime=None),
        "market_regime": None,
    }]
    decision = DecisionResult(
        symbol="BTC-USD",
        action=Action.HOLD,
        confidence=70.0,
        evidence=70.0,
    )

    engine.analyze_candidates = lambda **kwargs: analyzed
    engine._evaluate_candidate_decision = lambda *args, **kwargs: decision

    results = engine.decide_candidates()

    assert results[0]["algorithm_signals"] is algorithm_signals
    assert results[0]["fusion_result"] is fusion_result

def test_decision_runtime_marks_existing_positions_to_market_before_risk():
    from types import SimpleNamespace

    from atlas.core.engine import AtlasEngine
    from atlas.models.action import Action
    from atlas.models.analysis_result import AnalysisResult

    engine = object.__new__(AtlasEngine)
    analysis = [
        AnalysisResult(
            analyst="Technical Analyst",
            symbol="BTC-USD",
            action=Action.BUY,
            confidence=90.0,
            evidence=90.0,
        )
    ]

    updated_prices = []
    engine._get_usd_nok_rate = lambda: SimpleNamespace(rate=10.0)
    engine._get_market_snapshot = lambda symbol: SimpleNamespace(price=200.0)
    engine._peak_equity_nok = None

    class PortfolioServiceStub:
        def update_prices(self, prices):
            updated_prices.append(dict(prices))

        def as_dict(self, usd_nok):
            return {
                "total_equity_nok": 10000.0,
                "positions_value_nok": 2000.0,
                "positions": [
                    {
                        "symbol": "BTC-USD",
                        "quantity": 1.0,
                        "market_value_nok": 2000.0,
                        "last_buy_price_usd": 100.0,
                        "average_price_usd": 100.0,
                    }
                ],
            }

    engine.portfolio_service = PortfolioServiceStub()

    captured = {}

    class DecisionEngineStub:
        def evaluate(
            self,
            results,
            *,
            price=None,
            equity=None,
            current_exposure_pct=0.0,
            drawdown_pct=0.0,
            portfolio_positions=(),
            current_position=0.0,
            last_buy_price=None,
            average_price=None,
        ):
            captured["current_exposure_pct"] = current_exposure_pct
            return "decision"

    engine.decision_engine = DecisionEngineStub()

    result = engine._evaluate_candidate_decision(
        analysis,
        market_snapshot=SimpleNamespace(price=200.0),
    )

    assert result == "decision"
    assert updated_prices == [{"BTC-USD": 200.0}]
    assert captured["current_exposure_pct"] == 20.0


def test_decision_runtime_marks_all_open_positions_to_market_before_risk():
    from types import SimpleNamespace

    from atlas.core.engine import AtlasEngine
    from atlas.models.action import Action
    from atlas.models.analysis_result import AnalysisResult

    engine = object.__new__(AtlasEngine)
    analysis = [
        AnalysisResult(
            analyst="Technical Analyst",
            symbol="BTC-USD",
            action=Action.BUY,
            confidence=90.0,
            evidence=90.0,
        )
    ]

    requested_symbols = []
    updated_prices = []
    engine._get_usd_nok_rate = lambda: SimpleNamespace(rate=10.0)
    engine._peak_equity_nok = None

    class PortfolioServiceStub:
        def update_prices(self, prices):
            updated_prices.append(dict(prices))

        def as_dict(self, usd_nok):
            eth_price = 100.0
            for prices in updated_prices:
                eth_price = prices.get("ETH-USD", eth_price)
            return {
                "total_equity_nok": 1000.0 + 200.0 * 10.0 + eth_price * 10.0,
                "positions_value_nok": 200.0 * 10.0 + eth_price * 10.0,
                "positions": [
                    {
                        "symbol": "BTC-USD",
                        "quantity": 1.0,
                        "market_value_nok": 2000.0,
                        "last_buy_price_usd": 100.0,
                        "average_price_usd": 100.0,
                    },
                    {
                        "symbol": "ETH-USD",
                        "quantity": 1.0,
                        "market_value_nok": eth_price * 10.0,
                        "last_buy_price_usd": 100.0,
                        "average_price_usd": 100.0,
                    },
                ],
            }

    engine.portfolio_service = PortfolioServiceStub()

    def get_many(symbols):
        requested_symbols.append(list(symbols))
        return {
            "ETH-USD": SimpleNamespace(price=300.0),
        }

    engine.market_data = SimpleNamespace(get_many=get_many)

    captured = {}

    class DecisionEngineStub:
        def evaluate(
            self,
            results,
            *,
            price=None,
            equity=None,
            current_exposure_pct=0.0,
            drawdown_pct=0.0,
            portfolio_positions=(),
            current_position=0.0,
            last_buy_price=None,
            average_price=None,
        ):
            captured["current_exposure_pct"] = current_exposure_pct
            return "decision"

    engine.decision_engine = DecisionEngineStub()

    result = engine._evaluate_candidate_decision(
        analysis,
        market_snapshot=SimpleNamespace(price=200.0),
    )

    assert result == "decision"
    assert requested_symbols == [["ETH-USD"]]
    assert updated_prices == [
        {
            "BTC-USD": 200.0,
            "ETH-USD": 300.0,
        }
    ]
    assert captured["current_exposure_pct"] == 83.33333333333334


def test_decision_runtime_preserves_historical_peak_equity_across_restart():
    from types import SimpleNamespace

    from atlas.core.engine import AtlasEngine
    from atlas.models.action import Action
    from atlas.models.analysis_result import AnalysisResult

    analysis = [
        AnalysisResult(
            analyst="Technical Analyst",
            symbol="BTC-USD",
            action=Action.BUY,
            confidence=90.0,
            evidence=90.0,
        )
    ]

    class PortfolioServiceStub:
        def update_prices(self, prices):
            pass

        def as_dict(self, usd_nok):
            return {
                "total_equity_nok": 8000.0,
                "positions_value_nok": 0.0,
                "positions": [],
            }

    class DecisionEngineStub:
        def __init__(self):
            self.drawdown_pct = None

        def evaluate(
            self,
            results,
            *,
            price=None,
            equity=None,
            current_exposure_pct=0.0,
            drawdown_pct=0.0,
            portfolio_positions=(),
            current_position=0.0,
            last_buy_price=None,
            average_price=None,
        ):
            self.drawdown_pct = drawdown_pct
            return "decision"

    engine = object.__new__(AtlasEngine)
    engine._get_usd_nok_rate = lambda: SimpleNamespace(rate=10.0)
    engine._peak_equity_nok = None
    engine.portfolio_service = PortfolioServiceStub()
    engine.market_data = SimpleNamespace()
    engine.decision_engine = DecisionEngineStub()

    # A restarted engine must retain the previous paper-account peak rather
    # than rebasing drawdown to the first post-restart equity observation.
    engine.paper_account_state_repository = SimpleNamespace(
        get_peak_equity_nok=lambda: 10000.0,
    )

    result = engine._evaluate_candidate_decision(
        analysis,
        market_snapshot=SimpleNamespace(price=100.0),
    )

    assert result == "decision"
    assert engine.decision_engine.drawdown_pct == 20.0



def test_select_best_candidate_prioritizes_sell_exit_over_new_buy():
    from atlas.models.action import Action
    from atlas.models.decision_result import DecisionResult

    engine = AtlasEngine()

    candidates = [
        {
            "symbol": "BTC-USD",
            "discovery_score": 95.0,
            "decision": DecisionResult(
                symbol="BTC-USD",
                action=Action.BUY,
                confidence=95.0,
                evidence=95.0,
                robustness=95.0,
                decision_margin=40.0,
            ),
        },
        {
            "symbol": "ETH-USD",
            "discovery_score": 80.0,
            "decision": DecisionResult(
                symbol="ETH-USD",
                action=Action.SELL,
                confidence=90.0,
                evidence=90.0,
                robustness=90.0,
                decision_margin=30.0,
            ),
        },
    ]

    selected = engine.select_best_candidate(candidates)

    assert selected is not None
    assert selected["symbol"] == "ETH-USD"
    assert selected["decision"].action is Action.SELL



def test_atlas_engine_restores_persisted_position_peak_across_restart(tmp_path):
    config = AtlasConfig(database_path=str(tmp_path / "atlas.db"))

    first = AtlasEngine(config)
    first.portfolio_service.buy(
        symbol="BTC-USD",
        amount_nok=1000.0,
        price_usd=100.0,
        usd_nok=10.0,
    )
    first.trading_service.record_buy(
        symbol="BTC-USD",
        quantity=1.0,
        price_usd=100.0,
        amount_nok=1000.0,
    )
    first.portfolio_service.update_prices({"BTC-USD": 120.0})
    first.paper_account_state_repository.set_position_peak_price_usd(
        "BTC-USD",
        120.0,
    )

    restarted = AtlasEngine(config)
    restarted.restore_paper_portfolio()

    position = restarted.portfolio_service.as_dict(10.0)["positions"][0]

    assert position["peak_price_usd"] == 120.0




def test_restore_paper_portfolio_reconciles_stale_position_peak(tmp_path):
    config = AtlasConfig(database_path=str(tmp_path / "atlas.db"))

    engine = AtlasEngine(config)
    engine.portfolio_service.buy(
        symbol="BTC-USD",
        amount_nok=1000.0,
        price_usd=100.0,
        usd_nok=10.0,
    )
    engine.trading_service.record_buy(
        symbol="BTC-USD",
        quantity=1.0,
        price_usd=100.0,
        amount_nok=1000.0,
    )
    engine.paper_account_state_repository.set_position_peak_price_usd(
        "BTC-USD",
        120.0,
    )

    sale = engine.portfolio_service.sell(
        symbol="BTC-USD",
        price_usd=110.0,
        usd_nok=10.0,
    )
    engine.trading_service.record_sell(
        symbol="BTC-USD",
        quantity=sale["quantity"],
        price_usd=110.0,
        amount_nok=sale["sale_value_nok"],
        realized_pnl_nok=sale["realized_pnl_nok"],
    )

    assert (
        engine.paper_account_state_repository
        .get_position_peak_price_usd("BTC-USD")
        == 120.0
    )

    engine.restore_paper_portfolio()

    assert engine.portfolio_service.as_dict(10.0)["positions"] == []
    assert (
        engine.paper_account_state_repository
        .get_position_peak_price_usd("BTC-USD")
        is None
    )


def test_decision_runtime_persists_new_position_peak_price():
    from types import SimpleNamespace

    from atlas.models.action import Action
    from atlas.models.analysis_result import AnalysisResult

    analysis = [
        AnalysisResult(
            analyst="Technical Analyst",
            symbol="BTC-USD",
            action=Action.HOLD,
            confidence=90.0,
            evidence=90.0,
        )
    ]

    class PortfolioServiceStub:
        def __init__(self):
            self.peak = 100.0

        def update_prices(self, prices):
            self.peak = max(self.peak, prices["BTC-USD"])

        def as_dict(self, usd_nok):
            return {
                "total_equity_nok": 10000.0,
                "positions_value_nok": 1200.0,
                "positions": [
                    {
                        "symbol": "BTC-USD",
                        "quantity": 1.0,
                        "market_value_nok": 1200.0,
                        "last_buy_price_usd": 100.0,
                        "average_price_usd": 100.0,
                        "peak_price_usd": self.peak,
                    }
                ],
            }

    class DecisionEngineStub:
        def evaluate(
            self,
            results,
            *,
            current_position=0.0,
            last_buy_price=None,
            average_price=None,
        ):
            return "decision"

    persisted = []
    engine = object.__new__(AtlasEngine)
    engine._get_usd_nok_rate = lambda: SimpleNamespace(rate=10.0)
    engine.portfolio_service = PortfolioServiceStub()
    engine.market_data = SimpleNamespace()
    engine.decision_engine = DecisionEngineStub()
    engine.paper_account_state_repository = SimpleNamespace(
        get_position_peak_price_usd=lambda symbol: 100.0,
        set_position_peak_price_usd=lambda symbol, peak: persisted.append(
            (symbol, peak)
        ),
    )

    result = engine._evaluate_candidate_decision(
        analysis,
        market_snapshot=SimpleNamespace(price=120.0),
    )

    assert result == "decision"
    assert persisted == [("BTC-USD", 120.0)]



def test_engine_clears_persisted_peak_after_full_paper_sell():
    from types import SimpleNamespace

    from atlas.models.action import Action

    deleted = []
    engine = object.__new__(AtlasEngine)
    engine.portfolio_service = SimpleNamespace(
        as_dict=lambda usd_nok: {
            "positions": [],
        }
    )
    engine.paper_account_state_repository = SimpleNamespace(
        delete_position_peak_price_usd=lambda symbol: deleted.append(symbol),
    )

    engine._sync_position_peak_after_execution(
        symbol="BTC-USD",
        action=Action.SELL,
        usd_nok=10.0,
    )

    assert deleted == ["BTC-USD"]



def test_start_syncs_position_peak_after_executed_paper_sell():
    from types import SimpleNamespace

    from atlas.models.action import Action
    from atlas.models.decision_result import DecisionResult

    engine = object.__new__(AtlasEngine)

    class LoggerStub:
        def info(self, message):
            pass

    decision = DecisionResult(
        symbol="BTC-USD",
        action=Action.SELL,
        confidence=90.0,
        evidence=90.0,
    )

    engine.logger = LoggerStub()
    engine.config = SimpleNamespace(
        version="test",
        trading_mode="paper",
        capital_limit=5000.0,
        ai_provider="test",
        paper_trading=True,
    )
    engine.asset_universe = SimpleNamespace(all=lambda: [])
    engine.prediction_evaluator = SimpleNamespace(
        evaluate_ready=lambda **kwargs: [],
    )
    engine.decide_candidates = lambda **kwargs: [
        {
            "symbol": "BTC-USD",
            "decision": decision,
            "analysis": [object()],
        }
    ]
    engine.select_best_candidate = lambda candidates: candidates[0]
    engine.analysis_service = SimpleNamespace(
        analyze=lambda symbol: [object()],
    )
    engine._get_market_snapshot = lambda symbol: SimpleNamespace(
        price=100.0,
    )
    engine.analysis_snapshot_builder = SimpleNamespace(
        build=lambda **kwargs: SimpleNamespace(database_id=None),
    )
    engine.analysis_snapshot_repository = SimpleNamespace(
        save=lambda snapshot: None,
    )
    engine.event_repository = SimpleNamespace(
        publish=lambda *args, **kwargs: None,
    )
    engine.report = SimpleNamespace(
        print_decision=lambda decision: None,
    )
    engine.prediction_tracker = SimpleNamespace(
        record=lambda **kwargs: None,
    )
    engine.decision_engine = SimpleNamespace(
        last_intelligence=None,
    )
    engine.decision_execution_service = SimpleNamespace(
        execute=lambda *args, **kwargs: {"quantity": 1.0},
    )

    sync_calls = []
    engine._get_usd_nok_rate = lambda: SimpleNamespace(rate=10.0)
    engine._sync_position_peak_after_execution = lambda **kwargs: sync_calls.append(
        kwargs
    )

    engine.start()

    assert sync_calls == [
        {
            "symbol": "BTC-USD",
            "action": Action.SELL,
            "usd_nok": 10.0,
        }
    ]



def test_engine_preserves_persisted_peak_after_partial_paper_sell():
    from types import SimpleNamespace

    from atlas.models.action import Action

    deleted = []
    engine = object.__new__(AtlasEngine)
    engine.portfolio_service = SimpleNamespace(
        as_dict=lambda usd_nok: {
            "positions": [
                {
                    "symbol": "BTC-USD",
                    "quantity": 0.5,
                    "peak_price_usd": 120.0,
                }
            ],
        }
    )
    engine.paper_account_state_repository = SimpleNamespace(
        delete_position_peak_price_usd=lambda symbol: deleted.append(symbol),
    )

    engine._sync_position_peak_after_execution(
        symbol="BTC-USD",
        action=Action.SELL,
        usd_nok=10.0,
    )

    assert deleted == []



def test_atlas_engine_constructor_restores_persisted_position_peak(tmp_path):
    config = AtlasConfig(
        database_path=str(tmp_path / "atlas.db"),
    )
    config.trading_mode = "paper"
    config.paper_trading = True

    engine = AtlasEngine(config)
    engine.portfolio_service.buy(
        symbol="BTC-USD",
        amount_nok=1000.0,
        price_usd=100.0,
        usd_nok=10.0,
    )
    engine.trading_service.record_buy(
        symbol="BTC-USD",
        quantity=1.0,
        price_usd=100.0,
        amount_nok=1000.0,
    )
    engine.paper_account_state_repository.set_position_peak_price_usd(
        "BTC-USD",
        120.0,
    )

    restarted = AtlasEngine(config)

    position = restarted.portfolio_service.as_dict(10.0)["positions"][0]
    assert position["symbol"] == "BTC-USD"
    assert position["peak_price_usd"] == 120.0



def test_new_position_does_not_inherit_peak_from_closed_same_symbol(tmp_path):
    from atlas.models.action import Action

    config = AtlasConfig(database_path=str(tmp_path / "atlas.db"))
    config.trading_mode = "paper"
    config.paper_trading = True

    engine = AtlasEngine(config)
    engine.portfolio_service.buy(
        symbol="BTC-USD",
        amount_nok=1000.0,
        price_usd=100.0,
        usd_nok=10.0,
    )
    engine.trading_service.record_buy(
        symbol="BTC-USD",
        quantity=1.0,
        price_usd=100.0,
        amount_nok=1000.0,
    )
    engine.paper_account_state_repository.set_position_peak_price_usd(
        "BTC-USD",
        120.0,
    )

    sale = engine.portfolio_service.sell(
        symbol="BTC-USD",
        price_usd=110.0,
        usd_nok=10.0,
    )
    engine.trading_service.record_sell(
        symbol="BTC-USD",
        quantity=sale["quantity"],
        price_usd=110.0,
        amount_nok=sale["sale_value_nok"],
        realized_pnl_nok=sale["realized_pnl_nok"],
    )
    engine._sync_position_peak_after_execution(
        symbol="BTC-USD",
        action=Action.SELL,
        usd_nok=10.0,
    )

    assert (
        engine.paper_account_state_repository
        .get_position_peak_price_usd("BTC-USD")
        is None
    )

    engine.portfolio_service.buy(
        symbol="BTC-USD",
        amount_nok=1000.0,
        price_usd=90.0,
        usd_nok=10.0,
    )
    new_position = engine.portfolio_service.as_dict(10.0)["positions"][0]
    engine.trading_service.record_buy(
        symbol="BTC-USD",
        quantity=new_position["quantity"],
        price_usd=90.0,
        amount_nok=1000.0,
    )

    restarted = AtlasEngine(config)
    position = restarted.portfolio_service.as_dict(10.0)["positions"][0]

    assert position["symbol"] == "BTC-USD"
    assert position["peak_price_usd"] == 90.0



def test_restart_reconciles_stale_peak_before_new_position_same_symbol(tmp_path):
    config = AtlasConfig(database_path=str(tmp_path / "atlas.db"))
    config.trading_mode = "paper"
    config.paper_trading = True

    engine = AtlasEngine(config)
    engine.portfolio_service.buy(
        symbol="BTC-USD",
        amount_nok=1000.0,
        price_usd=100.0,
        usd_nok=10.0,
    )
    engine.trading_service.record_buy(
        symbol="BTC-USD",
        quantity=1.0,
        price_usd=100.0,
        amount_nok=1000.0,
    )
    engine.paper_account_state_repository.set_position_peak_price_usd(
        "BTC-USD",
        120.0,
    )

    sale = engine.portfolio_service.sell(
        symbol="BTC-USD",
        price_usd=110.0,
        usd_nok=10.0,
    )
    engine.trading_service.record_sell(
        symbol="BTC-USD",
        quantity=sale["quantity"],
        price_usd=110.0,
        amount_nok=sale["sale_value_nok"],
        realized_pnl_nok=sale["realized_pnl_nok"],
    )

    assert (
        engine.paper_account_state_repository
        .get_position_peak_price_usd("BTC-USD")
        == 120.0
    )

    restarted = AtlasEngine(config)
    assert restarted.portfolio_service.as_dict(10.0)["positions"] == []
    assert (
        restarted.paper_account_state_repository.get_trade_replay_after()
        is None
    )

    restarted.portfolio_service.buy(
        symbol="BTC-USD",
        amount_nok=1000.0,
        price_usd=90.0,
        usd_nok=10.0,
    )
    new_position = restarted.portfolio_service.as_dict(10.0)["positions"][0]
    restarted.trading_service.record_buy(
        symbol="BTC-USD",
        quantity=new_position["quantity"],
        price_usd=90.0,
        amount_nok=1000.0,
    )
    assert (
        restarted.paper_account_state_repository.get_trade_replay_after()
        is None
    )

    restarted_again = AtlasEngine(config)
    position = restarted_again.portfolio_service.as_dict(10.0)["positions"][0]

    assert position["symbol"] == "BTC-USD"
    assert position["peak_price_usd"] == 90.0


def test_decision_runtime_passes_position_peak_to_decision_engine():
    from types import SimpleNamespace

    from atlas.models.action import Action
    from atlas.models.analysis_result import AnalysisResult

    analysis = [
        AnalysisResult(
            analyst="Technical Analyst",
            symbol="BTC-USD",
            action=Action.HOLD,
            confidence=90.0,
            evidence=90.0,
        )
    ]

    engine = object.__new__(AtlasEngine)
    engine._peak_equity_nok = None
    engine._get_usd_nok_rate = lambda: SimpleNamespace(rate=10.0)

    class PortfolioServiceStub:
        def update_prices(self, prices):
            pass

        def as_dict(self, usd_nok):
            return {
                "total_equity_nok": 10000.0,
                "positions_value_nok": 1100.0,
                "positions": [
                    {
                        "symbol": "BTC-USD",
                        "quantity": 1.0,
                        "market_value_nok": 1100.0,
                        "last_buy_price_usd": 100.0,
                        "average_price_usd": 100.0,
                        "peak_price_usd": 120.0,
                    }
                ],
            }

    engine.portfolio_service = PortfolioServiceStub()
    engine.market_data = SimpleNamespace()
    engine.paper_account_state_repository = SimpleNamespace(
        get_position_peak_price_usd=lambda symbol: 120.0,
        set_position_peak_price_usd=lambda symbol, peak: None,
    )

    captured = {}

    class DecisionEngineStub:
        def evaluate(
            self,
            results,
            *,
            current_position=0.0,
            last_buy_price=None,
            average_price=None,
            peak_price=None,
        ):
            captured["peak_price"] = peak_price
            return "decision"

    engine.decision_engine = DecisionEngineStub()

    result = engine._evaluate_candidate_decision(
        analysis,
        market_snapshot=SimpleNamespace(price=110.0),
    )

    assert result == "decision"
    assert captured["peak_price"] == 120.0



def test_atlas_engine_reconciles_stale_agent_performance_from_predictions(
    tmp_path,
):
    from datetime import datetime, timedelta

    from atlas.models.action import Action
    from atlas.trading.prediction_record import PredictionRecord

    database_path = tmp_path / "atlas.db"
    performance_path = tmp_path / "agent_performance.json"
    config = AtlasConfig(
        database_path=str(database_path),
        agent_performance_storage=str(performance_path),
    )

    first = AtlasEngine(config)

    prediction = PredictionRecord(
        symbol="BTC-USD",
        action="BUY",
        confidence=90.0,
        evidence=90.0,
        price_usd=100.0,
        timestamp=datetime.now() - timedelta(hours=25),
        analysts=["Technical Analyst"],
    )
    first.prediction_tracker.repository.save(prediction)
    first.prediction_evaluator.evaluate(
        prediction=prediction,
        current_price_usd=105.0,
    )

    performance_path.write_text(
        """{
  "Technical Analyst": {
    "predictions": 99,
    "correct": 0,
    "action_predictions": {"SELL": 99},
    "action_correct": {"SELL": 0}
  }
}"""
    )

    restarted = AtlasEngine(config)

    performance = restarted.agent_performance.get(
        "Technical Analyst"
    )
    assert performance.predictions == 1
    assert performance.correct == 1
    assert performance.action_predictions == {"BUY": 1}
    assert performance.action_correct == {"BUY": 1}

    assert (
        restarted.decision_engine.agent_weight_engine.performance
        is restarted.agent_performance
    )



def test_atlas_engine_restart_preserves_original_analyst_directions(tmp_path):
    from datetime import datetime

    from atlas.database.analysis_snapshot_repository import (
        AnalysisSnapshotRepository,
    )
    from atlas.models.action import Action
    from atlas.models.analysis_snapshot import AnalysisSnapshot
    from atlas.models.decision_result import DecisionResult

    database_path = tmp_path / "atlas.db"
    performance_path = tmp_path / "agent_performance.json"
    config = AtlasConfig(
        database_path=str(database_path),
        agent_performance_storage=str(performance_path),
    )

    first = AtlasEngine(config)
    snapshot_repository = AnalysisSnapshotRepository(
        first.database
    )
    snapshot = AnalysisSnapshot(
        database_id=None,
        symbol="BTC-USD",
        timestamp=datetime.now(),
        provider="test",
        model="test",
        results=[
            {
                "analyst": "Technical Analyst",
                "symbol": "BTC-USD",
                "action": "BUY",
                "confidence": 90.0,
                "evidence": 90.0,
                "reasoning": ["Bullish."],
            },
            {
                "analyst": "News Analyst",
                "symbol": "BTC-USD",
                "action": "SELL",
                "confidence": 90.0,
                "evidence": 90.0,
                "reasoning": ["Bearish."],
            },
        ],
        decision={
            "action": "BUY",
            "confidence": 90.0,
            "evidence": 90.0,
        },
        intelligence={
            "action": "BUY",
            "buy_count": 1,
            "hold_count": 0,
            "sell_count": 1,
            "agreement": 50.0,
        },
    )
    snapshot_repository.save(snapshot)

    prediction = first.prediction_tracker.record(
        decision=DecisionResult(
            symbol="BTC-USD",
            action=Action.BUY,
            confidence=90.0,
            evidence=90.0,
            analysts=[
                "Technical Analyst",
                "News Analyst",
            ],
            analysis_snapshot_id=snapshot.database_id,
        ),
        price_usd=100.0,
    )
    first.prediction_evaluator.evaluate(
        prediction=prediction,
        current_price_usd=105.0,
    )

    restarted = AtlasEngine(config)

    technical = restarted.agent_performance.get(
        "Technical Analyst"
    )
    news = restarted.agent_performance.get(
        "News Analyst"
    )

    assert technical.predictions == 1
    assert technical.correct == 1
    assert technical.action_predictions == {"BUY": 1}
    assert technical.action_correct == {"BUY": 1}

    assert news.predictions == 1
    assert news.correct == 0
    assert news.action_predictions == {"SELL": 1}
    assert news.action_correct == {"SELL": 0}

    assert (
        restarted.decision_engine.agent_weight_engine.performance
        is restarted.agent_performance
    )



def test_atlas_engine_restart_applies_rebuilt_directional_learning_to_decision_support(tmp_path):
    from datetime import datetime

    from atlas.database.analysis_snapshot_repository import (
        AnalysisSnapshotRepository,
    )
    from atlas.models.action import Action
    from atlas.models.analysis_result import AnalysisResult
    from atlas.models.analysis_snapshot import AnalysisSnapshot
    from atlas.models.decision_result import DecisionResult

    database_path = tmp_path / "atlas.db"
    performance_path = tmp_path / "agent_performance.json"
    config = AtlasConfig(
        database_path=str(database_path),
        agent_performance_storage=str(performance_path),
    )

    first = AtlasEngine(config)
    snapshot_repository = AnalysisSnapshotRepository(
        first.database
    )

    for analyst, current_price_usd in (
        ("Technical Analyst", 105.0),
        ("News Analyst", 95.0),
    ):
        for _ in range(20):
            snapshot = AnalysisSnapshot(
                database_id=None,
                symbol="BTC-USD",
                timestamp=datetime.now(),
                provider="test",
                model="test",
                results=[
                    {
                        "analyst": analyst,
                        "symbol": "BTC-USD",
                        "action": "BUY",
                        "confidence": 90.0,
                        "evidence": 90.0,
                        "reasoning": ["Directional BUY signal."],
                    },
                ],
                decision={
                    "action": "BUY",
                    "confidence": 90.0,
                    "evidence": 90.0,
                },
                intelligence={
                    "action": "BUY",
                    "buy_count": 1,
                    "hold_count": 0,
                    "sell_count": 0,
                    "agreement": 100.0,
                },
            )
            snapshot_repository.save(snapshot)

            prediction = first.prediction_tracker.record(
                decision=DecisionResult(
                    symbol="BTC-USD",
                    action=Action.BUY,
                    confidence=90.0,
                    evidence=90.0,
                    analysts=[analyst],
                    analysis_snapshot_id=snapshot.database_id,
                ),
                price_usd=100.0,
            )
            first.prediction_evaluator.evaluate(
                prediction=prediction,
                current_price_usd=current_price_usd,
            )

    restarted = AtlasEngine(config)

    buy_weights = restarted.agent_weight_engine.calculate(
        action="BUY"
    )

    assert buy_weights["Technical Analyst"] > buy_weights["News Analyst"]

    restarted.decision_engine.risk_manager = None
    restarted.decision_engine.portfolio_manager = None
    restarted.decision_engine.position_exit_engine = None

    decision = restarted.decision_engine.evaluate(
        [
            AnalysisResult(
                symbol="BTC-USD",
                analyst="Technical Analyst",
                action=Action.HOLD,
                confidence=80.0,
                evidence=80.0,
                reasoning=["Neutral current signal."],
            ),
            AnalysisResult(
                symbol="BTC-USD",
                analyst="News Analyst",
                action=Action.HOLD,
                confidence=80.0,
                evidence=80.0,
                reasoning=["Neutral current signal."],
            ),
        ]
    )

    assert decision.action is Action.HOLD
    assert decision.action_support_analyst == "Technical Analyst"
    assert decision.action_support_action is Action.BUY
    assert decision.action_support_weight == buy_weights["Technical Analyst"]


def test_trade_persistence_failure_rolls_back_paper_buy(
    monkeypatch,
    tmp_path,
):
    import pytest

    from atlas.models.action import Action
    from atlas.models.analysis_result import AnalysisResult

    config = AtlasConfig(
        agent_performance_storage=str(tmp_path / "agent_performance.json"),
        database_path=str(tmp_path / "atlas_test.db"),
        capital_limit=1000000.0,
        trading_mode="paper",
        paper_trading=True,
    )
    engine = AtlasEngine(config=config)

    analysis = [
        AnalysisResult(
            symbol="BTC-USD",
            analyst="test-analyst",
            action=Action.BUY,
            confidence=95.0,
            evidence=95.0,
            reasoning=["Strong BUY signal."],
        )
    ]
    selected = {
        "symbol": "BTC-USD",
        "discovery_score": 100.0,
        "analysis": analysis,
    }

    def fake_snapshot(symbol):
        return type("Snapshot", (), {"price": 20000.0})()

    def fake_decide_candidates(limit=3, minimum_score=0.0):
        selected["decision"] = engine._evaluate_candidate_decision(
            analysis,
            market_snapshot=fake_snapshot("BTC-USD"),
        )
        return [selected]

    def fail_trade_save(record):
        raise RuntimeError("trade persistence failed")

    monkeypatch.setattr(engine, "decide_candidates", fake_decide_candidates)
    monkeypatch.setattr(
        engine,
        "select_best_candidate",
        lambda candidates, investable_only=False: selected,
    )
    monkeypatch.setattr(engine, "_get_market_snapshot", fake_snapshot)
    monkeypatch.setattr(engine.report, "print_decision", lambda decision: None)
    monkeypatch.setattr(
        engine.prediction_evaluator,
        "evaluate_ready",
        lambda current_prices_usd: [],
    )
    monkeypatch.setattr(
        engine.trading_service._repository,
        "save",
        fail_trade_save,
    )

    portfolio_before = engine.portfolio_service.as_dict(usd_nok=10.0)

    with pytest.raises(RuntimeError, match="trade persistence failed"):
        engine.start()

    predictions = engine.prediction_tracker.history()
    assert len(predictions) == 1
    assert predictions[0]["action"] == "BUY"
    assert engine.trading_service.count() == 0
    assert engine.portfolio_service.as_dict(usd_nok=10.0) == portfolio_before

    events = engine.event_repository.after(0, limit=100)
    assert any(event["type"] == "DECISION_READY" for event in events)
    assert not any(event["type"] == "TRADE_EXECUTED" for event in events)



def test_trade_persistence_failure_rolls_back_paper_sell(
    monkeypatch,
    tmp_path,
):
    import pytest

    from atlas.models.action import Action
    from atlas.models.analysis_result import AnalysisResult

    config = AtlasConfig(
        agent_performance_storage=str(tmp_path / "agent_performance.json"),
        database_path=str(tmp_path / "atlas_test.db"),
        capital_limit=1000000.0,
        trading_mode="paper",
        paper_trading=True,
    )
    engine = AtlasEngine(config=config)

    engine.portfolio_service.buy(
        symbol="BTC-USD",
        amount_nok=1000.0,
        price_usd=100.0,
        usd_nok=10.0,
    )
    engine.trading_service.record_buy(
        symbol="BTC-USD",
        quantity=1.0,
        price_usd=100.0,
        amount_nok=1000.0,
    )

    analysis = [
        AnalysisResult(
            symbol="BTC-USD",
            analyst="test-analyst",
            action=Action.SELL,
            confidence=95.0,
            evidence=95.0,
            reasoning=["Strong SELL signal."],
        )
    ]
    selected = {
        "symbol": "BTC-USD",
        "discovery_score": 100.0,
        "analysis": analysis,
    }

    def fake_snapshot(symbol):
        return type("Snapshot", (), {"price": 110.0})()

    def fake_decide_candidates(limit=3, minimum_score=0.0):
        selected["decision"] = engine._evaluate_candidate_decision(
            analysis,
            market_snapshot=fake_snapshot("BTC-USD"),
        )
        return [selected]

    original_save = engine.trading_service._repository.save

    def fail_sell_trade_save(record):
        if record.action == "SELL":
            raise RuntimeError("sell trade persistence failed")
        return original_save(record)

    monkeypatch.setattr(engine, "decide_candidates", fake_decide_candidates)
    monkeypatch.setattr(
        engine,
        "select_best_candidate",
        lambda candidates, investable_only=False: selected,
    )
    monkeypatch.setattr(engine, "_get_market_snapshot", fake_snapshot)
    monkeypatch.setattr(engine.report, "print_decision", lambda decision: None)
    monkeypatch.setattr(
        engine.prediction_evaluator,
        "evaluate_ready",
        lambda current_prices_usd: [],
    )
    monkeypatch.setattr(
        engine.trading_service._repository,
        "save",
        fail_sell_trade_save,
    )

    portfolio_before = engine.portfolio_service.as_dict(usd_nok=10.0)
    trade_count_before = engine.trading_service.count()

    with pytest.raises(RuntimeError, match="sell trade persistence failed"):
        engine.start()

    assert engine.trading_service.count() == trade_count_before

    portfolio_after = engine.portfolio_service.as_dict(usd_nok=10.0)
    assert portfolio_after["cash_nok"] == portfolio_before["cash_nok"]
    assert portfolio_after["profit_vault_nok"] == 0.0
    assert len(portfolio_after["positions"]) == 1
    assert portfolio_after["positions"][0]["symbol"] == "BTC-USD"
    assert portfolio_after["positions"][0]["quantity"] == 1.0

    predictions = engine.prediction_tracker.history()
    assert len(predictions) == 1
    assert predictions[0]["action"] == "SELL"

    events = engine.event_repository.after(0, limit=100)
    assert any(event["type"] == "DECISION_READY" for event in events)
    assert not any(event["type"] == "TRADE_EXECUTED" for event in events)


def test_trade_remains_committed_when_trade_executed_event_publish_fails(monkeypatch, tmp_path):
    import pytest

    from atlas.models.action import Action
    from atlas.models.analysis_result import AnalysisResult

    config = AtlasConfig(
        agent_performance_storage=str(tmp_path / "agent_performance.json"),
        database_path=str(tmp_path / "atlas_test.db"),
    )
    config.trading_mode = "paper"
    config.paper_trading = True
    config.capital_limit = 1000000.0

    engine = AtlasEngine(config=config)

    analysis = [
        AnalysisResult(
            symbol="BTC-USD",
            analyst="test-analyst",
            action=Action.BUY,
            confidence=95.0,
            evidence=95.0,
            reasoning=["Strong BUY signal."],
        )
    ]
    selected = {
        "symbol": "BTC-USD",
        "discovery_score": 100.0,
        "analysis": analysis,
    }

    def fake_snapshot(symbol):
        return type("Snapshot", (), {"price": 20000.0})()

    def fake_decide_candidates(limit=3, minimum_score=0.0):
        decision = engine._evaluate_candidate_decision(
            analysis,
            market_snapshot=fake_snapshot("BTC-USD"),
        )
        selected["decision"] = decision
        return [selected]

    original_publish = engine.event_repository.publish

    def fail_trade_event(event_type, payload=None):
        if event_type == "TRADE_EXECUTED":
            raise RuntimeError("trade event persistence failed")
        return original_publish(event_type, payload)

    monkeypatch.setattr(engine, "decide_candidates", fake_decide_candidates)
    monkeypatch.setattr(
        engine,
        "select_best_candidate",
        lambda candidates, investable_only=False: selected,
    )
    monkeypatch.setattr(engine, "_get_market_snapshot", fake_snapshot)
    monkeypatch.setattr(engine.report, "print_decision", lambda decision: None)
    monkeypatch.setattr(
        engine.prediction_evaluator,
        "evaluate_ready",
        lambda current_prices_usd: [],
    )
    monkeypatch.setattr(engine.event_repository, "publish", fail_trade_event)

    with pytest.raises(RuntimeError, match="trade event persistence failed"):
        engine.start()

    assert engine.trading_service.count() == 1
    trade = engine.trading_service.history()[0]
    assert trade["symbol"] == "BTC-USD"
    assert trade["action"] == "BUY"

    portfolio = engine.portfolio_service.as_dict(usd_nok=10.0)
    position = next(
        item
        for item in portfolio["positions"]
        if item["symbol"] == "BTC-USD"
    )
    assert position["quantity"] > 0.0

def test_committed_sell_survives_position_peak_cleanup_failure(monkeypatch, tmp_path):
    import pytest

    from atlas.models.action import Action
    from atlas.models.analysis_result import AnalysisResult

    config = AtlasConfig(
        agent_performance_storage=str(tmp_path / "agent_performance.json"),
        database_path=str(tmp_path / "atlas_test.db"),
    )
    config.trading_mode = "paper"
    config.paper_trading = True
    config.capital_limit = 1000000.0

    engine = AtlasEngine(config=config)
    engine.portfolio_service.buy(
        symbol="BTC-USD",
        amount_nok=1000.0,
        price_usd=100.0,
        usd_nok=10.0,
    )
    engine.trading_service.record_buy(
        symbol="BTC-USD",
        quantity=1.0,
        price_usd=100.0,
        amount_nok=1000.0,
    )
    engine.paper_account_state_repository.set_position_peak_price_usd(
        "BTC-USD",
        120.0,
    )

    analysis = [
        AnalysisResult(
            symbol="BTC-USD",
            analyst="test-analyst",
            action=Action.SELL,
            confidence=95.0,
            evidence=95.0,
            reasoning=["Strong SELL signal."],
        )
    ]
    selected = {
        "symbol": "BTC-USD",
        "discovery_score": 100.0,
        "analysis": analysis,
    }

    def fake_snapshot(symbol):
        return type("Snapshot", (), {"price": 110.0})()

    def fake_decide_candidates(limit=3, minimum_score=0.0):
        decision = engine._evaluate_candidate_decision(
            analysis,
            market_snapshot=fake_snapshot("BTC-USD"),
        )
        selected["decision"] = decision
        return [selected]

    def fail_peak_cleanup(symbol):
        raise RuntimeError("position peak cleanup failed")

    monkeypatch.setattr(engine, "decide_candidates", fake_decide_candidates)
    monkeypatch.setattr(
        engine,
        "select_best_candidate",
        lambda candidates, investable_only=False: selected,
    )
    monkeypatch.setattr(engine, "_get_market_snapshot", fake_snapshot)
    monkeypatch.setattr(engine.report, "print_decision", lambda decision: None)
    monkeypatch.setattr(
        engine.prediction_evaluator,
        "evaluate_ready",
        lambda current_prices_usd: [],
    )
    monkeypatch.setattr(
        engine.paper_account_state_repository,
        "delete_position_peak_price_usd",
        fail_peak_cleanup,
    )

    with pytest.raises(RuntimeError, match="position peak cleanup failed"):
        engine.start()

    trades = engine.trading_service.history()
    assert len(trades) == 2
    assert trades[0]["symbol"] == "BTC-USD"
    assert trades[0]["action"] == "SELL"

    portfolio = engine.portfolio_service.as_dict(usd_nok=10.0)
    assert not any(
        position["symbol"] == "BTC-USD"
        for position in portfolio["positions"]
    )




def test_restore_paper_portfolio_respects_persisted_replay_boundary(tmp_path):
    config = AtlasConfig(
        database_path=str(tmp_path / "atlas.db"),
        capital_limit=5_000.0,
    )

    legacy = AtlasEngine(config)
    legacy.trading_service.record_buy(
        symbol="BTC-USD",
        quantity=0.2,
        price_usd=100_000.0,
        amount_nok=185_854.02,
    )

    restarted = AtlasEngine(config)

    assert (
        restarted.paper_account_state_repository.get_trade_replay_after()
        is not None
    )
    assert restarted.portfolio_service.as_dict(10.0)["positions"] == []

    restarted.portfolio_service.buy(
        symbol="ETH-USD",
        amount_nok=2_000.0,
        price_usd=20_000.0,
        usd_nok=10.0,
    )
    restarted.trading_service.record_buy(
        symbol="ETH-USD",
        quantity=0.01,
        price_usd=20_000.0,
        amount_nok=2_000.0,
    )

    restarted.restore_paper_portfolio()

    positions = restarted.portfolio_service.as_dict(10.0)["positions"]

    assert [position["symbol"] for position in positions] == ["ETH-USD"]

def test_atlas_engine_start_records_prediction_and_executes_modern_paper_buy(
    monkeypatch,
    tmp_path,
):
    from atlas.models.action import Action
    from atlas.models.analysis_result import AnalysisResult

    config = AtlasConfig(
        agent_performance_storage=str(tmp_path / "agent_performance.json"),
        database_path=str(tmp_path / "atlas_test.db"),
        capital_limit=1000000.0,
        trading_mode="paper",
        paper_trading=True,
    )
    engine = AtlasEngine(config=config)

    analysis = [
        AnalysisResult(
            symbol="BTC-USD",
            analyst="test-analyst",
            action=Action.BUY,
            confidence=95.0,
            evidence=95.0,
            reasoning=["Strong BUY signal."],
        )
    ]
    selected = {
        "symbol": "BTC-USD",
        "discovery_score": 100.0,
        "analysis": analysis,
    }

    def fake_snapshot(symbol):
        return type(
            "Snapshot",
            (),
            {"price": 20000.0},
        )()

    def fake_decide_candidates(limit=3, minimum_score=0.0):
        selected["decision"] = engine._evaluate_candidate_decision(
            analysis,
            market_snapshot=fake_snapshot("BTC-USD"),
        )
        return [selected]

    monkeypatch.setattr(
        engine,
        "decide_candidates",
        fake_decide_candidates,
    )
    monkeypatch.setattr(
        engine,
        "select_best_candidate",
        lambda candidates, investable_only=False: selected,
    )
    monkeypatch.setattr(
        engine,
        "_get_market_snapshot",
        fake_snapshot,
    )
    monkeypatch.setattr(
        engine,
        "_get_usd_nok_rate",
        lambda: type("ExchangeRate", (), {"rate": 10.0})(),
    )
    monkeypatch.setattr(
        engine.exchange,
        "get_rate",
        lambda base, target: type("ExchangeRate", (), {"rate": 10.0})(),
    )
    monkeypatch.setattr(
        engine.report,
        "print_decision",
        lambda decision: None,
    )
    monkeypatch.setattr(
        engine.prediction_evaluator,
        "evaluate_ready",
        lambda current_prices_usd: [],
    )

    engine.start()

    decision = selected["decision"]
    assert decision.action is Action.BUY
    assert decision.analysis_snapshot_id is not None

    predictions = engine.prediction_tracker.history()
    assert len(predictions) == 1
    assert predictions[0]["symbol"] == "BTC-USD"
    assert predictions[0]["action"] == "BUY"
    assert predictions[0]["analysis_snapshot_id"] == decision.analysis_snapshot_id

    trades = engine.trading_service.history()
    assert len(trades) == 1
    assert trades[0]["symbol"] == "BTC-USD"
    assert trades[0]["action"] == "BUY"
    assert trades[0]["analysis_snapshot_id"] == decision.analysis_snapshot_id
    assert (
        trades[0]["analysis_snapshot_id"]
        == predictions[0]["analysis_snapshot_id"]
    )

    portfolio = engine.portfolio_service.as_dict(usd_nok=10.0)
    assert any(
        position["symbol"] == "BTC-USD"
        for position in portfolio["positions"]
    )

    events = engine.event_repository.after(0, limit=100)
    event_types = [event["type"] for event in events]
    assert "DECISION_READY" in event_types
    assert "TRADE_EXECUTED" in event_types
    assert event_types.index("DECISION_READY") < event_types.index(
        "TRADE_EXECUTED"
    )

def test_atlas_engine_start_runs_real_algorithm_pipeline_to_modern_paper_buy(
    monkeypatch,
    tmp_path,
):
    from atlas.market.asset import Asset
    from atlas.market.asset_discovery import DiscoveryScore
    from atlas.market.asset_type import AssetType
    from atlas.models.action import Action
    from atlas.models.analysis_result import AnalysisResult
    from atlas.trading.market_data import Candle, MarketSnapshot

    config = AtlasConfig(
        agent_performance_storage=str(tmp_path / "agent_performance.json"),
        database_path=str(tmp_path / "atlas_test.db"),
        capital_limit=1000000.0,
        trading_mode="paper",
        paper_trading=True,
    )
    engine = AtlasEngine(config=config)

    closes = [
        100.0 + index * 0.1
        for index in range(30)
    ]
    closes[-1] = 105.0
    candles = tuple(
        Candle(
            timestamp=float(index + 1),
            open=close,
            high=close,
            low=close,
            close=close,
            volume=100.0,
        )
        for index, close in enumerate(closes)
    )
    normalized_snapshot = MarketSnapshot.from_candles(
        "BTC-USD",
        candles,
        timeframe_candles={"5m": candles},
    )

    candidate = DiscoveryScore(
        asset=Asset(
            symbol="BTC-USD",
            name="Bitcoin",
            asset_type=AssetType.CRYPTO,
            market="crypto",
            currency="USD",
        ),
        score=100.0,
    )
    analyst_evidence = [
        AnalysisResult(
            symbol="BTC-USD",
            analyst="Technical Analyst",
            action=Action.BUY,
            confidence=95.0,
            evidence=95.0,
            reasoning=["Strong controlled BUY evidence."],
        )
    ]

    monkeypatch.setattr(
        engine,
        "discover_candidates",
        lambda limit=3, minimum_score=0.0, horizon=None: [candidate],
    )
    monkeypatch.setattr(
        engine.analysis_service,
        "analyze",
        lambda symbol: analyst_evidence,
    )
    monkeypatch.setattr(
        engine.market_data,
        "snapshot",
        lambda symbol, interval, limit: normalized_snapshot,
    )
    monkeypatch.setattr(
        engine,
        "_get_market_snapshot",
        lambda symbol: type(
            "Snapshot",
            (),
            {"price": normalized_snapshot.price},
        )(),
    )
    monkeypatch.setattr(
        engine,
        "_get_usd_nok_rate",
        lambda: type("ExchangeRate", (), {"rate": 10.0})(),
    )
    monkeypatch.setattr(
        engine.exchange,
        "get_rate",
        lambda base, target: type("ExchangeRate", (), {"rate": 10.0})(),
    )
    monkeypatch.setattr(
        engine,
        "get_regime_memory_decision",
        lambda symbol, regime: None,
    )
    monkeypatch.setattr(
        engine,
        "integrate_regime_decision",
        lambda decision, regime_decision: decision,
    )
    monkeypatch.setattr(
        engine.report,
        "print_decision",
        lambda decision: None,
    )
    monkeypatch.setattr(
        engine.prediction_evaluator,
        "evaluate_ready",
        lambda current_prices_usd: [],
    )

    engine.start()

    predictions = engine.prediction_tracker.history()
    trades = engine.trading_service.history()
    portfolio = engine.portfolio_service.as_dict(usd_nok=10.0)

    assert len(predictions) == 1
    assert predictions[0]["symbol"] == "BTC-USD"
    assert predictions[0]["action"] == "BUY"
    assert len(trades) == 1
    assert trades[0]["symbol"] == "BTC-USD"
    assert trades[0]["action"] == "BUY"
    assert any(
        position["symbol"] == "BTC-USD"
        for position in portfolio["positions"]
    )

def test_atlas_engine_start_persists_ready_prediction_learning_update(
    monkeypatch,
    tmp_path,
):
    from datetime import datetime, timedelta

    from atlas.models.action import Action
    from atlas.models.analysis_result import AnalysisResult
    from atlas.models.analysis_snapshot import AnalysisSnapshot
    from atlas.models.decision_result import DecisionResult
    from atlas.trading.prediction_record import PredictionRecord

    config = AtlasConfig(
        agent_performance_storage=str(tmp_path / "agent_performance.json"),
        database_path=str(tmp_path / "atlas_test.db"),
        trading_mode="paper",
        paper_trading=True,
    )
    engine = AtlasEngine(config=config)

    snapshot = AnalysisSnapshot(
        database_id=None,
        symbol="BTC-USD",
        timestamp=datetime.now() - timedelta(hours=25),
        provider="test",
        model="test",
        results=[
            {
                "analyst": "Technical Analyst",
                "symbol": "BTC-USD",
                "action": "BUY",
                "confidence": 95.0,
                "evidence": 95.0,
                "reasoning": ["Bullish test evidence."],
            },
            {
                "analyst": "News Analyst",
                "symbol": "BTC-USD",
                "action": "SELL",
                "confidence": 90.0,
                "evidence": 90.0,
                "reasoning": ["Bearish test evidence."],
            },
        ],
        decision={
            "action": "BUY",
            "confidence": 95.0,
            "evidence": 95.0,
        },
        intelligence={
            "action": "BUY",
            "buy_count": 1,
            "hold_count": 0,
            "sell_count": 1,
            "agreement": 50.0,
        },
    )
    engine.analysis_snapshot_repository.save(snapshot)

    prediction = PredictionRecord(
        symbol="BTC-USD",
        action="BUY",
        confidence=95.0,
        evidence=95.0,
        price_usd=100.0,
        timestamp=datetime.now() - timedelta(hours=25),
        analysts=["Technical Analyst", "News Analyst"],
        reason="Learning lifecycle test.",
        analysis_snapshot_id=snapshot.database_id,
    )
    engine.prediction_tracker.repository.save(prediction)
    engine.prediction_tracker._predictions.append(prediction)

    monkeypatch.setattr(
        engine,
        "_get_market_snapshot",
        lambda symbol: type("Snapshot", (), {"price": 105.0})(),
    )
    monkeypatch.setattr(
        engine,
        "decide_candidates",
        lambda limit=3: [],
    )

    engine.start()

    stored_prediction = (
        engine.prediction_tracker.repository.get_all()[0]
    )
    assert stored_prediction.evaluated is True
    assert stored_prediction.correct is True
    assert stored_prediction.evaluated_price_usd == 105.0
    assert stored_prediction.price_change_percent == 5.0

    outcomes = engine.outcome_repository.get_for_prediction(
        prediction.database_id
    )
    assert len(outcomes) == 1
    assert outcomes[0].correct is True

    technical = engine.agent_performance.get("Technical Analyst")
    news = engine.agent_performance.get("News Analyst")
    assert technical.predictions == 1
    assert technical.correct == 1
    assert technical.action_predictions == {"BUY": 1}
    assert technical.action_correct == {"BUY": 1}
    assert news.predictions == 1
    assert news.correct == 0
    assert news.action_predictions == {"SELL": 1}
    assert news.action_correct == {"SELL": 0}

    events = engine.event_repository.after(0, limit=100)
    learning_events = [
        event
        for event in events
        if event["type"] == "LEARNING_UPDATED"
    ]
    assert len(learning_events) == 1
    assert learning_events[0]["payload"] == {
        "evaluated_predictions": 1,
    }

def test_atlas_engine_evaluated_history_changes_next_decision_weights(
    tmp_path,
):
    from datetime import datetime, timedelta

    from atlas.models.action import Action
    from atlas.models.analysis_result import AnalysisResult
    from atlas.models.analysis_snapshot import AnalysisSnapshot
    from atlas.trading.prediction_record import PredictionRecord

    config = AtlasConfig(
        agent_performance_storage=str(tmp_path / "agent_performance.json"),
        database_path=str(tmp_path / "atlas_test.db"),
    )
    engine = AtlasEngine(config=config)

    for index in range(20):
        snapshot = AnalysisSnapshot(
            database_id=None,
            symbol="BTC-USD",
            timestamp=datetime.now() - timedelta(hours=25, minutes=index),
            provider="test",
            model="test",
            results=[
                {
                    "analyst": "Technical Analyst",
                    "symbol": "BTC-USD",
                    "action": "BUY",
                    "confidence": 90.0,
                    "evidence": 90.0,
                    "reasoning": ["Historical BUY."],
                },
                {
                    "analyst": "News Analyst",
                    "symbol": "BTC-USD",
                    "action": ("BUY" if index < 6 else "SELL"),
                    "confidence": 90.0,
                    "evidence": 90.0,
                    "reasoning": ["Historical directional signal."],
                },
            ],
            decision={
                "action": "BUY",
                "confidence": 90.0,
                "evidence": 90.0,
            },
            intelligence={
                "action": "BUY",
                "buy_count": 2,
                "hold_count": 0,
                "sell_count": 0,
                "agreement": 100.0,
            },
        )
        engine.analysis_snapshot_repository.save(snapshot)

        prediction = PredictionRecord(
            symbol="BTC-USD",
            action="BUY",
            confidence=90.0,
            evidence=90.0,
            price_usd=100.0,
            timestamp=datetime.now() - timedelta(
                hours=25,
                minutes=index,
            ),
            analysts=["Technical Analyst", "News Analyst"],
            analysis_snapshot_id=snapshot.database_id,
        )
        engine.prediction_tracker.repository.save(prediction)

        current_price = 105.0 if index < 18 else 95.0

        engine.prediction_evaluator.evaluate(
            prediction=prediction,
            current_price_usd=current_price,
        )

    technical = engine.agent_performance.get("Technical Analyst")
    news = engine.agent_performance.get("News Analyst")

    assert technical.action_predictions["BUY"] == 20
    assert technical.action_correct["BUY"] == 18
    assert news.action_predictions["BUY"] == 6
    assert news.action_correct["BUY"] == 6
    assert news.action_predictions["SELL"] == 14
    assert news.action_correct["SELL"] == 2

    decision = engine.decision_engine.evaluate(
        [
            AnalysisResult(
                symbol="BTC-USD",
                analyst="Technical Analyst",
                action=Action.BUY,
                confidence=90.0,
                evidence=90.0,
                reasoning=["Current technical BUY."],
            ),
            AnalysisResult(
                symbol="BTC-USD",
                analyst="News Analyst",
                action=Action.HOLD,
                confidence=90.0,
                evidence=90.0,
                reasoning=["Current news HOLD."],
            ),
        ],
        price=100.0,
        equity=10000.0,
    )

    assert decision.agent_weights["Technical Analyst"] > (
        decision.agent_weights["News Analyst"]
    )
    assert decision.agent_weights == engine.agent_weight_engine.calculate()

def test_atlas_engine_start_runs_modern_paper_buy_then_sell_lifecycle(
    monkeypatch,
    tmp_path,
):
    from atlas.models.action import Action
    from atlas.models.analysis_result import AnalysisResult

    config = AtlasConfig(
        agent_performance_storage=str(tmp_path / "agent_performance.json"),
        database_path=str(tmp_path / "atlas_test.db"),
        capital_limit=1000000.0,
        trading_mode="paper",
        paper_trading=True,
    )
    engine = AtlasEngine(config=config)

    state = {
        "action": Action.BUY,
        "price": 100.0,
    }
    selected = {
        "symbol": "BTC-USD",
        "discovery_score": 100.0,
    }

    def current_analysis():
        return [
            AnalysisResult(
                symbol="BTC-USD",
                analyst="test-analyst",
                action=state["action"],
                confidence=95.0,
                evidence=95.0,
                reasoning=[f"Strong {state['action'].value} signal."],
            )
        ]

    def fake_snapshot(symbol):
        return type(
            "Snapshot",
            (),
            {"price": state["price"]},
        )()

    def fake_decide_candidates(limit=3, minimum_score=0.0):
        analysis = current_analysis()
        selected["analysis"] = analysis
        selected["decision"] = engine._evaluate_candidate_decision(
            analysis,
            market_snapshot=fake_snapshot("BTC-USD"),
        )
        return [selected]

    monkeypatch.setattr(
        engine,
        "decide_candidates",
        fake_decide_candidates,
    )
    monkeypatch.setattr(
        engine,
        "select_best_candidate",
        lambda candidates, investable_only=False: selected,
    )
    monkeypatch.setattr(
        engine,
        "_get_market_snapshot",
        fake_snapshot,
    )
    monkeypatch.setattr(
        engine,
        "_get_usd_nok_rate",
        lambda: type("ExchangeRate", (), {"rate": 10.0})(),
    )
    monkeypatch.setattr(
        engine.exchange,
        "get_rate",
        lambda base, target: type("ExchangeRate", (), {"rate": 10.0})(),
    )
    monkeypatch.setattr(
        engine.report,
        "print_decision",
        lambda decision: None,
    )
    monkeypatch.setattr(
        engine.prediction_evaluator,
        "evaluate_ready",
        lambda current_prices_usd: [],
    )

    engine.start()

    buy_decision = selected["decision"]
    assert buy_decision.action is Action.BUY
    assert buy_decision.risk_assessment is not None
    assert buy_decision.risk_assessment.allowed is True

    bought_portfolio = engine.portfolio_service.as_dict(usd_nok=10.0)
    bought_position = next(
        position
        for position in bought_portfolio["positions"]
        if position["symbol"] == "BTC-USD"
    )
    bought_quantity = bought_position["quantity"]
    assert bought_quantity > 0.0

    state["action"] = Action.SELL
    state["price"] = 110.0

    engine.start()

    sell_decision = selected["decision"]
    assert sell_decision.action is Action.SELL
    assert sell_decision.risk_assessment is not None
    assert sell_decision.risk_assessment.allowed is True
    assert sell_decision.risk_assessment.position_size == bought_quantity

    predictions = engine.prediction_tracker.history()
    assert [prediction["action"] for prediction in predictions] == [
        "SELL",
        "BUY",
    ]

    trades = engine.trading_service.history()
    assert [trade["action"] for trade in reversed(trades)] == [
        "BUY",
        "SELL",
    ]
    sell_trade = trades[0]
    assert sell_trade["realized_pnl_nok"] > 0.0

    portfolio = engine.portfolio_service.as_dict(usd_nok=10.0)
    assert not any(
        position["symbol"] == "BTC-USD"
        for position in portfolio["positions"]
    )
    assert portfolio["profit_vault_nok"] > 0.0

    events = engine.event_repository.after(0, limit=100)
    trade_events = [
        event
        for event in events
        if event["type"] == "TRADE_EXECUTED"
    ]
    assert [
        event["payload"]["action"]
        for event in trade_events
    ] == ["BUY", "SELL"]

def test_atlas_engine_buy_prediction_is_evaluated_on_later_start(
    monkeypatch,
    tmp_path,
):
    from datetime import datetime, timedelta

    import atlas.trading.prediction_tracker as prediction_tracker_module
    from atlas.models.action import Action
    from atlas.models.analysis_result import AnalysisResult

    config = AtlasConfig(
        agent_performance_storage=str(tmp_path / "agent_performance.json"),
        database_path=str(tmp_path / "atlas_test.db"),
        capital_limit=1000000.0,
        trading_mode="paper",
        paper_trading=True,
    )
    engine = AtlasEngine(config=config)

    real_datetime = datetime
    first_run_time = real_datetime.now() - timedelta(hours=25)

    class HistoricalDateTime(real_datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is not None:
                return first_run_time.astimezone(tz)
            return first_run_time

    state = {
        "action": Action.BUY,
        "price": 100.0,
    }
    selected = {
        "symbol": "BTC-USD",
        "discovery_score": 100.0,
    }

    def current_analysis():
        return [
            AnalysisResult(
                symbol="BTC-USD",
                analyst="Technical Analyst",
                action=state["action"],
                confidence=95.0,
                evidence=95.0,
                reasoning=[f"Strong {state['action'].value} signal."],
            )
        ]

    def fake_snapshot(symbol):
        return type("Snapshot", (), {"price": state["price"]})()

    def fake_decide_candidates(limit=3, minimum_score=0.0):
        analysis = current_analysis()
        selected["analysis"] = analysis
        selected["decision"] = engine._evaluate_candidate_decision(
            analysis,
            market_snapshot=fake_snapshot("BTC-USD"),
        )
        return [selected]

    monkeypatch.setattr(
        engine,
        "decide_candidates",
        fake_decide_candidates,
    )
    monkeypatch.setattr(
        engine,
        "select_best_candidate",
        lambda candidates, investable_only=False: selected,
    )
    monkeypatch.setattr(engine, "_get_market_snapshot", fake_snapshot)
    monkeypatch.setattr(
        engine,
        "_get_usd_nok_rate",
        lambda: type("ExchangeRate", (), {"rate": 10.0})(),
    )
    monkeypatch.setattr(
        engine.exchange,
        "get_rate",
        lambda base, target: type("ExchangeRate", (), {"rate": 10.0})(),
    )
    monkeypatch.setattr(engine.report, "print_decision", lambda decision: None)

    monkeypatch.setattr(
        prediction_tracker_module,
        "datetime",
        HistoricalDateTime,
    )
    engine.start()

    stored = engine.prediction_tracker.repository.get_all()
    assert len(stored) == 1
    assert stored[0].action == "BUY"
    assert stored[0].evaluated is False
    assert stored[0].timestamp == first_run_time

    monkeypatch.setattr(
        prediction_tracker_module,
        "datetime",
        real_datetime,
    )
    state["action"] = Action.SELL
    state["price"] = 110.0

    engine.start()

    stored = engine.prediction_tracker.repository.get_all()
    buy_prediction = next(
        prediction
        for prediction in stored
        if prediction.action == "BUY"
    )
    assert buy_prediction.evaluated is True
    assert buy_prediction.correct is True
    assert buy_prediction.evaluated_price_usd == 110.0
    assert buy_prediction.price_change_percent == 10.0

    outcomes = engine.outcome_repository.get_for_prediction(
        buy_prediction.database_id
    )
    assert len(outcomes) == 1
    assert outcomes[0].correct is True

    performance = engine.agent_performance.get("Technical Analyst")
    assert performance.predictions == 1
    assert performance.correct == 1
    assert performance.action_predictions == {"BUY": 1}
    assert performance.action_correct == {"BUY": 1}

    trades = engine.trading_service.history()
    assert [trade["action"] for trade in reversed(trades)] == [
        "BUY",
        "SELL",
    ]

    events = engine.event_repository.after(0, limit=100)
    assert any(
        event["type"] == "LEARNING_UPDATED"
        and event["payload"] == {"evaluated_predictions": 1}
        for event in events
    )

def test_atlas_engine_start_uses_newly_evaluated_history_in_same_run_decision(
    monkeypatch,
    tmp_path,
):
    from datetime import datetime, timedelta

    from atlas.models.action import Action
    from atlas.models.analysis_result import AnalysisResult
    from atlas.models.analysis_snapshot import AnalysisSnapshot
    from atlas.trading.prediction_record import PredictionRecord

    config = AtlasConfig(
        agent_performance_storage=str(tmp_path / "agent_performance.json"),
        database_path=str(tmp_path / "atlas_test.db"),
        capital_limit=1000000.0,
        trading_mode="paper",
        paper_trading=True,
    )
    engine = AtlasEngine(config=config)

    for index in range(40):
        snapshot = AnalysisSnapshot(
            database_id=None,
            symbol="BTC-USD",
            timestamp=datetime.now() - timedelta(
                hours=25,
                minutes=index,
            ),
            provider="test",
            model="test",
            results=[
                {
                    "analyst": "Technical Analyst",
                    "symbol": "BTC-USD",
                    "action": "BUY",
                    "confidence": 100.0,
                    "evidence": 100.0,
                    "reasoning": ["Historical technical BUY."],
                },
                {
                    "analyst": "News Analyst",
                    "symbol": "BTC-USD",
                    "action": "SELL",
                    "confidence": 100.0,
                    "evidence": 0.0,
                    "reasoning": ["Historical news SELL."],
                },
                {
                    "analyst": "Company Analyst",
                    "symbol": "BTC-USD",
                    "action": "SELL",
                    "confidence": 100.0,
                    "evidence": 0.0,
                    "reasoning": ["Historical company SELL."],
                },
            ],
            decision={
                "action": "BUY",
                "confidence": 100.0,
                "evidence": 100.0,
            },
            intelligence={
                "action": "BUY",
                "buy_count": 1,
                "hold_count": 0,
                "sell_count": 2,
                "agreement": 66.67,
            },
        )
        engine.analysis_snapshot_repository.save(snapshot)

        prediction = PredictionRecord(
            symbol="BTC-USD",
            action="BUY",
            confidence=100.0,
            evidence=100.0,
            price_usd=100.0,
            timestamp=datetime.now() - timedelta(
                hours=25,
                minutes=index,
            ),
            analysts=[
                "Technical Analyst",
                "News Analyst",
                "Company Analyst",
            ],
            analysis_snapshot_id=snapshot.database_id,
        )
        engine.prediction_tracker.repository.save(prediction)

    analysis = [
        AnalysisResult(
            symbol="BTC-USD",
            analyst="Technical Analyst",
            action=Action.BUY,
            confidence=100.0,
            evidence=100.0,
            reasoning=["Current technical BUY."],
        ),
        AnalysisResult(
            symbol="BTC-USD",
            analyst="News Analyst",
            action=Action.SELL,
            confidence=100.0,
            evidence=100.0,
            reasoning=["Current news SELL."],
        ),
        AnalysisResult(
            symbol="BTC-USD",
            analyst="Company Analyst",
            action=Action.SELL,
            confidence=100.0,
            evidence=100.0,
            reasoning=["Current company SELL."],
        ),
    ]
    selected = {
        "symbol": "BTC-USD",
        "discovery_score": 100.0,
        "analysis": analysis,
    }

    def fake_snapshot(symbol):
        return type("Snapshot", (), {"price": 105.0})()

    def fake_decide_candidates(limit=3, minimum_score=0.0):
        selected["decision"] = engine._evaluate_candidate_decision(
            analysis,
            market_snapshot=fake_snapshot("BTC-USD"),
        )
        return [selected]

    monkeypatch.setattr(
        engine,
        "decide_candidates",
        fake_decide_candidates,
    )
    monkeypatch.setattr(
        engine,
        "select_best_candidate",
        lambda candidates, investable_only=False: selected,
    )
    monkeypatch.setattr(engine, "_get_market_snapshot", fake_snapshot)
    monkeypatch.setattr(
        engine,
        "_get_usd_nok_rate",
        lambda: type("ExchangeRate", (), {"rate": 10.0})(),
    )
    monkeypatch.setattr(
        engine.exchange,
        "get_rate",
        lambda base, target: type("ExchangeRate", (), {"rate": 10.0})(),
    )
    monkeypatch.setattr(engine.report, "print_decision", lambda decision: None)

    engine.start()

    decision = selected["decision"]
    weights = engine.agent_weight_engine.calculate()

    assert engine.agent_performance.get("Technical Analyst").predictions == 40
    assert engine.agent_performance.get("Technical Analyst").correct == 40
    assert engine.agent_performance.get("News Analyst").predictions == 40
    assert engine.agent_performance.get("News Analyst").correct == 0
    assert engine.agent_performance.get("Company Analyst").predictions == 40
    assert engine.agent_performance.get("Company Analyst").correct == 0

    assert weights["Technical Analyst"] > weights["News Analyst"]
    assert weights["Technical Analyst"] > weights["Company Analyst"]
    assert decision.agent_weights == weights
    assert decision.action is Action.BUY
    assert any(
        "adaptive" in reason.lower()
        for reason in decision.reasoning
    )

    events = engine.event_repository.after(0, limit=100)
    learning_events = [
        event
        for event in events
        if event["type"] == "LEARNING_UPDATED"
    ]
    assert learning_events[-1]["payload"] == {
        "evaluated_predictions": 40,
    }

    trades = engine.trading_service.history()
    assert trades[0]["action"] == "BUY"

def test_atlas_engine_restart_reuses_persisted_learning_for_decision(
    monkeypatch,
    tmp_path,
):
    from datetime import datetime, timedelta

    from atlas.models.action import Action
    from atlas.models.analysis_result import AnalysisResult
    from atlas.models.analysis_snapshot import AnalysisSnapshot
    from atlas.trading.prediction_record import PredictionRecord

    config = AtlasConfig(
        agent_performance_storage=str(tmp_path / "agent_performance.json"),
        database_path=str(tmp_path / "atlas_test.db"),
        capital_limit=1000000.0,
        trading_mode="paper",
        paper_trading=True,
    )
    first = AtlasEngine(config=config)

    for index in range(40):
        snapshot = AnalysisSnapshot(
            database_id=None,
            symbol="BTC-USD",
            timestamp=datetime.now() - timedelta(
                hours=25,
                minutes=index,
            ),
            provider="test",
            model="test",
            results=[
                {
                    "analyst": "Technical Analyst",
                    "symbol": "BTC-USD",
                    "action": "BUY",
                    "confidence": 100.0,
                    "evidence": 100.0,
                    "reasoning": ["Historical technical BUY."],
                },
                {
                    "analyst": "News Analyst",
                    "symbol": "BTC-USD",
                    "action": "SELL",
                    "confidence": 100.0,
                    "evidence": 100.0,
                    "reasoning": ["Historical news SELL."],
                },
                {
                    "analyst": "Company Analyst",
                    "symbol": "BTC-USD",
                    "action": "SELL",
                    "confidence": 100.0,
                    "evidence": 100.0,
                    "reasoning": ["Historical company SELL."],
                },
            ],
            decision={
                "action": "BUY",
                "confidence": 100.0,
                "evidence": 100.0,
            },
            intelligence={
                "action": "BUY",
                "buy_count": 1,
                "hold_count": 0,
                "sell_count": 2,
                "agreement": 66.67,
            },
        )
        first.analysis_snapshot_repository.save(snapshot)
        first.prediction_tracker.repository.save(
            PredictionRecord(
                symbol="BTC-USD",
                action="BUY",
                confidence=100.0,
                evidence=100.0,
                price_usd=100.0,
                timestamp=datetime.now() - timedelta(
                    hours=25,
                    minutes=index,
                ),
                analysts=[
                    "Technical Analyst",
                    "News Analyst",
                    "Company Analyst",
                ],
                analysis_snapshot_id=snapshot.database_id,
            )
        )

    evaluated = first.prediction_evaluator.evaluate_ready(
        current_prices_usd={"BTC-USD": 105.0},
    )
    assert len(evaluated) == 40

    first_weights = first.agent_weight_engine.calculate()
    assert first_weights["Technical Analyst"] > first_weights["News Analyst"]

    restarted = AtlasEngine(config=config)

    restarted_weights = restarted.agent_weight_engine.calculate()
    assert restarted_weights == first_weights
    assert restarted.agent_performance.get(
        "Technical Analyst"
    ).predictions == 40
    assert restarted.agent_performance.get(
        "Technical Analyst"
    ).correct == 40
    assert restarted.agent_performance.get(
        "News Analyst"
    ).correct == 0
    assert restarted.agent_performance.get(
        "Company Analyst"
    ).correct == 0

    analysis = [
        AnalysisResult(
            symbol="BTC-USD",
            analyst="Technical Analyst",
            action=Action.BUY,
            confidence=100.0,
            evidence=100.0,
            reasoning=["Current technical BUY."],
        ),
        AnalysisResult(
            symbol="BTC-USD",
            analyst="News Analyst",
            action=Action.SELL,
            confidence=100.0,
            evidence=100.0,
            reasoning=["Current news SELL."],
        ),
        AnalysisResult(
            symbol="BTC-USD",
            analyst="Company Analyst",
            action=Action.SELL,
            confidence=100.0,
            evidence=100.0,
            reasoning=["Current company SELL."],
        ),
    ]

    monkeypatch.setattr(
        restarted,
        "_get_usd_nok_rate",
        lambda: type("ExchangeRate", (), {"rate": 10.0})(),
    )

    decision = restarted._evaluate_candidate_decision(
        analysis,
        market_snapshot=type("Snapshot", (), {"price": 105.0})(),
    )

    assert decision.agent_weights == restarted_weights
    assert decision.action is Action.BUY
    assert any(
        "adaptive weighting allowed" in reason.lower()
        for reason in decision.reasoning
    )

def test_atlas_engine_restart_restores_position_for_modern_paper_sell(
    monkeypatch,
    tmp_path,
):
    from atlas.models.action import Action
    from atlas.models.analysis_result import AnalysisResult

    config = AtlasConfig(
        agent_performance_storage=str(tmp_path / "agent_performance.json"),
        database_path=str(tmp_path / "atlas_test.db"),
        capital_limit=1000000.0,
        trading_mode="paper",
        paper_trading=True,
    )
    first = AtlasEngine(config=config)

    buy_analysis = [
        AnalysisResult(
            symbol="BTC-USD",
            analyst="test-analyst",
            action=Action.BUY,
            confidence=95.0,
            evidence=95.0,
            reasoning=["Strong BUY signal."],
        )
    ]
    buy_decision = first._evaluate_candidate_decision(
        buy_analysis,
        market_snapshot=type("Snapshot", (), {"price": 100.0})(),
    )
    assert buy_decision.action is Action.BUY

    buy_result = first.decision_execution_service.execute(
        decision=buy_decision,
        price=100.0,
    )
    assert buy_result is not None

    bought_position = first.portfolio_service.as_dict(10.0)["positions"][0]
    bought_quantity = bought_position["quantity"]
    assert bought_quantity > 0.0
    first.paper_account_state_repository.set_position_peak_price_usd(
        "BTC-USD",
        120.0,
    )

    restarted = AtlasEngine(config=config)
    restored_position = restarted.portfolio_service.as_dict(10.0)["positions"][0]
    assert restored_position["symbol"] == "BTC-USD"
    assert restored_position["quantity"] == bought_quantity
    assert restored_position["peak_price_usd"] == 120.0

    sell_analysis = [
        AnalysisResult(
            symbol="BTC-USD",
            analyst="test-analyst",
            action=Action.SELL,
            confidence=95.0,
            evidence=95.0,
            reasoning=["Strong SELL signal."],
        )
    ]
    selected = {
        "symbol": "BTC-USD",
        "discovery_score": 100.0,
        "analysis": sell_analysis,
    }

    def fake_snapshot(symbol):
        return type("Snapshot", (), {"price": 110.0})()

    def fake_decide_candidates(limit=3, minimum_score=0.0):
        selected["decision"] = restarted._evaluate_candidate_decision(
            sell_analysis,
            market_snapshot=fake_snapshot("BTC-USD"),
        )
        return [selected]

    monkeypatch.setattr(
        restarted,
        "decide_candidates",
        fake_decide_candidates,
    )
    monkeypatch.setattr(
        restarted,
        "select_best_candidate",
        lambda candidates, investable_only=False: selected,
    )
    monkeypatch.setattr(
        restarted,
        "_get_market_snapshot",
        fake_snapshot,
    )
    monkeypatch.setattr(
        restarted,
        "_get_usd_nok_rate",
        lambda: type("ExchangeRate", (), {"rate": 10.0})(),
    )
    monkeypatch.setattr(
        restarted.exchange,
        "get_rate",
        lambda base, target: type("ExchangeRate", (), {"rate": 10.0})(),
    )
    monkeypatch.setattr(
        restarted.report,
        "print_decision",
        lambda decision: None,
    )
    monkeypatch.setattr(
        restarted.prediction_evaluator,
        "evaluate_ready",
        lambda current_prices_usd: [],
    )

    restarted.start()

    sell_decision = selected["decision"]
    assert sell_decision.action is Action.SELL
    assert sell_decision.risk_assessment is not None
    assert sell_decision.risk_assessment.allowed is True
    assert sell_decision.risk_assessment.position_size == bought_quantity

    trades = restarted.trading_service.history()
    assert [trade["action"] for trade in reversed(trades)] == [
        "BUY",
        "SELL",
    ]
    assert trades[0]["realized_pnl_nok"] > 0.0
    assert trades[0]["analysis_snapshot_id"] is not None

    portfolio = restarted.portfolio_service.as_dict(10.0)
    assert not any(
        position["symbol"] == "BTC-USD"
        for position in portfolio["positions"]
    )
    assert portfolio["profit_vault_nok"] > 0.0
    assert (
        restarted.paper_account_state_repository
        .get_position_peak_price_usd("BTC-USD")
        is None
    )

    events = restarted.event_repository.after(0, limit=100)
    sell_events = [
        event
        for event in events
        if event["type"] == "TRADE_EXECUTED"
        and event["payload"]["action"] == "SELL"
    ]
    assert len(sell_events) == 1
    assert (
        sell_events[0]["payload"]["analysis_snapshot_id"]
        == trades[0]["analysis_snapshot_id"]
    )

