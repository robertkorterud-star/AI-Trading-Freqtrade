"""
ATLAS Binance adapter.

Provides read-only Binance Spot market data without exposing HTTP
details to the rest of ATLAS.

The adapter is intentionally small and mockable. No authentication
or order execution is supported here.
"""

from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class BinanceAdapter:
    """Read-only adapter for Binance Spot public REST API."""

    BASE_URL = "https://data-api.binance.vision/api/v3"
    SAPI_BASE_URL = "https://api.binance.com/sapi/v1"

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = 10.0,
        user_agent: str = "ATLAS/1.0",
        api_key: str | None = None,
        sapi_base_url: str | None = None,
        opener=None,
    ):
        self.base_url = (
            base_url.rstrip("/")
            if base_url
            else self.BASE_URL
        )
        self.timeout = timeout
        self.user_agent = user_agent
        self.api_key = api_key
        self.sapi_base_url = (
            sapi_base_url.rstrip("/")
            if sapi_base_url
            else self.SAPI_BASE_URL
        )
        self._opener = opener or urlopen

    def get_price(self, symbol: str) -> dict:
        """Return the current price for a symbol."""
        return self._get("/ticker/price", {"symbol": symbol})

    def get_24hr_ticker(self, symbol: str) -> dict:
        """Return 24-hour ticker statistics for a symbol."""
        return self._get("/ticker/24hr", {"symbol": symbol})

    def get_24hr_tickers(self) -> list[dict]:
        """Return all Binance Spot 24-hour ticker statistics."""
        payload = self._get("/ticker/24hr")
        if not isinstance(payload, list):
            raise RuntimeError("Binance returned an invalid ticker list")
        return payload

    def get_order_book(
        self,
        symbol: str,
        limit: int = 100,
    ) -> dict:
        """Return the current order book for a symbol."""
        return self._get(
            "/depth",
            {"symbol": symbol, "limit": limit},
        )

    def get_recent_trades(
        self,
        symbol: str,
        limit: int = 500,
    ) -> list[dict]:
        """Return recent public trades for a symbol."""
        return self._get(
            "/trades",
            {"symbol": symbol, "limit": limit},
        )

    def get_klines(
        self,
        symbol: str,
        interval: str = "1m",
        limit: int = 500,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> list[list]:
        """Return OHLCV candlesticks for a symbol."""
        return self._get(
            "/klines",
            {
                "symbol": symbol,
                "interval": interval,
                "limit": limit,
                "startTime": start_time,
                "endTime": end_time,
            },
        )

    def get_tokenized_assets(self) -> list[dict]:
        """Return Binance tokenized-asset metadata using API-key auth only."""
        if not self.api_key:
            return []

        payload = self._get_absolute(
            f"{self.sapi_base_url}/equity/market/tokenized-assets",
            headers={"X-MBX-APIKEY": self.api_key},
        )
        if not isinstance(payload, list):
            raise RuntimeError("Binance returned an invalid tokenized asset list")
        return payload

    def get_exchange_info(self, symbol: str | None = None) -> dict:
        """Return public exchange metadata, optionally for one symbol."""
        return self._get(
            "/exchangeInfo",
            {"symbol": symbol},
        )

    def _get(
        self,
        path: str,
        params: dict | None = None,
    ):
        return self._get_absolute(self._build_url(path, params))

    def _get_absolute(
        self,
        url: str,
        headers: dict | None = None,
    ):
        request_headers = {
            "Accept": "application/json",
            "User-Agent": self.user_agent,
        }
        if headers:
            request_headers.update(headers)

        request = Request(
            url,
            headers=request_headers,
            method="GET",
        )

        try:
            with self._opener(
                request,
                timeout=self.timeout,
            ) as response:
                payload = response.read()

            return json.loads(payload.decode("utf-8"))

        except HTTPError as exc:
            raise RuntimeError(
                f"Binance API error {exc.code}: "
                f"{self._error_message(exc)}"
            ) from exc

        except URLError as exc:
            raise RuntimeError(
                f"Binance connection error: {exc.reason}"
            ) from exc

        except TimeoutError as exc:
            raise RuntimeError(
                "Binance request timed out"
            ) from exc

        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "Binance returned invalid JSON"
            ) from exc

    def _build_url(
        self,
        path: str,
        params: dict | None = None,
    ) -> str:
        url = f"{self.base_url}{path}"

        if params:
            encoded = urlencode(
                {
                    key: value
                    for key, value in params.items()
                    if value is not None
                }
            )
            if encoded:
                url = f"{url}?{encoded}"

        return url

    @staticmethod
    def _error_message(exc: HTTPError) -> str:
        try:
            payload = exc.read().decode("utf-8")
            data = json.loads(payload)
            if isinstance(data, dict):
                return str(data.get("msg", data.get("code", payload)))
            return payload
        except (
            OSError,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ):
            return str(exc.reason)
