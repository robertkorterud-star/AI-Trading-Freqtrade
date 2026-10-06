"""ATLAS Binance USD-M Futures market-data adapter.

Provides read-only public derivatives market data without exposing HTTP
details to the rest of ATLAS.

No authentication or order execution is supported here.
"""

from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class BinanceFuturesAdapter:
    """Read-only adapter for Binance USD-M Futures public market data."""

    BASE_URL = "https://fapi.binance.com"

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = 10.0,
        user_agent: str = "ATLAS/1.0",
        opener=None,
    ):
        self.base_url = (
            base_url.rstrip("/")
            if base_url
            else self.BASE_URL
        )
        self.timeout = timeout
        self.user_agent = user_agent
        self._opener = opener or urlopen

    def get_funding_rate_history(
        self,
        symbol: str,
        start_time: int | None = None,
        end_time: int | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """Return public historical funding rates."""

        payload = self._get(
            "/fapi/v1/fundingRate",
            {
                "symbol": symbol,
                "startTime": start_time,
                "endTime": end_time,
                "limit": limit,
            },
        )

        if not isinstance(payload, list):
            raise RuntimeError(
                "Binance Futures returned invalid funding-rate data"
            )

        return payload

    def get_open_interest_history(
        self,
        symbol: str,
        period: str = "5m",
        start_time: int | None = None,
        end_time: int | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """Return public historical open-interest statistics."""

        payload = self._get(
            "/futures/data/openInterestHist",
            {
                "symbol": symbol,
                "period": period,
                "startTime": start_time,
                "endTime": end_time,
                "limit": limit,
            },
        )

        if not isinstance(payload, list):
            raise RuntimeError(
                "Binance Futures returned invalid open-interest data"
            )

        return payload

    def _get(
        self,
        path: str,
        params: dict | None = None,
    ):
        url = self._build_url(path, params)

        request = Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": self.user_agent,
            },
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
                f"Binance Futures API error {exc.code}: "
                f"{self._error_message(exc)}"
            ) from exc

        except URLError as exc:
            raise RuntimeError(
                f"Binance Futures connection error: {exc.reason}"
            ) from exc

        except TimeoutError as exc:
            raise RuntimeError(
                "Binance Futures request timed out"
            ) from exc

        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "Binance Futures returned invalid JSON"
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
                return str(
                    data.get(
                        "msg",
                        data.get("code", payload),
                    )
                )

            return payload

        except (
            OSError,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ):
            return str(exc.reason)
