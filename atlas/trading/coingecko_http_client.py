"""
ATLAS CoinGecko HTTP client.

Transport-only client for CoinGecko API requests.
No trading or strategy logic belongs here.
"""

from typing import Protocol


class HTTPResponse(Protocol):
    status_code: int

    def json(self) -> object:
        ...

    def raise_for_status(self) -> None:
        ...


class HTTPTransport(Protocol):

    def get(
        self,
        url: str,
        *,
        params: dict[str, str],
        timeout: float,
    ) -> HTTPResponse:
        ...


class CoinGeckoAPIError(RuntimeError):
    """Base exception for CoinGecko API failures."""


class CoinGeckoRateLimitError(
    CoinGeckoAPIError
):
    """Raised when CoinGecko rate-limits the client."""


class CoinGeckoHTTPError(
    CoinGeckoAPIError
):
    """Raised for other HTTP failures."""


class CoinGeckoResponseError(
    CoinGeckoAPIError
):
    """Raised when CoinGecko returns invalid data."""


class CoinGeckoHTTPClient:
    """Small transport-only CoinGecko client."""

    BASE_URL = (
        "https://api.coingecko.com/api/v3"
    )

    def __init__(
        self,
        transport: HTTPTransport,
        timeout: float = 10.0,
    ):
        if timeout <= 0:
            raise ValueError(
                "timeout must be positive."
            )

        self.transport = transport
        self.timeout = timeout

    def get_ohlc(
        self,
        coin_id: str,
        vs_currency: str,
        days: str,
    ) -> list[list[float]]:

        if not coin_id:
            raise ValueError(
                "coin_id must not be empty."
            )

        if not vs_currency:
            raise ValueError(
                "vs_currency must not be empty."
            )

        if not days:
            raise ValueError(
                "days must not be empty."
            )

        response = self.transport.get(
            f"{self.BASE_URL}/coins/"
            f"{coin_id}/ohlc",
            params={
                "vs_currency": vs_currency,
                "days": days,
            },
            timeout=self.timeout,
        )

        if response.status_code == 429:
            raise CoinGeckoRateLimitError(
                "CoinGecko rate limit reached."
            )

        if response.status_code >= 400:
            raise CoinGeckoHTTPError(
                "CoinGecko request failed with "
                f"HTTP {response.status_code}."
            )

        try:
            payload = response.json()
        except Exception as exc:
            raise CoinGeckoResponseError(
                "CoinGecko returned invalid JSON."
            ) from exc

        if not isinstance(payload, list):
            raise CoinGeckoResponseError(
                "CoinGecko OHLC response must be a list."
            )

        validated = []

        for row in payload:

            if not isinstance(row, list):
                raise CoinGeckoResponseError(
                    "CoinGecko OHLC row must be a list."
                )

            if len(row) < 5:
                raise CoinGeckoResponseError(
                    "CoinGecko OHLC row must contain "
                    "at least five values."
                )

            try:
                validated.append(
                    [
                        float(row[0]),
                        float(row[1]),
                        float(row[2]),
                        float(row[3]),
                        float(row[4]),
                    ]
                )
            except (TypeError, ValueError) as exc:
                raise CoinGeckoResponseError(
                    "CoinGecko OHLC row contains "
                    "non-numeric values."
                ) from exc

        return validated
