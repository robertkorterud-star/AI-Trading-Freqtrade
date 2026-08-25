from dataclasses import dataclass

from atlas.market.asset_type import AssetType


@dataclass(slots=True, frozen=True)
class Asset:
    """One tradeable asset known to ATLAS."""

    symbol: str
    name: str
    asset_type: AssetType
    market: str
    currency: str
    active: bool = True
