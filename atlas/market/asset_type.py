from enum import Enum


class AssetType(str, Enum):
    """Supported ATLAS asset classes."""

    STOCK = "stock"
    CRYPTO = "crypto"
    ETF = "etf"
