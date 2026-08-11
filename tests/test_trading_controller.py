from atlas.models.action import Action
from atlas.models.decision_result import DecisionResult
from atlas.risk.risk_engine import RiskEngine
from atlas.services.portfolio_service import PortfolioService
from atlas.trading.paper_trading_engine import PaperTradingEngine
from atlas.trading.trading_service import TradingService
from atlas.trading.trading_controller import TradingController


def make_buy():
    return DecisionResult(
        symbol="BTC-USD",
        action=Action.BUY,
        confidence=89.5,
        evidence=86.5,
    )


def make_sell():
    return DecisionResult(
        symbol="BTC-USD",
        action=Action.SELL,
        confidence=40.0,
        evidence=40.0,
    )


def test_controller_executes_buy_only_once_for_same_decision():

    portfolio = PortfolioService(5000)
    risk = RiskEngine()
    trading = TradingService()

    engine = PaperTradingEngine(
        portfolio=portfolio,
        risk=risk,
        trading=trading,
    )

    controller = TradingController(
        trader=engine,
    )

    first = controller.process(
        decision=make_buy(),
        price_usd=65000,
        usd_nok=9.50,
        amount_nok=1000,
    )

    second = controller.process(
        decision=make_buy(),
        price_usd=65000,
        usd_nok=9.50,
        amount_nok=1000,
    )

    assert first["executed"] is True
    assert second["executed"] is False
    assert second["reason"] == "Decision already executed."
    assert trading.count() == 1


def test_controller_allows_sell_after_buy():

    portfolio = PortfolioService(5000)
    risk = RiskEngine()
    trading = TradingService()

    engine = PaperTradingEngine(
        portfolio=portfolio,
        risk=risk,
        trading=trading,
    )

    controller = TradingController(
        trader=engine,
    )

    buy = controller.process(
        decision=make_buy(),
        price_usd=65000,
        usd_nok=9.50,
        amount_nok=1000,
    )

    sell = controller.process(
        decision=make_sell(),
        price_usd=70000,
        usd_nok=9.50,
    )

    assert buy["executed"] is True
    assert sell["executed"] is True
    assert sell["realized_pnl_nok"] == 76.92
    assert trading.count() == 2
