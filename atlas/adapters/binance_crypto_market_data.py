"""Read-only Binance Spot crypto observations for ATLAS MarketScout."""

from __future__ import annotations

import math

from atlas.adapters.binance import BinanceAdapter
from atlas.market.market_scout import AssetType, MarketObservation


class BinanceCryptoMarketDataProvider:
    """Build cheap discovery observations from Binance public Spot data."""

    def __init__(
        self,
        adapter: BinanceAdapter | None = None,
        quote_asset: str = "USDT",
    ) -> None:
        self.adapter = adapter or BinanceAdapter()
        self.quote_asset = quote_asset.strip().upper()

    def get_crypto_observations(self) -> list[MarketObservation]:
        """Return active quote-market observations from one ticker snapshot."""
        exchange_info = self.adapter.get_exchange_info()
        raw_markets = exchange_info.get("symbols", [])
        tickers = {
            str(item.get("symbol", "")).upper(): item
            for item in self.adapter.get_24hr_tickers()
            if isinstance(item, dict)
        }

        observations: list[MarketObservation] = []

        for market in raw_markets:
            if not self._is_tradable_market(market):
                continue

            exchange_symbol = str(market.get("symbol", "")).upper()
            base_asset = str(market.get("baseAsset", "")).upper()
            ticker = tickers.get(exchange_symbol)

            if not base_asset or ticker is None:
                continue

            observation = self._observation(base_asset, ticker)
            if observation is not None:
                observations.append(observation)

        return observations

    def _is_tradable_market(self, market: dict) -> bool:
        return (
            str(market.get("status", "")).upper() == "TRADING"
            and str(market.get("quoteAsset", "")).upper() == self.quote_asset
            and market.get("isSpotTradingAllowed", True) is True
        )

    @staticmethod
    def _number(value) -> float | None:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        if not math.isfinite(number):
            return None
        return number

    def _observation(
        self,
        base_asset: str,
        ticker: dict,
    ) -> MarketObservation | None:
        price = self._number(ticker.get("lastPrice"))
        quote_volume = self._number(ticker.get("quoteVolume"))
        change_percent = self._number(ticker.get("priceChangePercent"))
        bid = self._number(ticker.get("bidPrice"))
        ask = self._number(ticker.get("askPrice"))

        if (
            price is None
            or price <= 0.0
            or quote_volume is None
            or quote_volume < 0.0
            or change_percent is None
            or bid is None
            or ask is None
            or bid <= 0.0
            or ask <= 0.0
            or ask < bid
        ):
            return None

        midpoint = (bid + ask) / 2.0
        if midpoint <= 0.0:
            return None

        spread_percent = ((ask - bid) / midpoint) * 100.0

        return MarketObservation(
            symbol=base_asset,
            asset_type=AssetType.CRYPTO,
            price=price,
            volume=quote_volume,
            # Broad 24h discovery has no historical-volume baseline yet.
            average_volume=0.0,
            change_percent=change_percent,
            liquid=quote_volume > 0.0,
            bid_ask_spread_percent=spread_percent,
        )
