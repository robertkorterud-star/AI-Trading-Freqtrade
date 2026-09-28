"""Read-only eToro market data for ATLAS crypto discovery.

The adapter only fetches instruments and market data. It never places orders.
API credentials are read from ETORO_API_KEY and ETORO_USER_KEY.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import time
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import uuid4

from atlas.market.market_scout import AssetType, MarketObservation


@dataclass(frozen=True, slots=True)
class EtoroCryptoInstrument:
    instrument_id: int
    symbol: str
    name: str


class EtoroMarketDataClient:
    """Small, injectable client for eToro's public market-data API."""

    BASE_URL = "https://public-api.etoro.com/api/v1"
    MIN_REQUEST_INTERVAL_SECONDS = 0.52
    RATE_BATCH_SIZE = 100

    def __init__(
        self,
        api_key: str,
        user_key: str,
        *,
        base_url: str | None = None,
        timeout: float = 15.0,
        opener: Callable | None = None,
        monotonic: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        if not api_key or not user_key:
            raise ValueError("Both eToro API key and user key are required.")
        self.api_key = api_key
        self.user_key = user_key
        self.base_url = (base_url or self.BASE_URL).rstrip("/")
        self.timeout = timeout
        self._opener = opener or urlopen
        self._monotonic = monotonic
        self._sleeper = sleeper
        self._last_request_at: float | None = None

    @classmethod
    def from_env(
        cls,
        env_file: str | Path | None = None,
    ) -> "EtoroMarketDataClient":
        """Build a client from environment variables and the project .env file."""
        _load_env_file(env_file)
        api_key = os.getenv("ETORO_API_KEY")
        user_key = os.getenv("ETORO_USER_KEY")
        if not api_key or not user_key:
            raise ValueError(
                "Set ETORO_API_KEY and ETORO_USER_KEY before using eToro data."
            )
        return cls(api_key=api_key, user_key=user_key)

    def _get(self, path: str, params: dict | None = None):
        if self._last_request_at is not None:
            elapsed = self._monotonic() - self._last_request_at
            delay = self.MIN_REQUEST_INTERVAL_SECONDS - elapsed
            if delay > 0:
                self._sleeper(delay)

        query = f"?{urlencode(params)}" if params else ""
        request = Request(
            f"{self.base_url}{path}{query}",
            headers={
                "Accept": "application/json",
                "User-Agent": "ATLAS/1.0",
                "x-api-key": self.api_key,
                "x-user-key": self.user_key,
                "x-request-id": str(uuid4()),
            },
            method="GET",
        )
        self._last_request_at = self._monotonic()

        try:
            with self._opener(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            if exc.code == 429:
                raise RuntimeError("eToro API rate limit reached (HTTP 429).") from exc
            raise RuntimeError(f"eToro API returned HTTP {exc.code}.") from exc
        except URLError as exc:
            raise RuntimeError(f"eToro API connection failed: {exc.reason}") from exc
        except json.JSONDecodeError as exc:
            raise RuntimeError("eToro API returned invalid JSON.") from exc

    def get_instrument_types(self) -> list[dict]:
        payload = self._get("/market-data/instrument-types")
        return payload.get("instrumentTypes", [])

    def get_instruments(self, instrument_type_id: int) -> list[dict]:
        """Read every search page, including explicit platform status fields.

        Search filters may be ignored by eToro, so the provider also validates
        instrument type and status locally. Status is not account suitability.
        """
        fields = (
            "instrumentId,instrumentTypeID,internalSymbolFull,displayname,"
            "isInternalInstrument,isHiddenFromClient,isDelisted,"
            "isCurrentlyTradable,isActiveInPlatform,isBuyEnabled"
        )
        results: list[dict] = []
        seen: set[int] = set()
        page = 1
        while True:
            payload = self._get("/market-data/search", {
                "instrumentTypeID": instrument_type_id,
                "fields": fields,
                "pageNumber": page,
                "pageSize": 100,
            })
            items = payload.get("items")
            total = _integer(payload.get("totalItems"))
            if not isinstance(items, list) or total is None or total < 0:
                raise RuntimeError("eToro returned invalid instrument search data.")
            if not items:
                if len(results) < total:
                    raise RuntimeError("eToro instrument search ended before all pages arrived.")
                return results
            new_ids = {_integer(item.get("instrumentId")) for item in items}
            new_ids.discard(None)
            if not new_ids - seen:
                raise RuntimeError("eToro instrument search repeated a page.")
            seen.update(new_ids)
            results.extend(items)
            if len(results) >= total:
                return results
            page += 1

    def get_rates(self, instrument_ids: list[int]) -> dict[int, dict]:
        """Retrieve rates in eToro's documented batches of at most 100 IDs."""
        results: dict[int, dict] = {}
        for start in range(0, len(instrument_ids), self.RATE_BATCH_SIZE):
            batch = instrument_ids[start : start + self.RATE_BATCH_SIZE]
            payload = self._get(
                "/market-data/instruments/rates",
                {"instrumentIds": ",".join(str(item) for item in batch)},
            )
            for rate in payload.get("rates", []):
                instrument_id = _integer(
                    rate.get("instrumentID", rate.get("instrumentId"))
                )
                if instrument_id is not None:
                    results[instrument_id] = rate
        return results

    def get_daily_candles(self, instrument_id: int, count: int = 8) -> list[dict]:
        payload = self._get(
            f"/market-data/instruments/{instrument_id}/history/candles/"
            f"asc/OneDay/{count}"
        )
        groups = payload.get("candles", [])
        if not groups:
            return []
        return groups[0].get("candles", [])


class EtoroCryptoMarketDataProvider:
    """Convert all eToro-listed crypto instruments into scanner observations."""

    def __init__(self, client: EtoroMarketDataClient) -> None:
        self.client = client

    @classmethod
    def from_env(
        cls,
        env_file: str | Path | None = None,
    ) -> "EtoroCryptoMarketDataProvider":
        return cls(EtoroMarketDataClient.from_env(env_file=env_file))

    def get_crypto_observations(self) -> list[MarketObservation]:
        types = self.client.get_instrument_types()
        crypto_type = next(
            (
                item
                for item in types
                if "crypto" in str(
                    item.get("instrumentTypeDescription", "")
                ).lower()
            ),
            None,
        )
        if crypto_type is None:
            raise RuntimeError("eToro did not return a cryptocurrency instrument type.")

        type_id = _integer(crypto_type.get("instrumentTypeID"))
        if type_id is None:
            raise RuntimeError("eToro returned an invalid cryptocurrency type ID.")

        instruments = self.client.get_instruments(type_id)
        normalized: list[EtoroCryptoInstrument] = []
        seen: set[int] = set()
        for item in instruments:
            if _integer(item.get("instrumentTypeID")) != type_id:
                continue
            # Require explicit status: missing/unknown fields must not qualify.
            if not all(item.get(key) is True for key in (
                "isActiveInPlatform", "isCurrentlyTradable", "isBuyEnabled"
            )):
                continue
            if not all(item.get(key) is False for key in (
                "isDelisted", "isHiddenFromClient", "isInternalInstrument"
            )):
                continue
            instrument_id = _integer(
                item.get("instrumentID", item.get("instrumentId"))
            )
            if instrument_id is None or instrument_id in seen:
                continue
            seen.add(instrument_id)
            symbol = str(
                item.get("internalSymbolFull") or ""
            ).strip()
            if not symbol or symbol.lower().endswith(".old"):
                continue
            normalized.append(
                EtoroCryptoInstrument(
                    instrument_id=instrument_id,
                    symbol=symbol,
                    name=str(item.get("displayname") or symbol),
                )
            )

        if not normalized:
            return []

        rates = self.client.get_rates(
            [instrument.instrument_id for instrument in normalized]
        )
        observations: list[MarketObservation] = []
        for instrument in normalized:
            rate = rates.get(instrument.instrument_id)
            if rate is None:
                continue
            price = _number(rate.get("lastExecution"))
            if price is None or price <= 0:
                price = _number(rate.get("bid"))
            if price is None or price <= 0:
                continue

            try:
                candles = self.client.get_daily_candles(instrument.instrument_id)
            except RuntimeError:
                # Keep a failed instrument from blocking the rest of the market.
                continue

            closes = [_number(item.get("close")) for item in candles]
            closes = [value for value in closes if value is not None and value > 0]
            previous_close = closes[-2] if len(closes) >= 2 else None
            week_ago_close = closes[0] if len(closes) >= 2 else None
            change_percent = (
                ((price / previous_close) - 1.0) * 100.0
                if previous_close
                else 0.0
            )
            weekly_change = (
                ((price / week_ago_close) - 1.0) * 100.0
                if week_ago_close
                else 0.0
            )

            volumes = [_number(item.get("volume")) or 0.0 for item in candles]
            current_volume = volumes[-1] if volumes else 0.0
            historical_volumes = volumes[:-1][-7:]
            average_volume = (
                sum(historical_volumes) / len(historical_volumes)
                if historical_volumes
                else 0.0
            )
            observations.append(
                MarketObservation(
                    symbol=instrument.symbol,
                    asset_type=AssetType.CRYPTO,
                    price=price,
                    volume=current_volume,
                    average_volume=average_volume,
                    change_percent=change_percent,
                    breakout_percent=weekly_change,
                    liquid=True,
                )
            )

        return observations


def _load_env_file(env_file: str | Path | None = None) -> None:
    """Load simple KEY=VALUE entries without overriding existing environment."""
    path = (
        Path(env_file)
        if env_file is not None
        else Path(__file__).resolve().parents[2] / ".env"
    )
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].lstrip()
        key, separator, value = line.partition("=")
        if not separator:
            continue
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if key:
            os.environ.setdefault(key, value)


def _number(value) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if result == result else None


def _integer(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
