"""Scanner candidate source for ATLAS research."""

from atlas.market.candidates.source import Candidate


class ScannerCandidateSource:
    """Expose read-only scanner results through the CandidateSource contract."""

    def __init__(
        self,
        scanner,
        limit: int = 100,
        exchange: str = "etoro",
    ):
        self.scanner = scanner
        self.limit = limit
        self.exchange = exchange.strip().lower()
        if self.exchange not in {"etoro", "binance"}:
            raise ValueError("Unsupported scanner exchange")

    @staticmethod
    def _canonical_symbol(symbol: str, asset_type) -> str:
        normalized = str(symbol or "").strip().upper()

        if not normalized:
            return ""

        asset_type_value = (
            asset_type.value
            if hasattr(asset_type, "value")
            else str(asset_type)
        )

        if asset_type_value == "crypto" and not normalized.endswith("-USD"):
            return f"{normalized}-USD"

        return normalized

    def discover(self) -> list[Candidate]:
        if self.exchange == "binance":
            result = self.scanner.scan(limit=self.limit)
        else:
            result = self.scanner.scan_etoro_crypto(limit=self.limit)
        candidates = []

        for item in result.candidates:
            scanner_symbol = str(item.symbol).strip().upper()
            quote_asset = None
            base_symbol = (
                scanner_symbol.removesuffix(".SPOT")
                if self.exchange == "etoro"
                else scanner_symbol
            )

            if self.exchange == "binance":
                for quote in ("USDT", "USDC"):
                    if scanner_symbol.endswith(quote):
                        quote_asset = quote
                        base_symbol = scanner_symbol[:-len(quote)]
                        break
                if not quote_asset or not base_symbol:
                    continue

            symbol = self._canonical_symbol(
                base_symbol,
                item.asset_type,
            )

            if not symbol:
                continue

            reasons = tuple(
                str(reason).strip()
                for reason in getattr(item, "reasons", ())
                if str(reason).strip()
            )

            asset_type = item.asset_type
            asset_type_value = (
                asset_type.value
                if hasattr(asset_type, "value")
                else str(asset_type)
            )

            candidates.append(
                Candidate(
                    symbol=symbol,
                    source=f"{self.exchange}_scanner",
                    score=float(item.score),
                    reason="; ".join(reasons),
                    metadata={
                        "scanner_symbol": scanner_symbol,
                        "asset_type": asset_type_value,
                        **(
                            {
                                "exchange": "binance",
                                "quote_asset": quote_asset,
                            }
                            if self.exchange == "binance"
                            else {}
                        ),
                    },
                )
            )

        return candidates
