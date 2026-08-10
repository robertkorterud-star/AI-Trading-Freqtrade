from atlas.models.action import Action
from atlas.models.decision_result import DecisionResult
from atlas.risk.risk_engine import RiskEngine
from atlas.services.portfolio_service import PortfolioService
from atlas.trading.paper_trading_engine import PaperTradingEngine
from atlas.trading.trading_service import TradingService


def test_paper_trading_engine_executes_buy():

    portfolio = PortfolioService(5000)
    risk = RiskEngine()
    trading = TradingService()

    trader = PaperTradingEngine(
        portfolio=portfolio,
        risk=risk,
        trading=trading,
    )

    decision = DecisionResult(
        symbol="BTC-USD",
        action=Action.BUY,
        confidence=89.5,
        evidence=86.5,
    )

    result = trader.execute(
        decision=decision,
        price_usd=65000,
        usd_nok=9.50,
        amount_nok=1000,
    )

    assert result["executed"] is True
    assert result["action"] == "BUY"
    assert result["symbol"] == "BTC-USD"

    assert len(trading.history()) == 1
    assert trading.history()[0]["action"] == "BUY"


def test_paper_trading_engine_executes_sell_and_records_profit():

    portfolio = PortfolioService(5000)
    risk = RiskEngine()
    trading = TradingService()

    trader = PaperTradingEngine(
        portfolio=portfolio,
        risk=risk,
        trading=trading,
    )

    buy = DecisionResult(
        symbol="BTC-USD",
        action=Action.BUY,
        confidence=89.5,
        evidence=86.5,
    )

    trader.execute(
        decision=buy,
        price_usd=65000,
        usd_nok=9.50,
        amount_nok=1000,
    )

    portfolio.update_prices({
        "BTC-USD": 70000
    })

    sell = DecisionResult(
        symbol="BTC-USD",
        action=Action.SELL,
        confidence=40.0,
        evidence=40.0,
    )

    result = trader.execute(
        decision=sell,
        price_usd=70000,
        usd_nok=9.50,
    )

    assert result["executed"] is True
    assert result["action"] == "SELL"
    assert result["realized_pnl_nok"] == 76.92

    history = trading.history()

    assert len(history) == 2
    assert history[0]["action"] == "SELL"
    assert history[0]["realized_pnl_nok"] == 76.92
    assert history[1]["action"] == "BUY"


def test_paper_trading_engine_rejects_buy_above_risk_limit():

    portfolio = PortfolioService(5000)
    risk = RiskEngine()
    trading = TradingService()

    trader = PaperTradingEngine(
        portfolio=portfolio,
        risk=risk,
        trading=trading,
    )

    decision = DecisionResult(
        symbol="BTC-USD",
        action=Action.BUY,
        confidence=89.5,
        evidence=86.5,
    )

    result = trader.execute(
        decision=decision,
        price_usd=65000,
        usd_nok=9.50,
        amount_nok=1200,
    )

    assert result["executed"] is False
    assert result["action"] == "BUY"
    assert len(trading.history()) == 0
