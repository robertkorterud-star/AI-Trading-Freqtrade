from datetime import datetime

import pytest

from atlas.trading.historical_data_provider import (
    HistoricalDataProvider,
)


def test_historical_data_provider_is_abstract():

    with pytest.raises(TypeError):
        HistoricalDataProvider()


def test_provider_contract_can_be_implemented():

    class TestProvider(
        HistoricalDataProvider
    ):

        def load(
            self,
            symbol: str,
            start: datetime | None = None,
            end: datetime | None = None,
        ):
            return None

    provider = TestProvider()

    assert isinstance(
        provider,
        HistoricalDataProvider,
    )


def test_provider_requires_load_implementation():

    class IncompleteProvider(
        HistoricalDataProvider
    ):
        pass

    with pytest.raises(TypeError):
        IncompleteProvider()


def test_csv_adapter_implements_provider_contract(
    tmp_path,
):

    from atlas.trading.historical_data_adapter import (
        CSVHistoricalDataAdapter,
    )

    path = tmp_path / "data.csv"

    path.write_text(
        """timestamp,open,high,low,close,volume
2026-01-01,100,105,99,104,1000
2026-01-02,104,108,103,107,1200
""",
        encoding="utf-8",
    )

    provider = CSVHistoricalDataAdapter(
        path
    )

    assert isinstance(
        provider,
        HistoricalDataProvider,
    )

    result = provider.load(
        symbol="BTC-USD",
    )

    assert result.symbol == "BTC-USD"
    assert len(result) == 2
