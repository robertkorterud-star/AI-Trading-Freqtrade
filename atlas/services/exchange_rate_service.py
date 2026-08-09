"""
Exchange Rate Service

Fetches currency exchange rates.
"""

from dataclasses import dataclass

import requests


@dataclass
class ExchangeRate:
    base: str
    target: str
    rate: float


class ExchangeRateService:
    """Provides exchange rates."""

    URL = "https://open.er-api.com/v6/latest"

    def get_rate(
        self,
        base: str = "USD",
        target: str = "NOK",
    ) -> ExchangeRate:

        try:

            response = requests.get(
                f"{self.URL}/{base}",
                timeout=10,
            )

            response.raise_for_status()

            data = response.json()

            rate = data["rates"][target]

            return ExchangeRate(
                base=base,
                target=target,
                rate=rate,
            )

        except Exception as error:

            print(f"Exchange rate error: {error}")

            return ExchangeRate(
                base=base,
                target=target,
                rate=1.0,
            )