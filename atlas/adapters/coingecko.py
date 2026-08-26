"""
ATLAS CoinGecko adapter.

Provides crypto market context without exposing HTTP details
to the rest of ATLAS.

The adapter is intentionally small and mockable.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


@dataclass(slots=True)
class CoinGeckoError:
    status: int | None
    message: str


class CoinGeckoAdapter:
    """Read-only adapter for CoinGecko public API data."""

    BASE_URL = "https://api.coingecko.com/api/v3"

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

    def get_coin(
        self,
        coin_id: str,
        localization: bool = False,
    ) -> dict:
        return self._get(
            f"/coins/{coin_id}",
            {
                "localization": str(
                    localization
                ).lower(),
            },
        )

    def get_markets(
        self,
        vs_currency: str = "usd",
        page: int = 1,
        per_page: int = 100,
        order: str = "market_cap_desc",
    ) -> list[dict]:
        return self._get(
            "/coins/markets",
            {
                "vs_currency": vs_currency,
                "order": order,
                "per_page": per_page,
                "page": page,
                "sparkline": "false",
            },
        )

    def get_ohlc(
        self,
        coin_id: str,
        vs_currency: str = "usd",
        days: int | str = 30,
    ) -> list[list[float]]:
        return self._get(
            f"/coins/{coin_id}/ohlc",
            {
                "vs_currency": vs_currency,
                "days": days,
            },
        )

    def get_market_chart(
        self,
        coin_id: str,
        vs_currency: str = "usd",
        days: int | str = 30,
        interval: str | None = None,
    ) -> dict:
        params = {
            "vs_currency": vs_currency,
            "days": days,
        }

        if interval is not None:
            params["interval"] = interval

        return self._get(
            f"/coins/{coin_id}/market_chart",
            params,
        )

    def get_global_market(self) -> dict:
        return self._get("/global")

    def get_categories(
        self,
        order: str = "market_cap_desc",
    ) -> list[dict]:
        return self._get(
            "/coins/categories",
            {"order": order},
        )

    def get_trending(self) -> dict:
        return self._get("/search/trending")

    def _get(
        self,
        path: str,
        params: dict | None = None,
    ):
        url = self._build_url(
            path,
            params,
        )

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

            return json.loads(
                payload.decode("utf-8")
            )

        except HTTPError as exc:
            message = self._error_message(exc)

            raise RuntimeError(
                f"CoinGecko API error "
                f"{exc.code}: {message}"
            ) from exc

        except URLError as exc:
            raise RuntimeError(
                f"CoinGecko connection error: "
                f"{exc.reason}"
            ) from exc

        except TimeoutError as exc:
            raise RuntimeError(
                "CoinGecko request timed out"
            ) from exc

        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "CoinGecko returned invalid JSON"
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
    def _error_message(
        exc: HTTPError,
    ) -> str:
        try:
            payload = exc.read().decode(
                "utf-8"
            )

            data = json.loads(payload)

            if isinstance(data, dict):
                return str(
                    data.get(
                        "error",
                        data.get(
                            "status",
                            payload,
                        ),
                    )
                )

            return payload

        except (
            OSError,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ):
            return str(exc.reason)
