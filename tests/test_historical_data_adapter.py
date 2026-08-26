from datetime import datetime

import pytest

from atlas.trading.historical_data_adapter import (
    CSVHistoricalDataAdapter,
)


def _csv():
    return """timestamp,open,high,low,close,volume
2026-01-01T00:00:00,100,105,99,104,1000
2026-01-02T00:00:00,104,108,103,107,1200
2026-01-03T00:00:00,107,110,105,109,1400
"""


def test_csv_adapter_loads_ohlcv(tmp_path):

    path = tmp_path / "btc.csv"
    path.write_text(
        _csv(),
        encoding="utf-8",
    )

    data = CSVHistoricalDataAdapter().load(
        path,
        symbol="BTC-USD",
    )

    assert data.symbol == "BTC-USD"
    assert len(data) == 3

    assert data.closes == [
        104.0,
        107.0,
        109.0,
    ]

    assert data.bars[0].timestamp == (
        datetime(
            2026,
            1,
            1,
        )
    )


def test_csv_adapter_supports_standard_timestamp():

    from pathlib import Path

    import tempfile

    with tempfile.TemporaryDirectory() as directory:

        path = Path(directory) / "data.csv"

        path.write_text(
            """timestamp,open,high,low,close,volume
2026-01-01 12:30:00,100,105,99,104,1000
""",
            encoding="utf-8",
        )

        data = CSVHistoricalDataAdapter().load(
            path,
            symbol="AAPL",
        )

        assert data.bars[0].timestamp == (
            datetime(
                2026,
                1,
                1,
                12,
                30,
            )
        )


def test_csv_adapter_rejects_missing_columns(
    tmp_path,
):

    path = tmp_path / "invalid.csv"

    path.write_text(
        """timestamp,open,high,low,close
2026-01-01,100,105,99,104
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        CSVHistoricalDataAdapter().load(
            path,
            symbol="BTC-USD",
        )


def test_csv_adapter_rejects_invalid_rows(
    tmp_path,
):

    path = tmp_path / "invalid.csv"

    path.write_text(
        """timestamp,open,high,low,close,volume
2026-01-01,not-a-number,105,99,104,1000
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        CSVHistoricalDataAdapter().load(
            path,
            symbol="BTC-USD",
        )


def test_csv_adapter_rejects_missing_file(
    tmp_path,
):

    path = tmp_path / "missing.csv"

    with pytest.raises(FileNotFoundError):
        CSVHistoricalDataAdapter().load(
            path,
            symbol="BTC-USD",
        )


def test_csv_adapter_rejects_empty_timestamp(
    tmp_path,
):

    path = tmp_path / "invalid.csv"

    path.write_text(
        """timestamp,open,high,low,close,volume
,100,105,99,104,1000
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        CSVHistoricalDataAdapter().load(
            path,
            symbol="BTC-USD",
        )


def test_csv_adapter_preserves_data_validation(
    tmp_path,
):

    path = tmp_path / "invalid.csv"

    path.write_text(
        """timestamp,open,high,low,close,volume
2026-01-01,100,99,98,104,1000
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        CSVHistoricalDataAdapter().load(
            path,
            symbol="BTC-USD",
        )
