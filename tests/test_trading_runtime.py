from atlas.core.config import AtlasConfig
from atlas.models.action import Action
from atlas.models.decision_result import DecisionResult
from atlas.services.portfolio_service import PortfolioService
from atlas.risk.risk_engine import RiskEngine
from atlas.trading.paper_trading_engine import PaperTradingEngine
from atlas.trading.trading_controller import TradingController
from atlas.trading.trading_service import TradingService
from atlas.trading.trading_runtime import TradingRuntime


def make_buy():
    return DecisionResult(
        symbol="BTC-USD",
        action=Action.BUY,
        confidence=89.5,
        evidence=86.5,
    )


def make_runtime(config=None):
    config = config or AtlasConfig(
    trading_mode="paper",
)

    portfolio = PortfolioService(
        config.capital_limit
    )

    risk = RiskEngine()
    trading = TradingService()

    trader = PaperTradingEngine(
        portfolio=portfolio,
        risk=risk,
        trading=trading,
    )

    controller = TradingController(
        trader=trader,
    )

    return TradingRuntime(
        config=config,
        controller=controller,
    )


def test_trading_runtime_executes_paper_buy():

    runtime = make_runtime()

    result = runtime.execute(
        decision=make_buy(),
        price_usd=65000,
        usd_nok=9.50,
        amount_nok=1000,
    )

    assert result["executed"] is True
    assert result["action"] == "BUY"


def test_trading_runtime_rejects_when_paper_trading_disabled():

    config = AtlasConfig(
        paper_trading=False,
    )

    runtime = make_runtime(config)

    result = runtime.execute(
        decision=make_buy(),
        price_usd=65000,
        usd_nok=9.50,
        amount_nok=1000,
    )

    assert result["executed"] is False
    assert result["reason"] == "Paper trading is disabled."
def test_trading_runtime_preserves_btc_usd_symbol():

    runtime = make_runtime()

    decision = make_buy()

    result = runtime.execute(
        decision=decision,
        price_usd=65000,
        usd_nok=9.50,
        amount_nok=1000,
    )

    assert result["symbol"] == "BTC-USD"

def test_trading_runtime_rejects_advisor_mode():

    config = AtlasConfig(
        trading_mode="advisor",
        paper_trading=True,
    )

    runtime = make_runtime(config)

    result = runtime.execute(
        decision=make_buy(),
        price_usd=65000,
        usd_nok=9.50,
        amount_nok=1000,
    )

    assert result["executed"] is False
    assert result["reason"] == "Trading mode is advisor."


def test_trading_runtime_records_prediction():
    from atlas.trading.prediction_tracker import PredictionTracker

    tracker = PredictionTracker()

    runtime = TradingRuntime(
        config=AtlasConfig(
            trading_mode="advisor",
            paper_trading=False,
        ),
        controller=None,
        prediction_tracker=tracker,
    )

    decision = DecisionResult(
        symbol="NVDA",
        action=Action.BUY,
        confidence=88.0,
        evidence=85.0,
    )

    runtime.execute(
        decision=decision,
        price_usd=180.0,
        usd_nok=10.0,
    )

    history = tracker.history()

    assert tracker.count() == 1
    assert history[0]["symbol"] == "NVDA"
    assert history[0]["action"] == "BUY"
    assert history[0]["confidence"] == 88.0
    assert history[0]["evidence"] == 85.0
    assert history[0]["price_usd"] == 180.0
