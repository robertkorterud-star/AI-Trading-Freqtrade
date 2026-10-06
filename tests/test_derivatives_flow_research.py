from datetime import datetime, timedelta, timezone

import pytest

from atlas.trading.historical_derivatives_data import (
    DerivativesFlowObservation,
)
from atlas.trading.historical_market_data import (
    HistoricalMarketData,
    OHLCVBar,
)
from atlas.trading.derivatives_flow_research import (
    DerivativesFlowResearch,
)


def _market_data() -> HistoricalMarketData:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)

    closes = [100.0, 110.0, 99.0]

    return HistoricalMarketData(
        symbol="BTCUSDT",
        timeframe="5m",
        source="test",
        bars=[
            OHLCVBar(
                timestamp=start + timedelta(minutes=5 * index),
                open=close,
                high=close + 1.0,
                low=close - 1.0,
                close=close,
                volume=1000.0,
            )
            for index, close in enumerate(closes)
        ],
    )


def test_derivatives_flow_research_measures_forward_return_without_trading_action():
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)

    flows = (
        DerivativesFlowObservation(
            timestamp=start.timestamp(),
            spot_taker_buy_ratio=0.70,
            futures_taker_buy_ratio=0.50,
            open_interest_change=0.02,
        ),
        DerivativesFlowObservation(
            timestamp=(
                start + timedelta(minutes=5)
            ).timestamp(),
            spot_taker_buy_ratio=0.40,
            futures_taker_buy_ratio=0.60,
            open_interest_change=-0.01,
        ),
    )

    result = DerivativesFlowResearch(
        forward_period=1,
    ).run(
        data=_market_data(),
        observations=flows,
    )

    assert result.symbol == "BTCUSDT"
    assert result.timeframe == "5m"
    assert len(result.observations) == 2

    first = result.observations[0]
    second = result.observations[1]

    assert first.flow is flows[0]
    assert first.forward_return_percent == pytest.approx(10.0)

    assert second.flow is flows[1]
    assert second.forward_return_percent == pytest.approx(-10.0)

    assert not hasattr(first, "action")
    assert not hasattr(first, "decision")
    assert not hasattr(result, "action")
    assert not hasattr(result, "decision")


def test_forward_period_must_be_positive():
    with pytest.raises(
        ValueError,
        match="forward_period must be positive",
    ):
        DerivativesFlowResearch(forward_period=0)


def test_flow_without_matching_market_timestamp_is_skipped():
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)

    flow = DerivativesFlowObservation(
        timestamp=(
            start + timedelta(minutes=2)
        ).timestamp(),
        spot_taker_buy_ratio=0.70,
        futures_taker_buy_ratio=0.50,
        open_interest_change=0.02,
    )

    result = DerivativesFlowResearch().run(
        data=_market_data(),
        observations=(flow,),
    )

    assert result.observations == ()


def test_flow_without_future_candle_is_skipped():
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)

    flow = DerivativesFlowObservation(
        timestamp=(
            start + timedelta(minutes=10)
        ).timestamp(),
        spot_taker_buy_ratio=0.70,
        futures_taker_buy_ratio=0.50,
        open_interest_change=0.02,
    )

    result = DerivativesFlowResearch(
        forward_period=1,
    ).run(
        data=_market_data(),
        observations=(flow,),
    )

    assert result.observations == ()
