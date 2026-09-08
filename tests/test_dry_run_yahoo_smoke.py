"""End-to-end contract test for the Yahoo -> ATLAS dry-run path."""

from unittest.mock import patch

import pandas as pd

from atlas.adapters.market_data import YFinanceMarketDataProvider
from atlas.trading.dry_run_loop import DryRunLoop


def test_yahoo_public_market_data_reaches_atlas_dry_run():
    """Verify Yahoo normalized market data reaches the dry-run pipeline."""
    history = pd.DataFrame(
        {
            "Open": [100.0 + index * 0.1 for index in range(100)],
            "High": [101.0 + index * 0.1 for index in range(100)],
            "Low": [99.0 + index * 0.1 for index in range(100)],
            "Close": [100.5 + index * 0.1 for index in range(100)],
            "Volume": [1000.0] * 100,
        },
        index=pd.date_range("2026-09-01", periods=100, freq="D"),
    )

    with patch("atlas.adapters.market_data.yf.Ticker") as mock_ticker:
        mock_ticker.return_value.history.return_value = history

        provider = YFinanceMarketDataProvider(history_period="3mo")
        snapshot = provider.snapshot(
            "NVDA",
            interval="1d",
            limit=100,
        )

    loop = DryRunLoop(agents=[])
    result = loop.process(snapshot)

    assert result.symbol == "NVDA"
    assert result.price == 110.4
    assert len(result.algorithm_signals) == 6
    assert result.execution.symbol == "NVDA"
    assert result.execution.action == result.decision.action.value
    assert result.execution.executed is False
