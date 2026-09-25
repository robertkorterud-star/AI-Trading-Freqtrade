import pytest

from atlas.models.action import Action
from atlas.risk.manager import RiskManager


def test_buy_position_is_limited_by_risk_budget():
    manager = RiskManager(risk_per_trade_pct=1.0, max_position_pct=60.0, stop_loss_pct=2.0)

    result = manager.assess(Action.BUY, price=100.0, equity=10_000.0)

    assert result.allowed is True
    assert result.position_size == pytest.approx(50.0)
    assert result.position_value == pytest.approx(5_000.0)
    assert result.stop_loss_price == pytest.approx(98.0)
    assert result.take_profit_price == pytest.approx(104.0)


def test_position_is_capped_by_max_position_pct():
    manager = RiskManager(risk_per_trade_pct=0.2, max_position_pct=10.0, stop_loss_pct=2.0)

    result = manager.assess(Action.BUY, price=100.0, equity=10_000.0)

    assert result.position_value == pytest.approx(1_000.0)
    assert result.position_size == pytest.approx(10.0)


def test_sell_without_open_position_is_blocked():
    result = RiskManager().assess(Action.SELL, price=100.0, equity=10_000.0)

    assert result.allowed is False
    assert result.position_size == 0.0
    assert result.stop_loss_price is None
    assert result.take_profit_price is None
    assert result.reasons == ("No open position available to sell.",)


def test_drawdown_limit_blocks_new_exposure():
    manager = RiskManager(max_drawdown_pct=20.0)

    result = manager.assess(Action.BUY, price=100.0, equity=10_000.0, drawdown_pct=20.0)

    assert result.allowed is False
    assert result.position_size == 0.0
    assert result.risk_level == "BLOCKED"


def test_max_exposure_blocks_new_exposure():
    manager = RiskManager(max_exposure_pct=50.0)

    result = manager.assess(Action.BUY, price=100.0, equity=10_000.0, current_exposure_pct=50.0)

    assert result.allowed is False
    assert result.position_size == 0.0


def test_hold_never_creates_a_position():
    result = RiskManager().assess(Action.HOLD, price=100.0, equity=10_000.0)

    assert result.allowed is True
    assert result.position_size == 0.0
    assert result.stop_loss_price is None
    assert result.take_profit_price is None


def test_invalid_risk_inputs_are_rejected():
    with pytest.raises(ValueError, match="price and equity"):
        RiskManager().assess(Action.BUY, price=0.0, equity=10_000.0)

    with pytest.raises(ValueError, match="risk parameters"):
        RiskManager(stop_loss_pct=-1.0)
