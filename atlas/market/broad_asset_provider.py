"""Normalize a broad external instrument feed into ATLAS assets."""

from collections.abc import Mapping

from atlas.market.asset import Asset
from atlas.market.asset_type import AssetType


class BroadAssetProvider:
    """Adapt an instrument source to the existing ``AssetUniverse`` contract.

    The source must provide ``list_instruments()`` and return mappings with
    ``symbol``, ``name``, ``type``, ``market``, ``currency`` and ``active``
    fields. Unsupported instrument types and inactive instruments are
    discarded before applying the result limit.
    """

    _ASSET_TYPES = {
        "STOCK": AssetType.STOCK,
        "EQUITY": AssetType.STOCK,
        "CRYPTO": AssetType.CRYPTO,
        "CRYPTOCURRENCY": AssetType.CRYPTO,
        "CRYPTO_CURRENCY": AssetType.CRYPTO,
        "ETF": AssetType.ETF,
    }

    def __init__(self, source, limit: int = 1000) -> None:
        if isinstance(limit, bool) or not isinstance(limit, int):
            raise TypeError("limit must be an integer")
        if limit < 0:
            raise ValueError("limit must be non-negative")
        list_instruments = getattr(source, "list_instruments", None)
        if not callable(list_instruments):
            raise TypeError("source must provide list_instruments()")
        self.source = source
        self.limit = limit

    @staticmethod
    def _is_active(value) -> bool:
        if isinstance(value, str):
            inactive_values = {"", "0", "false", "no", "inactive"}
            return value.strip().lower() not in inactive_values
        return bool(value)

    @classmethod
    def _normalize(cls, instrument) -> Asset | None:
        if not isinstance(instrument, Mapping):
            return None

        symbol = str(instrument.get("symbol") or "").strip().upper()
        if not symbol or not cls._is_active(instrument.get("active", True)):
            return None

        raw_type = str(instrument.get("type") or "").strip().upper()
        asset_type = cls._ASSET_TYPES.get(raw_type)
        if asset_type is None:
            return None

        name = str(instrument.get("name") or symbol).strip() or symbol
        market = str(instrument.get("market") or "").strip()
        currency = str(instrument.get("currency") or "USD").strip().upper()

        return Asset(
            symbol=symbol,
            name=name,
            asset_type=asset_type,
            market=market,
            currency=currency,
            active=True,
        )

    def list_assets(self) -> list[Asset]:
        """Return supported active instruments, capped at ``limit``."""
        if self.limit == 0:
            return []

        instruments = self.source.list_instruments()
        assets = []
        seen = set()
        for instrument in instruments:
            asset = self._normalize(instrument)
            if asset is None or asset.symbol in seen:
                continue
            seen.add(asset.symbol)
            assets.append(asset)
            if len(assets) >= self.limit:
                break
        return assets
