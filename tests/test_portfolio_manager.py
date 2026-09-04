import pytest

from atlas.portfolio.manager import (
    PortfolioManager,
    PortfolioPosition,
)


def test_allows_allocation_within_portfolio_and_position_limits() -> None:
    manager = PortfolioManager(max_exposure_pct=80.0, max_single_position_pct=20.0)

    result = manager.assess(
        "EQNR.OL",
        requested_value=10_000,
        equity=100_000,
        positions=[PortfolioPosition("DNB.OL", 20_000)],
    )

    assert result.allowed is True
    assert result.approved_value == 10_000
    assert result.current_exposure_pct == 20.0
    assert result.resulting_exposure_pct == 30.0


def test_rejects_allocation_above_single_position_capacity() -> None:
    manager = PortfolioManager(max_exposure_pct=80.0, max_single_position_pct=20.0)

    result = manager.assess(
        "EQNR.OL",
        requested_value=15_000,
        equity=100_000,
        positions=[PortfolioPosition("EQNR.OL", 10_000)],
    )

    assert result.allowed is False
    assert result.approved_value == 10_000
    assert result.available_capacity_value == 10_000
    assert any("single-position" in reason for reason in result.reasons)


def test_rejects_allocation_above_aggregate_exposure_capacity() -> None:
    manager = PortfolioManager(max_exposure_pct=50.0, max_single_position_pct=50.0)

    result = manager.assess(
        "EQNR.OL",
        requested_value=20_000,
        equity=100_000,
        positions=[
            PortfolioPosition("DNB.OL", 20_000),
            PortfolioPosition("YAR.OL", 20_000),
        ],
    )

    assert result.allowed is False
    assert result.approved_value == 10_000
    assert result.resulting_exposure_pct == 50.0
    assert any("exposure capacity" in reason for reason in result.reasons)


def test_existing_symbol_value_counts_toward_single_position_limit() -> None:
    manager = PortfolioManager(max_exposure_pct=100.0, max_single_position_pct=20.0)

    result = manager.assess(
        "EQNR.OL",
        requested_value=5_000,
        equity=100_000,
        positions=[PortfolioPosition("eqnr.ol", 18_000)],
    )

    assert result.allowed is False
    assert result.approved_value == 2_000


def test_zero_allocation_is_allowed_without_changing_exposure() -> None:
    manager = PortfolioManager()

    result = manager.assess("EQNR.OL", 0, 100_000)

    assert result.allowed is True
    assert result.approved_value == 0
    assert result.resulting_exposure_value == 0
    assert result.reasons == ("No additional allocation requested.",)


def test_validates_configuration_and_inputs() -> None:
    with pytest.raises(ValueError):
        PortfolioManager(max_exposure_pct=10.0, max_single_position_pct=20.0)

    manager = PortfolioManager()

    with pytest.raises(ValueError):
        manager.assess("", 1_000, 100_000)

    with pytest.raises(ValueError):
        manager.assess("EQNR.OL", 1_000, 0)


def test_position_rejects_invalid_values() -> None:
    with pytest.raises(ValueError):
        PortfolioPosition("EQNR.OL", -1)

    with pytest.raises(ValueError):
        PortfolioPosition("", 1_000)
