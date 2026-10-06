from datetime import datetime, timezone

import pytest

from atlas.trading.derivatives_flow_builder import DerivativesFlowBuilder
from atlas.trading.historical_derivatives_data import (
    DerivativesFlowObservation,
    OpenInterestObservation,
)


def test_builds_descriptive_flow_observation_from_spot_futures_and_oi():
    spot_kline = [
        1_791_279_000_000,
        "86200.0",
        "86250.0",
        "86180.0",
        "86230.0",
        "100.0",
        1_791_279_059_999,
        "8623000.0",
        321,
        "64.0",
        "5518720.0",
        "0",
    ]
    futures_kline = [
        1_791_279_000_000,
        "86200.0",
        "86250.0",
        "86180.0",
        "86230.0",
        "200.0",
        1_791_279_059_999,
        "17246000.0",
        400,
        "96.0",
        "8278080.0",
        "0",
    ]

    previous_oi = OpenInterestObservation(
        timestamp=datetime(
            2026, 10, 6, 8, 25, tzinfo=timezone.utc
        ),
        open_interest=100_000.0,
        open_interest_value=8_620_000_000.0,
    )
    current_oi = OpenInterestObservation(
        timestamp=datetime(
            2026, 10, 6, 8, 30, tzinfo=timezone.utc
        ),
        open_interest=99_850.0,
        open_interest_value=8_607_070_000.0,
    )

    observation = DerivativesFlowBuilder.build(
        spot_kline=spot_kline,
        futures_kline=futures_kline,
        previous_open_interest=previous_oi,
        current_open_interest=current_oi,
    )

    assert isinstance(observation, DerivativesFlowObservation)
    assert observation.timestamp == pytest.approx(
        1_791_279_000.0
    )
    assert observation.spot_taker_buy_ratio == pytest.approx(0.64)
    assert observation.futures_taker_buy_ratio == pytest.approx(0.48)
    assert observation.taker_buy_ratio_delta == pytest.approx(0.16)
    assert observation.open_interest_change == pytest.approx(-0.0015)

    assert not hasattr(observation, "action")
    assert not hasattr(observation, "decision")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("spot", "0"),
        ("futures", "0"),
    ],
)
def test_rejects_non_positive_kline_volume(field, value):
    spot_kline = [
        1_791_279_000_000,
        "86200", "86250", "86180", "86230",
        "100", 1_791_279_059_999, "0", 1, "50", "0", "0",
    ]
    futures_kline = [
        1_791_279_000_000,
        "86200", "86250", "86180", "86230",
        "200", 1_791_279_059_999, "0", 1, "100", "0", "0",
    ]

    if field == "spot":
        spot_kline[5] = value
    else:
        futures_kline[5] = value

    previous_oi = OpenInterestObservation(
        timestamp=datetime(2026, 10, 6, 8, 25, tzinfo=timezone.utc),
        open_interest=100_000.0,
        open_interest_value=1.0,
    )
    current_oi = OpenInterestObservation(
        timestamp=datetime(2026, 10, 6, 8, 30, tzinfo=timezone.utc),
        open_interest=99_850.0,
        open_interest_value=1.0,
    )

    with pytest.raises(ValueError, match="volume must be positive"):
        DerivativesFlowBuilder.build(
            spot_kline=spot_kline,
            futures_kline=futures_kline,
            previous_open_interest=previous_oi,
            current_open_interest=current_oi,
        )


def test_rejects_mismatched_spot_and_futures_kline_timestamps():
    spot_kline = [
        1_791_279_000_000,
        "86200", "86250", "86180", "86230",
        "100", 1_791_279_059_999, "0", 1, "50", "0", "0",
    ]
    futures_kline = [
        1_791_279_060_000,
        "86200", "86250", "86180", "86230",
        "200", 1_791_279_119_999, "0", 1, "100", "0", "0",
    ]

    previous_oi = OpenInterestObservation(
        timestamp=datetime(2026, 10, 6, 8, 25, tzinfo=timezone.utc),
        open_interest=100_000.0,
        open_interest_value=1.0,
    )
    current_oi = OpenInterestObservation(
        timestamp=datetime(2026, 10, 6, 8, 30, tzinfo=timezone.utc),
        open_interest=99_850.0,
        open_interest_value=1.0,
    )

    with pytest.raises(ValueError, match="kline timestamps must match"):
        DerivativesFlowBuilder.build(
            spot_kline=spot_kline,
            futures_kline=futures_kline,
            previous_open_interest=previous_oi,
            current_open_interest=current_oi,
        )


def test_rejects_zero_previous_open_interest():
    kline = [
        1_791_279_000_000,
        "86200", "86250", "86180", "86230",
        "100", 1_791_279_059_999, "0", 1, "50", "0", "0",
    ]

    previous_oi = OpenInterestObservation(
        timestamp=datetime(2026, 10, 6, 8, 25, tzinfo=timezone.utc),
        open_interest=0.0,
        open_interest_value=0.0,
    )
    current_oi = OpenInterestObservation(
        timestamp=datetime(2026, 10, 6, 8, 30, tzinfo=timezone.utc),
        open_interest=100.0,
        open_interest_value=1.0,
    )

    with pytest.raises(
        ValueError,
        match="previous open interest must be positive",
    ):
        DerivativesFlowBuilder.build(
            spot_kline=kline,
            futures_kline=kline,
            previous_open_interest=previous_oi,
            current_open_interest=current_oi,
        )
