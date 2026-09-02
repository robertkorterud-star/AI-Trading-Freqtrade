from atlas.models.action import Action
from atlas.models.decision_result import DecisionResult
from atlas.risk.risk_engine import RiskEngine
from atlas.services.portfolio_service import PortfolioService
from atlas.trading.paper_trading_engine import PaperTradingEngine
from atlas.trading.trading_cost_model import TradingCostModel
from atlas.trading.trading_service import TradingService


def _trader():
    portfolio = PortfolioService(5000)
    trading = TradingService()
    trader = PaperTradingEngine(
        portfolio=portfolio,
        risk=RiskEngine(),
        trading=trading,
        cost_model=TradingCostModel(),
    )
    return trader, trading


def test_paper_buy_is_blocked_when_expected_return_does_not_cover_costs():
    trader, trading = _trader()

    decision = DecisionResult(
        symbol="BTC-USD",
        action=Action.BUY,
        confidence=90.0,
        evidence=90.0,
        expected_return=0.0020,
    )

    result = trader.execute(
        decision=decision,
        price_usd=65000.0,
        usd_nok=9.50,
        amount_nok=1000.0,
    )

    assert result["executed"] is False
    assert result["action"] == "BUY"
    assert result["expected_return"] == 0.0020
    assert result["estimated_round_trip_cost"] == 0.0024
    assert result["net_expected_return"] == -0.0004
    assert len(trading.history()) == 0


def test_paper_buy_executes_when_expected_return_covers_costs():
    trader, trading = _trader()

    decision = DecisionResult(
        symbol="BTC-USD",
        action=Action.BUY,
        confidence=90.0,
        evidence=90.0,
        expected_return=0.0050,
    )

    result = trader.execute(
        decision=decision,
        price_usd=65000.0,
        usd_nok=9.50,
        amount_nok=1000.0,
    )

    assert result["executed"] is True
    assert result["action"] == "BUY"
    assert len(trading.history()) == 1
    assert trading.history()[0]["action"] == "BUY"


def test_paper_sell_is_not_blocked_by_expected_return_gate():
    trader, trading = _trader()

    buy = DecisionResult(
        symbol="BTC-USD",
        action=Action.BUY,
        confidence=90.0,
        evidence=90.0,
        expected_return=0.0050,
    )

    trader.execute(
        decision=buy,
        price_usd=65000.0,
        usd_nok=9.50,
        amount_nok=1000.0,
    )

    sell = DecisionResult(
        symbol="BTC-USD",
        action=Action.SELL,
        confidence=40.0,
        evidence=40.0,
        expected_return=0.0,
    )

    result = trader.execute(
        decision=sell,
        price_usd=65000.0,
        usd_nok=9.50,
    )

    assert result["executed"] is True
    assert result["action"] == "SELL"
    assert len(trading.history()) == 2
