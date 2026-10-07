from datetime import datetime, timezone

import pytest

from atlas.trading.historical_derivatives_data import (
    OpenInterestObservation,
)
from atlas.trading.historical_derivatives_flow_assembler import (
    HistoricalDerivativesFlowAssembler,
)


def _kline(open_minute, close_minute, volume, taker_buy_volume):
    open_time = datetime(
        2026, 10, 6, 8, open_minute, tzinfo=timezone.utc
    )
    close_time = datetime(
        2026, 10, 6, 8, close_minute, tzinfo=timezone.utc
    )

    return [
        int(open_time.timestamp() * 1000),
        "100",
        "101",
        "99",
        "100",
        str(volume),
        int(close_time.timestamp() * 1000) - 1,
        "0",
        1,
        str(taker_buy_volume),
        "0",
        "0",
    ]


def _oi(minute, value):
    return OpenInterestObservation(
        timestamp=datetime(
            2026, 10, 6, 8, minute, tzinfo=timezone.utc
        ),
        open_interest=value,
        open_interest_value=value * 100.0,
    )


def test_assembles_completed_candle_with_boundary_open_interest():
    spot_klines = (
        _kline(25, 30, 100.0, 64.0),
    )
    futures_klines = (
        _kline(25, 30, 200.0, 96.0),
    )
    open_interest = (
        _oi(25, 100_000.0),
        _oi(30, 99_850.0),
        _oi(35, 120_000.0),
    )

    result = HistoricalDerivativesFlowAssembler().assemble(
        spot_klines=spot_klines,
        futures_klines=futures_klines,
        open_interest=open_interest,
    )

    assert len(result) == 1

    flow = result[0]

    assert flow.timestamp == pytest.approx(
        datetime(
            2026, 10, 6, 8, 25, tzinfo=timezone.utc
        ).timestamp()
    )
    assert flow.spot_taker_buy_ratio == pytest.approx(0.64)
    assert flow.futures_taker_buy_ratio == pytest.approx(0.48)

    # Candle 08:25-08:30 must use OI 08:25 -> 08:30.
    # The 08:35 observation is future information and must not leak in.
    assert flow.open_interest_change == pytest.approx(-0.0015)


def test_skips_candle_without_matching_futures_kline():
    spot_klines = (
        _kline(25, 30, 100.0, 64.0),
    )
    open_interest = (
        _oi(25, 100_000.0),
        _oi(30, 99_850.0),
    )

    result = HistoricalDerivativesFlowAssembler().assemble(
        spot_klines=spot_klines,
        futures_klines=(),
        open_interest=open_interest,
    )

    assert result == ()


def test_skips_candle_without_close_boundary_open_interest():
    spot_klines = (
        _kline(25, 30, 100.0, 64.0),
    )
    futures_klines = (
        _kline(25, 30, 200.0, 96.0),
    )
    open_interest = (
        _oi(25, 100_000.0),
        _oi(35, 120_000.0),
    )

    result = HistoricalDerivativesFlowAssembler().assemble(
        spot_klines=spot_klines,
        futures_klines=futures_klines,
        open_interest=open_interest,
    )

    assert result == ()


def test_reuses_shared_open_interest_boundary_between_adjacent_candles():
    spot_klines = (
        _kline(25, 30, 100.0, 64.0),
        _kline(30, 35, 120.0, 60.0),
    )
    futures_klines = (
        _kline(25, 30, 200.0, 96.0),
        _kline(30, 35, 240.0, 144.0),
    )
    open_interest = (
        _oi(25, 100_000.0),
        _oi(30, 99_850.0),
        _oi(35, 100_848.5),
    )

    result = HistoricalDerivativesFlowAssembler().assemble(
        spot_klines=spot_klines,
        futures_klines=futures_klines,
        open_interest=open_interest,
    )

    assert len(result) == 2
    assert result[0].open_interest_change == pytest.approx(-0.0015)
    assert result[1].open_interest_change == pytest.approx(0.01)
