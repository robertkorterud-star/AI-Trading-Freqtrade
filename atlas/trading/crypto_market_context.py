"""
ATLAS normalized crypto market context.

Converts external crypto market data into stable ATLAS models.
No HTTP or CoinGecko-specific logic belongs here.
"""

from dataclasses import dataclass


@dataclass(slots=True)
class CryptoAssetContext:
    coin_id: str
    symbol: str
    name: str

    price: float | None
    market_cap: float | None
    market_cap_rank: int | None
    volume_24h: float | None

    change_24h: float | None
    change_7d: float | None
    change_30d: float | None

    circulating_supply: float | None
    total_supply: float | None

    data_quality: str


@dataclass(slots=True)
class GlobalCryptoContext:
    total_market_cap: float | None
    total_volume_24h: float | None
    market_cap_change_24h: float | None

    btc_dominance: float | None
    eth_dominance: float | None

    data_quality: str


class CryptoMarketContextBuilder:
    """Normalize CoinGecko-compatible responses."""

    @staticmethod
    def asset_from_market(
        data: dict,
    ) -> CryptoAssetContext:

        required_identity = all(
            data.get(key)
            for key in (
                "id",
                "symbol",
                "name",
            )
        )

        if not required_identity:
            quality = "MISSING"
        elif data.get("current_price") is None:
            quality = "POOR"
        else:
            quality = "GOOD"

        return CryptoAssetContext(
            coin_id=str(
                data.get("id", "")
            ),
            symbol=str(
                data.get("symbol", "")
            ).upper(),
            name=str(
                data.get("name", "")
            ),
            price=_number(
                data.get("current_price")
            ),
            market_cap=_number(
                data.get("market_cap")
            ),
            market_cap_rank=_integer(
                data.get("market_cap_rank")
            ),
            volume_24h=_number(
                data.get("total_volume")
            ),
            change_24h=_number(
                data.get("price_change_percentage_24h")
            ),
            change_7d=_number(
                data.get("price_change_percentage_7d_in_currency")
            ),
            change_30d=_number(
                data.get("price_change_percentage_30d_in_currency")
            ),
            circulating_supply=_number(
                data.get("circulating_supply")
            ),
            total_supply=_number(
                data.get("total_supply")
            ),
            data_quality=quality,
        )

    @staticmethod
    def asset_from_coin(
        data: dict,
    ) -> CryptoAssetContext:

        market_data = data.get(
            "market_data",
            {},
        )

        market_cap = market_data.get(
            "market_cap",
            {},
        )

        current_price = market_data.get(
            "current_price",
            {},
        )

        volume = market_data.get(
            "total_volume",
            {},
        )

        change = market_data.get(
            "price_change_percentage_24h",
        )

        if not data.get("id"):
            quality = "MISSING"
        elif not current_price.get("usd"):
            quality = "POOR"
        else:
            quality = "GOOD"

        return CryptoAssetContext(
            coin_id=str(
                data.get("id", "")
            ),
            symbol=str(
                data.get("symbol", "")
            ).upper(),
            name=str(
                data.get("name", "")
            ),
            price=_number(
                current_price.get("usd")
            ),
            market_cap=_number(
                market_cap.get("usd")
            ),
            market_cap_rank=_integer(
                data.get("market_cap_rank")
            ),
            volume_24h=_number(
                volume.get("usd")
            ),
            change_24h=_number(change),
            change_7d=_number(
                market_data.get(
                    "price_change_percentage_7d_in_currency",
                    {},
                ).get("usd")
                if isinstance(
                    market_data.get(
                        "price_change_percentage_7d_in_currency"
                    ),
                    dict,
                )
                else None
            ),
            change_30d=_number(
                market_data.get(
                    "price_change_percentage_30d_in_currency",
                    {},
                ).get("usd")
                if isinstance(
                    market_data.get(
                        "price_change_percentage_30d_in_currency"
                    ),
                    dict,
                )
                else None
            ),
            circulating_supply=_number(
                market_data.get(
                    "circulating_supply"
                )
            ),
            total_supply=_number(
                market_data.get(
                    "total_supply"
                )
            ),
            data_quality=quality,
        )

    @staticmethod
    def global_context(
        data: dict,
    ) -> GlobalCryptoContext:

        payload = data.get(
            "data",
            {},
        )

        market_cap = payload.get(
            "total_market_cap",
            {},
        )

        volume = payload.get(
            "total_volume",
            {},
        )

        percentage = payload.get(
            "market_cap_percentage",
            {},
        )

        market_cap_change = payload.get(
            "market_cap_change_percentage_24h_usd"
        )

        if not payload:
            quality = "MISSING"
        elif (
            market_cap.get("usd") is None
            or volume.get("usd") is None
        ):
            quality = "POOR"
        else:
            quality = "GOOD"

        return GlobalCryptoContext(
            total_market_cap=_number(
                market_cap.get("usd")
            ),
            total_volume_24h=_number(
                volume.get("usd")
            ),
            market_cap_change_24h=_number(
                market_cap_change
            ),
            btc_dominance=_number(
                percentage.get("btc")
            ),
            eth_dominance=_number(
                percentage.get("eth")
            ),
            data_quality=quality,
        )


def _number(value) -> float | None:
    if value is None:
        return None

    try:
        return float(value)
    except (
        TypeError,
        ValueError,
    ):
        return None


def _integer(value) -> int | None:
    if value is None:
        return None

    try:
        return int(value)
    except (
        TypeError,
        ValueError,
    ):
        return None
