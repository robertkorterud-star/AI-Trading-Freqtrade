"""
ATLAS Historical Data Adapter.

Loads normalized OHLCV data from deterministic sources.

The adapter is intentionally independent of trading strategies,
backtesting and decision making.
"""

from csv import DictReader
from datetime import datetime
from pathlib import Path

from atlas.trading.historical_market_data import (
    HistoricalMarketData,
    OHLCVBar,
)


class CSVHistoricalDataAdapter:
    """Load HistoricalMarketData from an OHLCV CSV file."""

    REQUIRED_COLUMNS = (
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "volume",
    )

    def load(
        self,
        path: str | Path,
        symbol: str,
    ) -> HistoricalMarketData:

        csv_path = Path(path)

        if not csv_path.exists():
            raise FileNotFoundError(
                csv_path
            )

        with csv_path.open(
            "r",
            encoding="utf-8",
            newline="",
        ) as file:

            reader = DictReader(file)

            if reader.fieldnames is None:
                raise ValueError(
                    "CSV file has no header."
                )

            missing = [
                column
                for column in self.REQUIRED_COLUMNS
                if column not in reader.fieldnames
            ]

            if missing:
                raise ValueError(
                    "Missing required columns: "
                    + ", ".join(missing)
                )

            bars = []

            for row_number, row in enumerate(
                reader,
                start=2,
            ):
                try:
                    bars.append(
                        OHLCVBar(
                            timestamp=self._parse_timestamp(
                                row["timestamp"]
                            ),
                            open=float(
                                row["open"]
                            ),
                            high=float(
                                row["high"]
                            ),
                            low=float(
                                row["low"]
                            ),
                            close=float(
                                row["close"]
                            ),
                            volume=float(
                                row["volume"]
                            ),
                        )
                    )
                except (
                    KeyError,
                    TypeError,
                    ValueError,
                ) as exc:
                    raise ValueError(
                        f"Invalid OHLCV row "
                        f"{row_number}: {exc}"
                    ) from exc

        return HistoricalMarketData(
            symbol=symbol,
            bars=bars,
        )

    @staticmethod
    def _parse_timestamp(
        value: str,
    ) -> datetime:

        value = value.strip()

        if not value:
            raise ValueError(
                "timestamp cannot be empty."
            )

        try:
            return datetime.fromisoformat(
                value
            )
        except ValueError:
            pass

        formats = (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
        )

        for date_format in formats:
            try:
                return datetime.strptime(
                    value,
                    date_format,
                )
            except ValueError:
                continue

        raise ValueError(
            f"Unsupported timestamp: {value}"
        )
