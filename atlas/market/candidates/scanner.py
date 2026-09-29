"""Scanner candidate source for ATLAS research."""

from atlas.market.asset_type import AssetType
from atlas.market.candidates.source import Candidate


class ScannerCandidateSource:
    """Expose read-only scanner results through the CandidateSource contract."""

    def __init__(self, scanner, limit: int = 100):
        self.scanner = scanner
        self.limit = limit

    @staticmethod
    def _canonical_symbol(symbol: str, asset_type) -> str:
        normalized = str(symbol or "").strip().upper()

        if not normalized:
            return ""

        if asset_type is AssetType.CRYPTO and not normalized.endswith("-USD"):
            return f"{normalized}-USD"

        return normalized

    def discover(self) -> list[Candidate]:
        result = self.scanner.scan_etoro_crypto(limit=self.limit)
        candidates = []

        for item in result.candidates:
            symbol = self._canonical_symbol(
                item.symbol,
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
                    source="etoro_scanner",
                    score=float(item.score),
                    reason="; ".join(reasons),
                    metadata={
                        "scanner_symbol": str(item.symbol).strip().upper(),
                        "asset_type": asset_type_value,
                    },
                )
            )

        return candidates
