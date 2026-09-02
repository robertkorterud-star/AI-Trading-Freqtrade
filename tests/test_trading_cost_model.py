import pytest

from atlas.trading.trading_cost_model import TradingCostModel


def test_default_round_trip_cost_includes_fee_spread_and_slippage():
    model = TradingCostModel()

    # 0.10% fee per side + 0.01% spread per side + 0.01% slippage per side.
    assert model.one_way_cost_rate == pytest.approx(0.0012)
    assert model.round_trip_cost_rate == pytest.approx(0.0024)


def test_round_trip_cost_amount():
    model = TradingCostModel(
        fee_rate=0.001,
        spread_bps=4.0,
        slippage_bps=2.0,
    )

    # 0.10% + 0.02% + 0.02% = 0.14% per side, 0.28% round trip.
    assert model.round_trip_cost(100_000.0) == pytest.approx(280.0)


def test_net_return_subtracts_round_trip_costs():
    model = TradingCostModel(
        fee_rate=0.001,
        spread_bps=4.0,
        slippage_bps=2.0,
    )

    assert model.net_return(0.01) == pytest.approx(0.0072)


def test_net_pnl_can_be_negative_when_costs_exceed_gross_return():
    model = TradingCostModel(
        fee_rate=0.001,
        spread_bps=4.0,
        slippage_bps=2.0,
    )

    assert model.net_pnl(100_000.0, 0.002) == pytest.approx(-80.0)


def test_negative_cost_parameters_are_rejected():
    with pytest.raises(ValueError, match="fee_rate"):
        TradingCostModel(fee_rate=-0.001)

    with pytest.raises(ValueError, match="spread_bps"):
        TradingCostModel(spread_bps=-1.0)

    with pytest.raises(ValueError, match="slippage_bps"):
        TradingCostModel(slippage_bps=-1.0)


def test_non_positive_notional_is_rejected():
    model = TradingCostModel()

    with pytest.raises(ValueError, match="notional"):
        model.round_trip_cost(0.0)
