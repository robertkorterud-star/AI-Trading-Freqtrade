from atlas.execution.protocol import ExecutionEngine
from atlas.execution.service import DecisionExecutionService
from atlas.execution.paper_adapter import PaperTradingExecutionAdapter
from atlas.services.portfolio_service import PortfolioService
from atlas.trading.trading_service import TradingService
from atlas.models.decision_result import DecisionResult
from atlas.models.action import Action
from atlas.risk.manager import RiskAssessment


def _make_decision(symbol: str, action: Action, quantity: float) -> DecisionResult:
    decision = DecisionResult(
        symbol=symbol,
        action=action,
        confidence=1.0,
        evidence=100.0,
    )

    # attach a RiskAssessment compatible with DecisionExecutionService
    decision.risk_assessment = RiskAssessment(
        action=action,
        allowed=True,
        risk_level="LOW",
        position_size=quantity,
        position_value=quantity * 100.0,
        stop_loss_price=None,
        take_profit_price=None,
        reasons=(),
    )

    decision.portfolio_assessment = None

    return decision


def test_paper_adapter_buy_uses_risk_quantity_and_updates_portfolio_and_trading():
    portfolio = PortfolioService(1000000)
    trading = TradingService()

    class FakeExchange:
        def get_rate(self, base, target):
            return type("R", (), {"rate": 10.0})()

    adapter = PaperTradingExecutionAdapter(
        portfolio=portfolio,
        trading=trading,
        exchange_service=FakeExchange(),
    )

    engine = ExecutionEngine(adapter)
    service = DecisionExecutionService(engine)

    decision = _make_decision("BTC-USD", Action.BUY, 0.5)

    result = service.execute(decision, price=20000.0)

    assert result is not None
    assert result.symbol == "BTC-USD"
    assert result.action is Action.BUY
    assert result.quantity == 0.5

    # portfolio should now contain the position with the requested quantity
    snapshot = portfolio.as_dict(usd_nok=10.0)
    positions = snapshot["positions"]
    assert any(p["symbol"] == "BTC-USD" and abs(p["quantity"] - 0.5) < 1e-8 for p in positions)

    # trading history should contain one buy
    assert trading.count() == 1


def test_paper_adapter_sell_respects_portfolio_service_contract():
    portfolio = PortfolioService(1000000)
    trading = TradingService()

    # Pre-populate position via portfolio.buy so average price and quantity exist
    # amount_nok chosen so resulting quantity >= 2.5 units
    portfolio.buy(symbol="BTC-USD", amount_nok=500000.0, price_usd=20000.0, usd_nok=10.0)

    class FakeExchange:
        def get_rate(self, base, target):
            return type("R", (), {"rate": 10.0})()

    adapter = PaperTradingExecutionAdapter(
        portfolio=portfolio,
        trading=trading,
        exchange_service=FakeExchange(),
    )

    engine = ExecutionEngine(adapter)
    service = DecisionExecutionService(engine)

    # Sell half the position; risk.position_size is units to sell
    decision = _make_decision("BTC-USD", Action.SELL, 2.5)

    result = service.execute(decision, price=20000.0)

    assert result is not None
    assert result.action is Action.SELL
    # ExecutionResult quantity should reflect sold units
    assert result.quantity == 2.5

    # trading history should contain one sell
    assert trading.count() == 1


def test_paper_adapter_blocks_repeated_buy_until_price_drop_threshold():
    portfolio = PortfolioService(1000000)
    trading = TradingService()

    class FakeExchange:
        def get_rate(self, base, target):
            return type("R", (), {"rate": 10.0})()

    adapter = PaperTradingExecutionAdapter(
        portfolio=portfolio,
        trading=trading,
        exchange_service=FakeExchange(),
    )

    engine = ExecutionEngine(adapter)
    service = DecisionExecutionService(engine)

    first_buy = _make_decision("BTC-USD", Action.BUY, 0.5)
    repeated_buy = _make_decision("BTC-USD", Action.BUY, 0.5)
    accumulation_buy = _make_decision("BTC-USD", Action.BUY, 0.5)
    premature_follow_up = _make_decision("BTC-USD", Action.BUY, 0.5)

    first_result = service.execute(first_buy, price=20000.0)
    repeated_result = service.execute(repeated_buy, price=19900.0)
    accumulation_result = service.execute(accumulation_buy, price=19600.0)
    premature_follow_up_result = service.execute(
        premature_follow_up,
        price=19400.0,
    )

    assert first_result is not None
    assert repeated_result is None
    assert accumulation_result is not None
    assert premature_follow_up_result is None

    snapshot = portfolio.as_dict(usd_nok=10.0)
    positions = snapshot["positions"]

    assert len(positions) == 1
    assert positions[0]["symbol"] == "BTC-USD"
    assert abs(positions[0]["quantity"] - 1.0) < 1e-8
    assert trading.count() == 2
