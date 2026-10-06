from datetime import datetime, timezone

import pytest

from atlas.trading.historical_derivatives_data import (
    FundingRateObservation,
    OpenInterestObservation,
)


def test_funding_rate_observation_preserves_normalized_values():
    timestamp = datetime(2026, 1, 1, tzinfo=timezone.utc)

    observation = FundingRateObservation(
        timestamp=timestamp,
        funding_rate=0.0001,
        mark_price=93450.0,
    )

    assert observation.timestamp == timestamp
    assert observation.funding_rate == 0.0001
    assert observation.mark_price == 93450.0


def test_open_interest_observation_preserves_normalized_values():
    timestamp = datetime(2026, 1, 1, tzinfo=timezone.utc)

    observation = OpenInterestObservation(
        timestamp=timestamp,
        open_interest=95312.78,
        open_interest_value=8122126905.81,
    )

    assert observation.timestamp == timestamp
    assert observation.open_interest == 95312.78
    assert observation.open_interest_value == 8122126905.81


@pytest.mark.parametrize(
    "observation",
    [
        lambda: FundingRateObservation(
            timestamp="2026-01-01",
            funding_rate=0.0001,
            mark_price=93450.0,
        ),
        lambda: OpenInterestObservation(
            timestamp="2026-01-01",
            open_interest=95312.78,
            open_interest_value=8122126905.81,
        ),
    ],
)
def test_derivatives_observations_require_datetime_timestamp(observation):
    with pytest.raises(ValueError, match="timestamp must be datetime"):
        observation()


def test_open_interest_cannot_be_negative():
    with pytest.raises(ValueError, match="open_interest cannot be negative"):
        OpenInterestObservation(
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
            open_interest=-1.0,
            open_interest_value=100.0,
        )


def test_open_interest_value_cannot_be_negative():
    with pytest.raises(
        ValueError,
        match="open_interest_value cannot be negative",
    ):
        OpenInterestObservation(
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
            open_interest=100.0,
            open_interest_value=-1.0,
        )


def test_funding_rate_observation_has_no_trading_action():
    observation = FundingRateObservation(
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        funding_rate=-0.0002,
        mark_price=93450.0,
    )

    assert not hasattr(observation, "action")


def test_derivatives_flow_observation_is_descriptive_market_evidence():
    from atlas.trading.historical_derivatives_data import (
        DerivativesFlowObservation,
    )

    observation = DerivativesFlowObservation(
        timestamp=1_760_000_000.0,
        spot_taker_buy_ratio=0.64,
        futures_taker_buy_ratio=0.48,
        open_interest_change=-0.0015,
    )

    assert observation.timestamp == 1_760_000_000.0
    assert observation.spot_taker_buy_ratio == 0.64
    assert observation.futures_taker_buy_ratio == 0.48
    assert observation.open_interest_change == -0.0015
    assert observation.taker_buy_ratio_delta == pytest.approx(0.16)

    # Market evidence only: this model must not own a trading decision.
    assert not hasattr(observation, "action")
    assert not hasattr(observation, "decision")
