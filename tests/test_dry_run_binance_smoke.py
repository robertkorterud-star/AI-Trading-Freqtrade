"""End-to-end contract tests for the Binance -> ATLAS dry-run path."""

import os

import pytest

from atlas.adapters.binance import BinanceAdapter
from atlas.trading.dry_run_loop import DryRunLoop


class FakeBinanceAdapter:
    """Deterministic public-market-data stand-in for the smoke test."""

    def get_klines(self, symbol, interval="1m", limit=100):
        assert symbol == "BTCUSDT"
        assert interval == "1m"
        assert limit == 100
        return [
            [1700000000000, "100", "102", "99", "101", "10"],
            [1700000060000, "101", "103", "100", "102", "12"],
        ]


def test_binance_public_market_data_reaches_atlas_dry_run():
    """Verify the complete market-data boundary without placing an order."""
    adapter = FakeBinanceAdapter()
    loop = DryRunLoop(agents=[])

    result = loop.process_binance(
        adapter,
        symbol="BTCUSDT",
        interval="1m",
        limit=100,
    )

    assert result.symbol == "BTCUSDT"
    assert result.price == 102.0
    assert len(result.algorithm_signals) == 6
    assert result.execution.symbol == "BTCUSDT"
    assert result.execution.action == result.decision.action.value


def test_binance_adapter_is_read_only_market_data_boundary():
    """The concrete Binance adapter exposes only public GET market data."""
    adapter = BinanceAdapter()

    assert adapter.BASE_URL == "https://data-api.binance.vision/api/v3"
    assert not hasattr(adapter, "create_order")
    assert not hasattr(adapter, "place_order")


@pytest.mark.skipif(
    os.getenv("ATLAS_LIVE_BINANCE_SMOKE") != "1",
    reason="set ATLAS_LIVE_BINANCE_SMOKE=1 to run the live public-data smoke test",
)
def test_live_binance_public_data_reaches_atlas_dry_run():
    """Exercise the real Binance public endpoint while keeping execution dry-run."""
    adapter = BinanceAdapter()
    loop = DryRunLoop(agents=[])

    result = loop.process_binance(
        adapter,
        symbol="BTCUSDT",
        interval="1m",
        limit=100,
    )

    assert result.symbol == "BTCUSDT"
    assert result.price > 0
    assert len(result.algorithm_signals) == 6
    assert result.execution.symbol == "BTCUSDT"
    assert result.execution.action == result.decision.action.value
    assert result.execution.status.value == "SIMULATED"
