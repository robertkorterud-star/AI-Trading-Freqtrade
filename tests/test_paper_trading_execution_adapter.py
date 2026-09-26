import pytest

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

    # Pre-populate 5.0 units so selling 2.5 exercises a true partial close.
    portfolio.buy(symbol="BTC-USD", amount_nok=1000000.0, price_usd=20000.0, usd_nok=10.0)

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

    snapshot = portfolio.as_dict(usd_nok=10.0)
    position = next(p for p in snapshot["positions"] if p["symbol"] == "BTC-USD")
    assert position["quantity"] == 2.5

    # trading history should contain one sell
    assert trading.count() == 1
    trade = trading.history()[0]
    assert trade["quantity"] == 2.5


def test_paper_adapter_executes_approved_repeated_buy_requests():
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

    first_result = service.execute(first_buy, price=20000.0)
    repeated_result = service.execute(repeated_buy, price=19900.0)

    assert first_result is not None
    assert repeated_result is not None
    assert trading.count() == 2

def test_paper_adapter_buy_persistence_failure_keeps_account_unchanged():
    portfolio = PortfolioService(1000000)

    class FailingRepository:
        def load(self):
            return []

        def save(self, trade):
            raise RuntimeError("trade persistence failed")

    trading = TradingService(repository=FailingRepository())

    class FakeExchange:
        def get_rate(self, base, target):
            return type("R", (), {"rate": 10.0})()

    adapter = PaperTradingExecutionAdapter(
        portfolio=portfolio,
        trading=trading,
        exchange_service=FakeExchange(),
    )
    service = DecisionExecutionService(ExecutionEngine(adapter))
    decision = _make_decision("BTC-USD", Action.BUY, 0.5)

    before = portfolio.as_dict(usd_nok=10.0)

    with pytest.raises(RuntimeError, match="trade persistence failed"):
        service.execute(decision, price=20000.0)

    assert trading.history() == []
    assert portfolio.as_dict(usd_nok=10.0) == before

def test_paper_adapter_sell_persistence_failure_keeps_account_unchanged():
    portfolio = PortfolioService(1000000)

    class FailingRepository:
        def load(self):
            return []

        def save(self, trade):
            raise RuntimeError("trade persistence failed")

    trading = TradingService(repository=FailingRepository())

    class FakeExchange:
        def get_rate(self, base, target):
            return type("R", (), {"rate": 10.0})()

    adapter = PaperTradingExecutionAdapter(
        portfolio=portfolio,
        trading=trading,
        exchange_service=FakeExchange(),
    )

    portfolio.buy(
        symbol="BTC-USD",
        amount_nok=100000.0,
        price_usd=20000.0,
        usd_nok=10.0,
    )
    before = portfolio.as_dict(usd_nok=10.0)

    service = DecisionExecutionService(ExecutionEngine(adapter))
    decision = _make_decision("BTC-USD", Action.SELL, 0.25)

    with pytest.raises(RuntimeError, match="trade persistence failed"):
        service.execute(decision, price=22000.0)

    assert trading.history() == []
    assert portfolio.as_dict(usd_nok=10.0) == before

def test_paper_adapter_repeated_buy_persistence_failure_restores_existing_position_state():
    portfolio = PortfolioService(1000000)
    portfolio.buy(
        symbol="BTC-USD",
        amount_nok=100000.0,
        price_usd=20000.0,
        usd_nok=10.0,
    )
    portfolio.update_prices({"BTC-USD": 25000.0})

    class FailingRepository:
        def load(self):
            return []

        def save(self, trade):
            raise RuntimeError("trade persistence failed")

    trading = TradingService(repository=FailingRepository())

    class FakeExchange:
        def get_rate(self, base, target):
            return type("R", (), {"rate": 10.0})()

    adapter = PaperTradingExecutionAdapter(
        portfolio=portfolio,
        trading=trading,
        exchange_service=FakeExchange(),
    )
    service = DecisionExecutionService(ExecutionEngine(adapter))
    decision = _make_decision("BTC-USD", Action.BUY, 0.25)

    before = portfolio.as_dict(usd_nok=10.0)

    with pytest.raises(RuntimeError, match="trade persistence failed"):
        service.execute(decision, price=22000.0)

    assert trading.history() == []
    assert portfolio.as_dict(usd_nok=10.0) == before

