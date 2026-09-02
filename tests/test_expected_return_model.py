import pytest

from atlas.models.action import Action
from atlas.trading.expected_return_model import ExpectedReturnModel


def test_buy_estimate_uses_historical_mean_and_haircut():
    model = ExpectedReturnModel(min_samples=4, haircut=0.5)

    result = model.estimate(
        Action.BUY,
        [0.02, 0.04, 0.01, 0.03],
    )

    assert result == pytest.approx(0.0125)


def test_sell_estimate_reverses_historical_direction():
    model = ExpectedReturnModel(min_samples=4, haircut=1.0)

    result = model.estimate(
        Action.SELL,
        [-0.02, -0.04, -0.01, -0.03],
    )

    assert result == pytest.approx(0.025)


def test_insufficient_history_returns_zero():
    model = ExpectedReturnModel(min_samples=4)

    assert model.estimate(Action.BUY, [0.05, 0.04, 0.03]) == 0.0


def test_non_positive_directional_mean_returns_zero():
    model = ExpectedReturnModel(min_samples=4, haircut=1.0)

    assert model.estimate(Action.BUY, [0.02, -0.02, 0.01, -0.01]) == 0.0


def test_hold_returns_zero_without_using_history():
    model = ExpectedReturnModel(min_samples=100)

    assert model.estimate(Action.HOLD, [0.50]) == 0.0


def test_estimate_is_capped():
    model = ExpectedReturnModel(min_samples=2, haircut=1.0, max_return=0.05)

    assert model.estimate(Action.BUY, [0.20, 0.10]) == pytest.approx(0.05)


def test_invalid_configuration_is_rejected():
    with pytest.raises(ValueError):
        ExpectedReturnModel(min_samples=0)

    with pytest.raises(ValueError):
        ExpectedReturnModel(haircut=0.0)

    with pytest.raises(ValueError):
        ExpectedReturnModel(max_return=0.0)


def test_non_finite_historical_return_is_rejected():
    model = ExpectedReturnModel(min_samples=2)

    with pytest.raises(ValueError):
        model.estimate(Action.BUY, [0.01, float("nan")])
